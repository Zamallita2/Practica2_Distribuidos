"""
Unit tests for Tarea 7: Base de Datos Central ASFI
"""

import unittest
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from databases.asfi_db import ASFICentralDatabase

class TestTarea7ASFICentralDB(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db = ASFICentralDatabase(db_path=self.temp_db.name)

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

    def test_bancos_catalog(self):
        bancos = self.db.get_bancos()
        self.assertEqual(len(bancos), 14, "Debe haber exactamente 14 bancos en el catálogo")
        b1 = self.db.get_banco_by_id(1)
        self.assertIsNotNone(b1)
        self.assertEqual(b1["nombre"], "Banco Unión S.A.")
        self.assertEqual(b1["algoritmo"], "César")

    def test_cuentas_and_audit_logs_management(self):
        cuenta_id = 999999
        banco_id = 1
        saldo_usd = 1500.00
        saldo_bs = 10440.00
        exchange_rate = 6.9600
        verification_code = "A1B2C3D4"

        # Registrar transacción
        self.db.record_transaction(
            cuenta_id=cuenta_id,
            banco_id=banco_id,
            saldo_usd=saldo_usd,
            saldo_bs=saldo_bs,
            exchange_rate=exchange_rate,
            verification_code=verification_code
        )

        # Verificar consulta de cuenta
        acc = self.db.get_account_by_id(cuenta_id)
        self.assertIsNotNone(acc)
        self.assertEqual(acc[0], cuenta_id)
        self.assertEqual(acc[1], banco_id)
        self.assertEqual(acc[2], saldo_usd)
        self.assertEqual(acc[3], saldo_bs)
        self.assertEqual(acc[5], verification_code)

        # Verificar consulta de audit logs
        logs = self.db.get_audit_logs()
        self.assertGreater(len(logs), 0)
        self.assertEqual(logs[0][3], cuenta_id)
        self.assertEqual(logs[0][4], banco_id)

if __name__ == "__main__":
    unittest.main()
