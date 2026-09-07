"""
Parallel Sweeping Engine for ASFI Central (Tarea 8)
Desarrollo del motor de extracción asíncrona y concurrente:
- Conexión simultánea a las 14 entidades bancarias.
- Uso del mismo instante de referencia t₀ para evitar sesgo cambiario.
- Gestión de respuestas, excepciones y errores por banco.
- Consolidación centralizada de la información extraída.
"""

import asyncio
import time
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

    async def fetch_bank_data_async(self, bank_id: int, client = None):
        """
        Consulta asíncrona a un banco específico con gestión de errores y timeouts.
        Intenta vía API HTTP (si se especifica base_url); si falla o no está disponible,
        realiza la extracción directa de la capa de BD del banco en forma asíncrona.
        """
        if self.base_url and HAS_HTTPX and client:
            try:
                resp = await client.get(
                    f"{self.base_url}/api/bank/{bank_id}/accounts",
                    timeout=self.timeout
                )
                if resp.status_code == 200:
                    return {"bank_id": bank_id, "success": True, "accounts": resp.json()["cuentas"], "error": None}
                else:
                    return {"bank_id": bank_id, "success": False, "accounts": [], "error": f"HTTP {resp.status_code}"}
            except Exception as e:
                # Si falla HTTP, recurre al acceso a BD directa como respaldo
                pass

        try:
            # Extracción directa desde la BD del banco
            accounts = bank_db_manager.get_encrypted_accounts(bank_id)
            return {"bank_id": bank_id, "success": True, "accounts": accounts, "error": None}
        except Exception as ex:
            return {"bank_id": bank_id, "success": False, "accounts": [], "error": str(ex)}

    async def execute_parallel_sweep(self):
        """
        Ejecuta el barrido paralelo a los 14 bancos fijando un único tipo de cambio e instante de referencia t₀.
        Garantiza concurrencia con asyncio.gather y captura de excepciones por banco.
        """
        # 1. Fijar instante de referencia t0 y Tipo de Cambio BCB
        rate_info = bcb_engine.get_current_rate()
        t0_timestamp = rate_info["timestamp"]
        current_rate = rate_info["current_rate"]
        start_time = time.time()

        print(f"\n🚀 [BARRIDO PARALELO ASFI - TAREA 8] Iniciando extracción simultánea a los 14 bancos...")
        print(f"⏱️  Instante de Referencia (t₀): {t0_timestamp}")
        print(f"💵 Tipo de Cambio BCB fijado para el lote: {current_rate} BOB/USD\n")

        # 2. Crear las 14 tareas asíncronas concurrentes
        tasks = []
        if HAS_HTTPX and self.base_url:
            async with httpx.AsyncClient() as client:
                for b in BANKS:
                    bank_id = b["id"]
                    tasks.append(self.fetch_bank_data_async(bank_id, client))
                # Ejecución simultánea con captura de excepciones por banco
                raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            for b in BANKS:
                bank_id = b["id"]
                tasks.append(self.fetch_bank_data_async(bank_id))
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. Consolidar información y procesar saldos
        total_processed = 0
        successful_banks = 0
        failed_banks = 0
        all_transactions = []
        bank_summary = {}

        for idx, res in enumerate(raw_results, start=1):
            if isinstance(res, Exception):
                print(f"⚠️ [BANCO #{idx:2d}] Error en conexión asíncrona: {res}")
                failed_banks += 1
                bank_summary[idx] = {"success": False, "count": 0, "error": str(res)}
                continue

            bank_id = res.get("bank_id", idx)
            success = res.get("success", False)
            accounts = res.get("accounts", [])
            err = res.get("error")

            if not success:
                print(f"⚠️ [BANCO #{bank_id:2d}] Error durante la extracción: {err}")
                failed_banks += 1
                bank_summary[bank_id] = {"success": False, "count": 0, "error": err}
                continue

            successful_banks += 1
            bank_count = 0
            for acc in accounts:
                tx = asfi_process_engine.process_bank_account_payload(
                    bank_id=bank_id,
                    account_data=acc,
                    exchange_rate=current_rate
                )
                all_transactions.append(tx)
                bank_count += 1
                total_processed += 1

            bank_summary[bank_id] = {"success": True, "count": bank_count, "error": None}

        elapsed = round(time.time() - start_time, 4)
        print(f"✅ [BARRIDO PARALELO FINALIZADO]")
        print(f"   - Bancos Procesados Exitosamente: {successful_banks}/14")
        print(f"   - Cuentas Consolidadas en ASFI: {total_processed}")
        print(f"   - Tiempo Total de Extracción: {elapsed} segundos (en t₀={t0_timestamp})\n")

        return {
            "t0_timestamp": t0_timestamp,
            "elapsed_seconds": elapsed,
            "total_processed": total_processed,
            "successful_banks": successful_banks,
            "failed_banks": failed_banks,
            "exchange_rate": current_rate,
            "bank_summary": bank_summary,
            "transactions": all_transactions
        }

sweeper = ParallelBankSweeper()

