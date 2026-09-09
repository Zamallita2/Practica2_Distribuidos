"""
Unit tests for Tarea 8: Motor de Barrido Paralelo Asíncrono
"""

import unittest
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from databases.seed_data import seed_bank_databases_from_csv
from asfi_central.sweeper import ParallelBankSweeper, sweeper

class TestTarea8ParallelSweeper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Poblar las bases de datos para garantizar cuentas disponibles
        seed_bank_databases_from_csv("01 - Practica 2 Dataset.csv", sample_rate=0.01)

    def test_parallel_sweep_execution(self):
        async def run():
            return await sweeper.execute_parallel_sweep()

        res = asyncio.run(run())
        self.assertIn("t0_timestamp", res)
        self.assertIn("exchange_rate", res)
        self.assertEqual(res["successful_banks"], 14, "Los 14 bancos deben responder exitosamente")
        self.assertGreater(res["total_processed"], 0, "Debe haber procesado cuentas de ahorristas")
        
        # Verificar que TODAS las transacciones del lote usen la misma cotización en t0
        t0_rate = res["exchange_rate"]
        for tx in res["transactions"]:
            self.assertEqual(tx["tipo_cambio"], t0_rate, "Todas las transacciones deben usar la cotización exacta en t0")

    def test_sweeper_error_resilience(self):
        """Verifica que el barrido paralelo tolere fallos individuales de bancos sin caerse."""
        sweeper_with_bad_url = ParallelBankSweeper(base_url="http://invalid-bank-host-9999.local")
        async def run_resilient():
            return await sweeper_with_bad_url.execute_parallel_sweep()

        # Debe responder usando el fallback interno sin lanzar excepción irrecoverable
        res = asyncio.run(run_resilient())
        self.assertIsNotNone(res)
        self.assertEqual(res["successful_banks"], 14)

if __name__ == "__main__":
    unittest.main()
