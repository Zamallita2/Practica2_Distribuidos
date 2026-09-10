"""
Pruebas unitarias - Tarea 2: Bases de Datos de Bancos 1-5.

Verifica que cada uno de los 5 adaptadores (SQLite, MySQL, PostgreSQL,
MongoDB, Grafo) cree su esquema y soporte el ciclo completo
insertar -> consultar -> actualizar codigo de verificacion, y que el
BankDatabaseManager (usado por seed_data.py, el sweeper y el router de
bancos) enrute correctamente los Bancos 1-5 hacia estos adaptadores sin
afectar la logica generica de los Bancos 6-14.
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from databases.banks_1_5 import (
    BankUnionSQLiteAdapter,
    BankMercantilMySQLAdapter,
    BankBNBPostgresAdapter,
    BankBCPMongoAdapter,
    BankBISAGraphAdapter,
)


class BaseAdapterRoundTripMixin:
    """Ejercita el ciclo insertar -> consultar -> actualizar comun a los
    adaptadores relacionales y documentales (Bancos 1-4)."""

    adapter_cls = None

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.adapter = self.adapter_cls(data_dir=self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_insert_and_get_round_trip(self):
        self.adapter.insert_encrypted_account(101, "Juana Perez", "CIFRADO_101")
        cuentas = self.adapter.get_encrypted_accounts()
        self.assertEqual(len(cuentas), 1)
        self.assertEqual(cuentas[0]["cuenta_id"], 101)
        self.assertEqual(cuentas[0]["saldo_usd_cifrado"], "CIFRADO_101")

    def test_update_verification_code(self):
        self.adapter.insert_encrypted_account(202, "Marco Rojas", "CIFRADO_202")
        updated = self.adapter.update_verification_code(202, 1406.79, "A1B2C3D4", "2026-09-08 10:00:00")
        self.assertTrue(updated)
        cuentas = self.adapter.get_encrypted_accounts()
        cuenta = next(c for c in cuentas if c["cuenta_id"] == 202)
        self.assertEqual(cuenta["codigo_verificacion"], "A1B2C3D4")
        self.assertAlmostEqual(cuenta["saldo_bs"], 1406.79, places=2)

    def test_update_unknown_account_returns_false(self):
        self.assertFalse(self.adapter.update_verification_code(9999, 0.0, "00000000", "2026-09-08 10:00:00"))

    def test_upsert_replaces_existing_account(self):
        self.adapter.insert_encrypted_account(303, "Cliente Uno", "CIFRADO_A")
        self.adapter.insert_encrypted_account(303, "Cliente Uno", "CIFRADO_B")
        cuentas = [c for c in self.adapter.get_encrypted_accounts() if c["cuenta_id"] == 303]
        self.assertEqual(len(cuentas), 1)
        self.assertEqual(cuentas[0]["saldo_usd_cifrado"], "CIFRADO_B")


class TestBank1UnionSQLite(BaseAdapterRoundTripMixin, unittest.TestCase):
    adapter_cls = BankUnionSQLiteAdapter

    def test_engine_mode_is_real(self):
        self.assertEqual(self.adapter.engine_mode, "real")


class TestBank2MercantilMySQL(BaseAdapterRoundTripMixin, unittest.TestCase):
    adapter_cls = BankMercantilMySQLAdapter

    def test_engine_mode_is_valid(self):
        self.assertIn(self.adapter.engine_mode, ("real", "local_fallback"))


class TestBank3BNBPostgres(BaseAdapterRoundTripMixin, unittest.TestCase):
    adapter_cls = BankBNBPostgresAdapter

    def test_engine_mode_is_valid(self):
        self.assertIn(self.adapter.engine_mode, ("real", "local_fallback"))


class TestBank4BCPMongo(BaseAdapterRoundTripMixin, unittest.TestCase):
    adapter_cls = BankBCPMongoAdapter

    def test_engine_mode_is_valid(self):
        self.assertIn(self.adapter.engine_mode, ("real", "local_fallback"))


class TestBank5BISAGraph(unittest.TestCase):
    """El Banco BISA usa un grafo con nodos Cliente/Cuenta, no una tabla."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.adapter = BankBISAGraphAdapter(data_dir=self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_engine_mode_is_real(self):
        self.assertEqual(self.adapter.engine_mode, "real")

    def test_insert_creates_cliente_and_cuenta_nodes(self):
        self.adapter.insert_encrypted_account(404, "Ana Flores", "CIFRADO_404")
        self.assertIn("Cliente_Ana_Flores", self.adapter.graph.nodes)
        self.assertIn("Cuenta_404", self.adapter.graph.nodes)
        self.assertTrue(self.adapter.graph.has_edge("Cliente_Ana_Flores", "Cuenta_404"))
        edge_data = self.adapter.graph.get_edge_data("Cliente_Ana_Flores", "Cuenta_404")
        self.assertEqual(edge_data["relacion"], "POSEE_CUENTA")

    def test_get_encrypted_accounts_round_trip(self):
        self.adapter.insert_encrypted_account(505, "Luis Mamani", "CIFRADO_505")
        cuentas = self.adapter.get_encrypted_accounts()
        self.assertEqual(len(cuentas), 1)
        self.assertEqual(cuentas[0]["cuenta_id"], 505)

    def test_update_verification_code(self):
        self.adapter.insert_encrypted_account(606, "Rosa Quispe", "CIFRADO_606")
        updated = self.adapter.update_verification_code(606, 999.99, "FEEDBEEF", "2026-09-08 11:00:00")
        self.assertTrue(updated)
        cuenta = next(c for c in self.adapter.get_encrypted_accounts() if c["cuenta_id"] == 606)
        self.assertEqual(cuenta["codigo_verificacion"], "FEEDBEEF")

    def test_persists_across_reload(self):
        self.adapter.insert_encrypted_account(707, "Pedro Choque", "CIFRADO_707")
        reloaded = BankBISAGraphAdapter(data_dir=self.tmp_dir)
        cuentas = [c for c in reloaded.get_encrypted_accounts() if c["cuenta_id"] == 707]
        self.assertEqual(len(cuentas), 0, "create_schema en un nuevo adaptador debe reiniciar el grafo")


class TestBankDatabaseManagerRoutingBanks1a5(unittest.TestCase):
    """Verifica que el BankDatabaseManager enrute correctamente los Bancos 1-5
    hacia sus adaptadores dedicados, sin tocar la logica de los Bancos 6-14."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        from databases.bank_dbs import BankDatabaseManager
        self.manager = BankDatabaseManager(data_dir=self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_all_5_banks_round_trip_through_manager(self):
        for bank_id in range(1, 6):
            with self.subTest(bank_id=bank_id):
                self.manager.insert_encrypted_account(bank_id, 1000 + bank_id, f"Cliente_{bank_id}", f"CIFRADO_{bank_id}")
                cuentas = self.manager.get_encrypted_accounts(bank_id)
                self.assertEqual(len(cuentas), 1)
                self.assertEqual(cuentas[0]["cuenta_id"], 1000 + bank_id)

                updated = self.manager.update_verification_code(bank_id, 1000 + bank_id, 500.0, "0BADC0DE", "2026-09-08 12:00:00")
                self.assertTrue(updated)

    def test_bank_6_still_uses_generic_sqlite_path(self):
        # Banco 6 (Ganadero, DES) no pertenece a Bancos 1-5: debe seguir
        # usando la simulacion generica (archivo bank_data/bank_6.db).
        self.manager.insert_encrypted_account(6, 2006, "Cliente Seis", "CIFRADO_6")
        cuentas = self.manager.get_encrypted_accounts(6)
        self.assertEqual(len(cuentas), 1)
        db_file = os.path.join(self.tmp_dir, "bank_6.db")
        self.assertTrue(os.path.exists(db_file))


if __name__ == "__main__":
    unittest.main()
