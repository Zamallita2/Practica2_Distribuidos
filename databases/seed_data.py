"""
Data Ingestion and Population Script for 14 Bank Databases.
Reads 01 - Practica 2 Dataset.csv, performs stratified sampling per bank,
encrypts sensitive balances using assigned algorithms, and seeds databases.
"""

import os
import csv
import math
import sys
import argparse
from collections import defaultdict
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

def parse_account_id(row: dict, fallback_idx: int) -> int:
    raw = str(row.get("NroCuenta", "")).strip()
    if not raw:
        return fallback_idx
    try:
        if 'E+' in raw or 'e+' in raw:
            return int(float(raw))
        return int(raw)
    except ValueError:
        return fallback_idx

def seed_bank_databases_from_csv(csv_path: str = "01 - Practica 2 Dataset.csv", sample_rate: float = 0.01):
    import sqlite3
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

    print(f"📥 Leyendo dataset original: '{csv_path}'...")
    bank_rows = defaultdict(list)
    
    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                b_id = int(row["IdBanco"])
                bank_rows[b_id].append(row)
            except (ValueError, KeyError):
                continue

    sampled_records = []
    pct_display = sample_rate * 100 if sample_rate <= 1.0 else sample_rate
    print(f"📊 Muestra Estratificada ({pct_display:.2f}%) por Banco:")
    
    for b_id in sorted(bank_rows.keys()):
        rows = bank_rows[b_id]
        sample_n = max(1, math.ceil(len(rows) * sample_rate))
        sampled_b = rows[:sample_n]
        sampled_records.extend(sampled_b)
        print(f"   - Banco #{b_id:2d}: {len(rows):5d} totales -> Muestra ({pct_display:.2f}%): {len(sampled_b):4d} cuentas")

    total_inserted = 0
    fallback_counter = 100000

    for row in sampled_records:
        banco_id = int(row["IdBanco"])
        cuenta_id = parse_account_id(row, fallback_counter)
        fallback_counter += 1
        
        nombres = str(row.get("Nombres", "")).strip()
        apellidos = str(row.get("Apellidos", "")).strip()
        cliente = f"{nombres} {apellidos}".strip() or f"Cliente_{cuenta_id}"
        
        try:
            saldo_usd = round(float(row["Saldo"]), 4)
        except (ValueError, KeyError):
            saldo_usd = 1000.00

        saldo_cifrado = encrypt_balance(banco_id, saldo_usd)
        bank_db_manager.insert_encrypted_account(banco_id, cuenta_id, cliente, saldo_cifrado)
        total_inserted += 1

    print(f"\n🎉 ¡Población de datos completada! Se ingresaron {total_inserted} cuentas en las 14 bases de datos bancarias.\n")

# Alias para compatibilidad
seed_bank_databases_from_excel = seed_bank_databases_from_csv

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Poblador de BDs con Muestra Parametrizable de Dataset CSV")
    parser.add_argument("--percent", "-p", type=float, default=1.0, help="Porcentaje de muestra (ej: 1.0 para 1%%, 2.5 para 2.5%%, 5.0 para 5%%)")
    parser.add_argument("--file", "-f", type=str, default="01 - Practica 2 Dataset.csv", help="Ruta del archivo CSV")
    args = parser.parse_args()

    rate = args.percent / 100.0 if args.percent >= 1.0 else args.percent
    if rate <= 0:
        rate = 0.01

    seed_bank_databases_from_csv(args.file, rate)
