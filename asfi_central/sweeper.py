"""
Parallel Sweeping Engine for ASFI Central (Tarea 8)
Desarrollo del motor de extracción asíncrona y concurrente:
- Conexión simultánea a las 14 entidades bancarias.
- Uso del mismo instante de referencia t₀ para evitar sesgo cambiario.
- Gestión de respuestas, excepciones y errores por banco.
- Consolidación centralizada de la información extraída.
- Procesamiento multi-hilo de conversiones (ThreadPoolExecutor) con métricas de rendimiento.
"""

import asyncio
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import BANKS
from bcb_service.rate_engine import bcb_engine
from asfi_central.process_engine import asfi_process_engine
from databases.bank_dbs import bank_db_manager

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class ParallelBankSweeper:
    def __init__(self, base_url: str = None, timeout: float = 5.0):
        self.base_url = base_url
        self.timeout = timeout

    def _fetch_bank_data_sync(self, bank_id: int):
        """Extracción síncrona desde la BD del banco (ejecutada en hilo / to_thread)."""
        from databases.seed_data import encrypt_balance
        raw_accounts = bank_db_manager.get_encrypted_accounts(bank_id)
        accounts = []
        for acc in raw_accounts:
            try:
                saldo_usd_val = float(acc.get("saldo_usd_cifrado", 0.0))
                cifrado = encrypt_balance(bank_id, saldo_usd_val)
            except (ValueError, TypeError):
                cifrado = acc.get("saldo_usd_cifrado", "0.0")

            accounts.append({
                "cuenta_id": acc["cuenta_id"],
                "cliente_nombre": acc.get("cliente_nombre", ""),
                "saldo_usd_cifrado": cifrado,
                "saldo_usd_plano": acc.get("saldo_usd_cifrado", "0.0"),
                "saldo_bs": acc.get("saldo_bs", 0.0),
                "codigo_verificacion": acc.get("codigo_verificacion", "")
            })
        return {"bank_id": bank_id, "success": True, "accounts": accounts, "error": None}

    async def fetch_bank_data_async(self, bank_id: int, client=None):
        """
        Consulta asíncrona a un banco específico con gestión de errores y timeouts.
        Intenta vía API HTTP (si se especifica base_url); si falla o no está disponible,
        realiza la extracción directa de la capa de BD del banco en un hilo de trabajo.
        """
        if self.base_url and HAS_HTTPX and client:
            try:
                resp = await client.get(
                    f"{self.base_url}/api/bank/{bank_id}/accounts",
                    timeout=self.timeout
                )
                if resp.status_code == 200:
                    return {"bank_id": bank_id, "success": True, "accounts": resp.json()["cuentas"], "error": None}
            except Exception:
                pass

        try:
            return await asyncio.to_thread(self._fetch_bank_data_sync, bank_id)
        except Exception as ex:
            return {"bank_id": bank_id, "success": False, "accounts": [], "error": str(ex)}

    def _process_account_job(self, bank_id, acc, use_dynamic_rate, initial_rate, update_bank_db, metrics):
        """Un cálculo de conversión en un worker del pool (prueba de multi-hilo)."""
        thread = threading.current_thread()
        with metrics["lock"]:
            metrics["active_workers"] += 1
            metrics["peak_workers"] = max(metrics["peak_workers"], metrics["active_workers"])
            metrics["worker_names"].add(thread.name)
            metrics["worker_idents"].add(thread.ident)
        try:
            active_rate = None if use_dynamic_rate else initial_rate
            return asfi_process_engine.process_bank_account_payload(
                bank_id=bank_id,
                account_data=acc,
                exchange_rate=active_rate,
                update_bank_db=update_bank_db,
            )
        finally:
            with metrics["lock"]:
                metrics["active_workers"] -= 1

    async def execute_parallel_sweep(self, use_dynamic_rate: bool = False, update_bank_db: bool = True, reset_first: bool = False):
        """
        Ejecuta el barrido paralelo a los 14 bancos.
        - reset_first: Si es True, limpia y vuelve a cargar los saldos originales en Dólares en los bancos.
        - update_bank_db: Si es True, actualiza los nuevos saldos en Bs y códigos 8-Hex en los bancos.
        """
        if reset_first:
            from databases.seed_data import seed_bank_databases_from_csv
            seed_bank_databases_from_csv("01 - Practica 2 Dataset.csv", 0.01)

        rate_info = bcb_engine.get_current_rate()
        t0_timestamp = rate_info["timestamp"]
        initial_rate = rate_info["current_rate"]
        start_time = time.time()
        cpu_cores = os.cpu_count() or 1
        max_calc_workers = max(4, min(32, cpu_cores * 4))

        print(f"\n🚀 [BARRIDO PARALELO ASFI - TAREA 8] Iniciando extracción simultánea a los 14 bancos...")
        print(f"⏱️  Instante de Referencia (t₀): {t0_timestamp}")
        print(f"💵 Tipo de Cambio BCB inicial: {initial_rate} BOB/USD (Modo Dinámico: {use_dynamic_rate})")
        print(f"🧵 Núcleos CPU: {cpu_cores} | Workers de cálculo: {max_calc_workers}\n")

        # --- Fase 1: extracción concurrente (14 tareas asyncio + hilos para I/O de BD) ---
        fetch_start = time.time()
        if HAS_HTTPX and self.base_url:
            async with httpx.AsyncClient() as client:
                tasks = [self.fetch_bank_data_async(b["id"], client) for b in BANKS]
                raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            tasks = [self.fetch_bank_data_async(b["id"]) for b in BANKS]
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        fetch_elapsed = round(time.time() - fetch_start, 4)

        # --- Fase 2: conversión multi-hilo (varios cálculos a la vez) ---
        metrics = {
            "lock": threading.Lock(),
            "active_workers": 0,
            "peak_workers": 0,
            "worker_names": set(),
            "worker_idents": set(),
        }
        total_processed = 0
        successful_banks = 0
        failed_banks = 0
        all_transactions = []
        bank_summary = {}
        jobs = []

        for idx, res in enumerate(raw_results, start=1):
            if isinstance(res, Exception):
                print(f"⚠️ [BANCO #{idx:2d}] Error en conexión asíncrona: {res}")
                failed_banks += 1
                bank_summary[idx] = {"success": False, "count": 0, "error": str(res), "elapsed_seconds": 0}
                continue

            bank_id = res.get("bank_id", idx)
            success = res.get("success", False)
            accounts = res.get("accounts", [])
            err = res.get("error")

            if not success:
                print(f"⚠️ [BANCO #{bank_id:2d}] Error durante la extracción: {err}")
                failed_banks += 1
                bank_summary[bank_id] = {"success": False, "count": 0, "error": err, "elapsed_seconds": 0}
                continue

            successful_banks += 1
            bank_summary[bank_id] = {"success": True, "count": len(accounts), "error": None, "elapsed_seconds": 0}
            for acc in accounts:
                jobs.append((bank_id, acc))

        process_start = time.time()
        threads_before = threading.active_count()

        with ThreadPoolExecutor(max_workers=max_calc_workers, thread_name_prefix="ASFI-Calc") as pool:
            futures = {
                pool.submit(
                    self._process_account_job,
                    bank_id, acc, use_dynamic_rate, initial_rate, update_bank_db, metrics,
                ): bank_id
                for bank_id, acc in jobs
            }
            threads_during = threading.active_count()
            bank_counts = {b["id"]: 0 for b in BANKS}
            bank_errors = {}

            for fut in as_completed(futures):
                bank_id = futures[fut]
                try:
                    tx = fut.result()
                    all_transactions.append(tx)
                    bank_counts[bank_id] = bank_counts.get(bank_id, 0) + 1
                    total_processed += 1
                except Exception as ex:
                    bank_errors[bank_id] = str(ex)

        process_elapsed = round(time.time() - process_start, 4)
        elapsed = round(time.time() - start_time, 4)
        throughput = round(total_processed / process_elapsed, 2) if process_elapsed > 0 else 0.0

        for bank_id, count in bank_counts.items():
            if bank_id in bank_summary and bank_summary[bank_id].get("success"):
                bank_summary[bank_id]["count"] = count
                bank_summary[bank_id]["elapsed_seconds"] = process_elapsed
                if bank_id in bank_errors:
                    bank_summary[bank_id]["error"] = bank_errors[bank_id]

        performance = {
            "cpu_cores": cpu_cores,
            "max_calc_workers": max_calc_workers,
            "peak_concurrent_workers": metrics["peak_workers"],
            "distinct_worker_threads": len(metrics["worker_idents"]),
            "worker_thread_samples": sorted(metrics["worker_names"])[:12],
            "os_threads_before": threads_before,
            "os_threads_during_peak_sample": threads_during,
            "os_threads_after": threading.active_count(),
            "parallel_bank_fetch_tasks": len(BANKS),
            "fetch_elapsed_seconds": fetch_elapsed,
            "process_elapsed_seconds": process_elapsed,
            "throughput_accounts_per_sec": throughput,
            "execution_model": (
                f"asyncio.gather({len(BANKS)} bancos) + "
                f"ThreadPoolExecutor(max_workers={max_calc_workers}) para conversiones concurrentes"
            ),
        }

        print(f"✅ [BARRIDO PARALELO FINALIZADO]")
        print(f"   - Bancos Procesados Exitosamente: {successful_banks}/14")
        print(f"   - Cuentas Consolidadas en ASFI: {total_processed}")
        print(f"   - Tiempo Total: {elapsed}s | Fetch: {fetch_elapsed}s | Cálculo: {process_elapsed}s")
        print(f"   - Pico workers concurrentes: {metrics['peak_workers']}/{max_calc_workers} | Throughput: {throughput} cuentas/s")
        print(f"   - Hilos worker distintos: {len(metrics['worker_idents'])} | CPU cores: {cpu_cores}\n")

        return {
            "t0_timestamp": t0_timestamp,
            "elapsed_seconds": elapsed,
            "total_processed": total_processed,
            "successful_banks": successful_banks,
            "failed_banks": failed_banks,
            "exchange_rate": initial_rate,
            "bank_summary": bank_summary,
            "transactions": all_transactions,
            "performance": performance,
        }


sweeper = ParallelBankSweeper()
