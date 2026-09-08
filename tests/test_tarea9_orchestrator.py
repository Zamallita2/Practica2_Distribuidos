"""
Unit tests for Tarea 9: Orquestador Central y Flujo Completo ASFI
"""

import unittest
import re
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from databases.seed_data import seed_bank_databases_from_csv
from asfi_central.process_engine import asfi_process_engine
from config import AUDIT_LOG_FILE

class TestTarea9Orchestrator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_bank_databases_from_csv("01 - Practica 2 Dataset.csv", sample_rate=0.01)

    def test_hex_verification_code_format(self):
        """Verifica que el código de verificación tenga 8 caracteres hexadecimales (0–9, A–F)."""
        code = asfi_process_engine.generate_verification_code()
        self.assertEqual(len(code), 8)
        self.assertTrue(bool(re.match(r'^[0-9A-F]{8}$', code)), f"El código {code} debe ser de 8 caracteres hexadecimales")

    def test_process_account_payload_and_audit_log(self):
        """Verifica el descifrado, conversión a BOB, persistencia DB y registro en archivo físico de auditoría."""
        from databases.seed_data import encrypt_balance
        from databases.bank_dbs import bank_db_manager
        
        enc_balance = encrypt_balance(1, 1250.50)
        bank_db_manager.insert_encrypted_account(1, 999901, "Cliente Test", enc_balance)

        sample_payload = {
            "cuenta_id": 999901,
            "saldo_usd_cifrado": enc_balance
        }

        tx = asfi_process_engine.process_bank_account_payload(
            bank_id=1,
            account_data=sample_payload,
            exchange_rate=6.9600
        )


        self.assertEqual(tx["cuenta_id"], 999901)
        self.assertEqual(tx["banco_id"], 1)
        self.assertEqual(tx["saldo_usd"], 1250.50)
        self.assertEqual(tx["saldo_bs"], round(1250.50 * 6.9600, 4))
        self.assertEqual(len(tx["codigo_verificacion"]), 8)
        self.assertTrue(tx["banco_sincronizado"])

        # Verificar existencia del archivo de auditoría física asfi_audit.log
        self.assertTrue(os.path.exists(AUDIT_LOG_FILE), "El archivo asfi_audit.log debe existir")

    def test_full_orchestration_cycle(self):
        """Verifica la coordinación completa entre ASFI, BCB y los 14 bancos."""
        orchestrator_result = asfi_process_engine.run_full_orchestration_cycle()
        
        self.assertIn("rate_info", orchestrator_result)
        self.assertIn("sweep_result", orchestrator_result)
        self.assertGreater(orchestrator_result["verified_consistent"], 0, "Debe haber verificado cuentas consistentes entre ASFI y Bancos")

if __name__ == "__main__":
    unittest.main()
