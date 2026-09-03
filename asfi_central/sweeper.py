"""
Parallel Sweeping Engine for ASFI Central.
Concurrently fetches encrypted accounts from all 14 banks using asyncio to eliminate BCB rate variation bias.
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
    def __init__(self, base_url: str = None):
        self.base_url = base_url

    async def fetch_bank_data_async(self, bank_id: int, client = None):
        """Si la API está corriendo en HTTP y httpx está instalado, realiza la llamada; de lo contrario, consulta la capa DB directamente en paralelo."""
        if self.base_url and HAS_HTTPX and client:
            try:
                resp = await client.get(f"{self.base_url}/api/bank/{bank_id}/accounts")
                if resp.status_code == 200:
                    return resp.json()["cuentas"]
            except Exception:
                pass

        # Direct in-memory / async DB reading fallback
        return bank_db_manager.get_encrypted_accounts(bank_id)

    async def execute_parallel_sweep(self):
        """Ejecuta el barrido paralelo a los 14 bancos fijando un único tipo de cambio en el instante de tiempo t0."""
        rate_info = bcb_engine.get_current_rate()
        current_rate = rate_info["current_rate"]
        start_time = time.time()

        print(f"\n🚀 [BARRIDO PARALELO ASFI] Iniciando barrido a los 14 bancos a las {rate_info['timestamp']}...")
        print(f"💵 Tipo de Cambio fijado para la corrida: {current_rate} BOB/USD")

        # Lanzar 14 tareas concurrentes en paralelo
        tasks = []
        if HAS_HTTPX and self.base_url:
            async with httpx.AsyncClient() as client:
                for b in BANKS:
                    bank_id = b["id"]
                    tasks.append(self.fetch_bank_data_async(bank_id, client))
                banks_results = await asyncio.gather(*tasks)
        else:
            for b in BANKS:
                bank_id = b["id"]
                tasks.append(self.fetch_bank_data_async(bank_id))
            banks_results = await asyncio.gather(*tasks)

        total_processed = 0
        all_transactions = []


        # Procesar los datos descifrándolos y convirtiéndolos a la cotización uniforme
        for bank_id, accounts in enumerate(banks_results, start=1):
            for acc in accounts:
                tx = asfi_process_engine.process_bank_account_payload(
                    bank_id=bank_id,
                    account_data=acc,
                    exchange_rate=current_rate
                )
                all_transactions.append(tx)
                total_processed += 1

        elapsed = round(time.time() - start_time, 4)
        print(f"✅ [BARRIDO PARALELO CONCLUIDO] {total_processed} cuentas de 14 bancos procesadas en {elapsed} segundos sin sesgo cambiario!\n")
        return {
            "elapsed_seconds": elapsed,
            "total_processed": total_processed,
            "exchange_rate": current_rate,
            "transactions": all_transactions
        }

sweeper = ParallelBankSweeper()
