"""
Data Ingestion and Population Script for 14 Bank Databases.
Lee el CSV de la práctica (con o sin línea de metadatos "Actualizado ..."),
valida campos, hace muestreo estratificado y carga multi-hilo en las 14 BDs.
"""

import os
import csv
import math
import sys
import argparse
import time
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import BANKS, ASFI_DB_PATH
from crypto import (
    CaesarCipher, AtbashCipher, VigenereCipher, PlayfairCipher, HillCipher,
    DESCipher, TripleDESCipher, BlowfishCipher, TwofishCipher, AESCipher, ChaCha20Cipher,
    RSACipher, ElGamalCipher, ECCCipher
)
from databases.bank_dbs import bank_db_manager

CIPHER_INSTANCES = {
    1: CaesarCipher(),
    2: AtbashCipher(),
    3: VigenereCipher(),
    4: PlayfairCipher(),
    5: HillCipher(),
    6: DESCipher(),
    7: TripleDESCipher(),
    8: BlowfishCipher(),
    9: TwofishCipher(),
    10: AESCipher(),
    11: RSACipher(),
    12: ElGamalCipher(),
    13: ECCCipher(),
    14: ChaCha20Cipher()
}

# Campos oficiales del dataset actualizado
REQUIRED_CSV_FIELDS = ("NroCuenta", "IdBanco", "Saldo", "Nombres", "Apellidos")
OPTIONAL_CSV_FIELDS = ("Nro", "Identificacion")
EXPECTED_CSV_FIELDS = REQUIRED_CSV_FIELDS + OPTIONAL_CSV_FIELDS


def encrypt_balance(bank_id: int, saldo_usd: float) -> str:
    cipher = CIPHER_INSTANCES.get(bank_id)
    if not cipher:
        raise ValueError(f"No cipher algorithm registered for BankId {bank_id}")
    return cipher.encrypt(str(saldo_usd))


def decrypt_balance(bank_id: int, saldo_cifrado: str) -> float:
    cipher = CIPHER_INSTANCES.get(bank_id)
    if not cipher:
        raise ValueError(f"No cipher algorithm registered for BankId {bank_id}")
    raw_str = cipher.decrypt(saldo_cifrado)
    return float(raw_str)


def _normalize_header(name: str) -> str:
    return (name or "").replace("\ufeff", "").strip()


def _is_header_row(fields) -> bool:
    normalized = {_normalize_header(f) for f in fields if f is not None}
    return {"NroCuenta", "IdBanco", "Saldo"}.issubset(normalized)


def iter_dataset_rows(csv_path: str):
    """
    Itera filas del CSV saltando metadatos previos al header real.
    Soporta BOM y la línea 'Actualizado YYYY-MM-DD ...'.
    """
    with open(csv_path, "r", encoding="utf-8-sig", errors="ignore", newline="") as f:
        header = None
        while True:
            line = f.readline()
            if not line:
                raise ValueError(f"No se encontró header válido en {csv_path}")
            probe = next(csv.reader([line]))
            if _is_header_row(probe):
                header = [_normalize_header(h) for h in probe]
                break
            first = _normalize_header(probe[0] if probe else "").lower()
            if first.startswith("actualizado") or not any(x.strip() for x in probe if x):
                continue
            # Línea inesperada: si parece header con nombres distintos, error claro
            raise ValueError(
                f"Header CSV no reconocido cerca de: {probe!r}. "
                f"Se esperaba una fila con {REQUIRED_CSV_FIELDS}"
            )

        reader = csv.DictReader(f, fieldnames=header)
        for row in reader:
            clean = {}
            for k, v in row.items():
                key = _normalize_header(k)
                if not key:
                    continue
                clean[key] = "" if v is None else str(v).strip()
            if not any(clean.values()) or str(clean.get("IdBanco", "")).lower() == "idbanco":
                continue
            yield clean


def parse_account_id(row: dict, fallback_idx: int) -> int:
    raw = str(row.get("NroCuenta", "")).strip()
    if not raw:
        return fallback_idx
    try:
        if "E+" in raw.upper() or "e+" in raw:
            return int(float(raw))
        return int(float(raw)) if "." in raw else int(raw)
    except ValueError:
        return fallback_idx


def validate_account_record(row: dict) -> tuple[bool, str]:
    """
    Validación estricta del dataset actualizado:
    Nro, Identificacion, Nombres, Apellidos, NroCuenta, IdBanco, Saldo
    """
    # 1. IdBanco (1..14)
    raw_b_id = str(row.get("IdBanco", "")).strip()
    try:
        b_id = int(float(raw_b_id))
        if not (1 <= b_id <= 14):
            return False, f"ID de Banco inválido ({raw_b_id})"
    except ValueError:
        return False, f"ID de Banco no numérico ({raw_b_id})"

    # 2. Saldo >= 0
    raw_saldo = str(row.get("Saldo", "")).strip()
    if not raw_saldo:
        return False, "Saldo vacío"
    try:
        saldo_val = float(raw_saldo)
        if math.isnan(saldo_val) or math.isinf(saldo_val):
            return False, "Saldo NaN/Infinito"
        if saldo_val < 0.0:
            return False, f"Saldo negativo ({saldo_val})"
    except ValueError:
        return False, f"Saldo contiene caracteres no numéricos ('{raw_saldo}')"

    # 3. NroCuenta
    raw_cuenta = str(row.get("NroCuenta", "")).strip()
    if not raw_cuenta:
        return False, "Número de Cuenta vacío"

    # 4. Nombres / Apellidos
    nombres = str(row.get("Nombres", "")).strip()
    apellidos = str(row.get("Apellidos", "")).strip()
    if not nombres and not apellidos:
        return False, "Nombre y Apellidos vacíos"

    # 5. Identificacion (opcional pero si viene, no vacía / no basura)
    ident = str(row.get("Identificacion", "")).strip()
    if "Identificacion" in row and ident == "":
        # Campo presente pero vacío
        return False, "Identificacion vacía"
    if ident:
        # Acepta dígitos (CI / NIT) o alfanumérico corto
        if len(ident) < 3:
            return False, f"Identificacion demasiado corta ({ident})"

    # 6. Nro (opcional; si viene debe ser numérico)
    nro = str(row.get("Nro", "")).strip()
    if nro:
        try:
            int(float(nro))
        except ValueError:
            return False, f"Nro no numérico ({nro})"

    return True, "OK"


def resolve_seed_sample_rate(percent=None) -> float:
    """
    Resuelve la fracción de muestra [0..1].
    - Si percent se pasa explícito: 100 -> 1.0, 5 -> 0.05, 0.01 -> 0.01
    - Si no: USE_FULL_DATASET=True => 1.0; si no => SEED_SAMPLE_PERCENT
    """
    from config import USE_FULL_DATASET, SEED_SAMPLE_PERCENT
    if percent is None:
        if USE_FULL_DATASET:
            return 1.0
        percent = SEED_SAMPLE_PERCENT
    rate = float(percent)
    if rate > 1.0:
        rate = rate / 100.0
    if rate <= 0:
        rate = 0.01
    return min(1.0, rate)


def _insert_account_job(row: dict, fallback_idx: int, bank_locks: dict, metrics: dict):
    banco_id = int(float(row["IdBanco"]))
    cuenta_id = parse_account_id(row, fallback_idx)
    nombres = str(row.get("Nombres", "")).strip()
    apellidos = str(row.get("Apellidos", "")).strip()
    cliente = f"{nombres} {apellidos}".strip() or f"Cliente_{cuenta_id}"
    saldo_usd = round(float(row["Saldo"]), 4)

    thread = threading.current_thread()
    with metrics["lock"]:
        metrics["active"] += 1
        metrics["peak"] = max(metrics["peak"], metrics["active"])
        metrics["workers"].add(thread.name)

    try:
        lock = bank_locks.get(banco_id)
        if lock:
            with lock:
                bank_db_manager.insert_encrypted_account(banco_id, cuenta_id, cliente, str(saldo_usd))
        else:
            bank_db_manager.insert_encrypted_account(banco_id, cuenta_id, cliente, str(saldo_usd))
        return True
    finally:
        with metrics["lock"]:
            metrics["active"] -= 1


def seed_bank_databases_from_csv(csv_path: str = "01 - Practica 2 Dataset.csv", sample_rate: float = None):
    import sqlite3
    from config import USE_FULL_DATASET

    if sample_rate is None:
        sample_rate = resolve_seed_sample_rate()
    elif sample_rate > 1.0:
        sample_rate = sample_rate / 100.0

    t0 = time.time()

    if os.path.exists(ASFI_DB_PATH):
        conn = sqlite3.connect(ASFI_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Cuentas")
        cursor.execute("DELETE FROM AuditLogs")
        conn.commit()
        conn.close()

    bank_db_manager._init_bank_stores(reset=True)

    if not os.path.exists(csv_path):
        from scripts.generate_sample_excel import generate_sample_excel
        csv_path = generate_sample_excel("cuentas_bancarias_muestra.csv")

    mode = "100% FULL DATASET" if sample_rate >= 1.0 or USE_FULL_DATASET else f"muestra {sample_rate * 100:.2f}%"
    print(f"📥 Leyendo dataset: '{csv_path}'... [{mode}]")
    print(f"   Campos aceptados: {', '.join(EXPECTED_CSV_FIELDS)}")

    bank_rows = defaultdict(list)
    total_rows_read = 0
    discarded_rows = []

    for row in iter_dataset_rows(csv_path):
        total_rows_read += 1
        is_valid, reason = validate_account_record(row)
        if is_valid:
            b_id = int(float(row["IdBanco"]))
            bank_rows[b_id].append(row)
        else:
            discarded_rows.append({"row": row, "reason": reason})

    sampled_records = []
    pct_display = sample_rate * 100
    print(f"📊 Muestra Estratificada ({pct_display:.2f}%) por Banco:")

    for b_id in sorted(bank_rows.keys()):
        rows = bank_rows[b_id]
        sample_n = len(rows) if sample_rate >= 1.0 else max(1, math.ceil(len(rows) * sample_rate))
        sampled_b = rows[:sample_n]
        sampled_records.extend(sampled_b)
        print(f"   - Banco #{b_id:2d}: {len(rows):5d} válidas -> Muestra ({pct_display:.2f}%): {len(sampled_b):4d} cuentas")

    cpu_cores = os.cpu_count() or 1
    max_workers = max(4, min(32, cpu_cores * 4))
    bank_locks = {b_id: threading.Lock() for b_id in range(1, 15)}
    metrics = {"lock": threading.Lock(), "active": 0, "peak": 0, "workers": set()}

    print(f"🧵 Carga multi-hilo: {max_workers} workers | {len(sampled_records)} cuentas")
    total_inserted = 0
    insert_errors = 0
    fallback_base = 100000

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ASFI-Seed") as pool:
        futures = {
            pool.submit(_insert_account_job, row, fallback_base + idx, bank_locks, metrics): idx
            for idx, row in enumerate(sampled_records)
        }
        for fut in as_completed(futures):
            try:
                if fut.result():
                    total_inserted += 1
            except Exception as ex:
                insert_errors += 1
                if insert_errors <= 5:
                    print(f"   ⚠️ Error insertando: {ex}")
            if total_inserted and total_inserted % 10000 == 0:
                print(f"   … insertadas {total_inserted}/{len(sampled_records)}")

    elapsed = round(time.time() - t0, 4)
    throughput = round(total_inserted / elapsed, 2) if elapsed > 0 else 0.0

    print(
        f"\n🎉 Seed completado: {total_inserted} cuentas | "
        f"leídas={total_rows_read} descartadas={len(discarded_rows)} errores={insert_errors} | "
        f"{elapsed}s | pico workers={metrics['peak']}/{max_workers} | {throughput} c/s\n"
    )
    return {
        "total_read": total_rows_read,
        "total_inserted": total_inserted,
        "discarded_count": len(discarded_rows),
        "discarded_sample": discarded_rows[:10],
        "sample_rate": sample_rate,
        "full_dataset": sample_rate >= 1.0,
        "accepted_fields": list(EXPECTED_CSV_FIELDS),
        "insert_errors": insert_errors,
        "performance": {
            "cpu_cores": cpu_cores,
            "max_workers": max_workers,
            "peak_concurrent_workers": metrics["peak"],
            "distinct_worker_threads": len(metrics["workers"]),
            "elapsed_seconds": elapsed,
            "throughput_accounts_per_sec": throughput,
            "execution_model": f"ThreadPoolExecutor(max_workers={max_workers}) + locks por banco",
        },
    }


# Alias para compatibilidad
seed_bank_databases_from_excel = seed_bank_databases_from_csv

if __name__ == "__main__":
    from config import USE_FULL_DATASET, SEED_SAMPLE_PERCENT

    parser = argparse.ArgumentParser(description="Poblador de BDs con Muestra Parametrizable de Dataset CSV")
    parser.add_argument("--percent", "-p", type=float, default=None,
                        help="Porcentaje de muestra (ej: 1, 5, 100). Si se omite, usa config.USE_FULL_DATASET / SEED_SAMPLE_PERCENT")
    parser.add_argument("--full", action="store_true", help="Forzar 100%% del dataset (igual que USE_FULL_DATASET=True)")
    parser.add_argument("--file", "-f", type=str, default="01 - Practica 2 Dataset.csv", help="Ruta del archivo CSV")
    args = parser.parse_args()

    if args.full:
        rate = 1.0
    elif args.percent is not None:
        rate = resolve_seed_sample_rate(args.percent)
    else:
        rate = resolve_seed_sample_rate()
        print(f"(config) USE_FULL_DATASET={USE_FULL_DATASET} SEED_SAMPLE_PERCENT={SEED_SAMPLE_PERCENT} -> rate={rate}")

    seed_bank_databases_from_csv(args.file, rate)
