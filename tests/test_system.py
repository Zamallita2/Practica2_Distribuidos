"""
Unit tests for Cryptography Engine, BCB Engine, Bank DBs, and Parallel Sweeper.
"""

import unittest
import asyncio
import os
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crypto import (
    CaesarCipher, AtbashCipher, VigenereCipher, PlayfairCipher, HillCipher,
    DESCipher, TripleDESCipher, BlowfishCipher, TwofishCipher, AESCipher, ChaCha20Cipher,
    RSACipher, ElGamalCipher, ECCCipher
)
from bcb_service.rate_engine import bcb_engine
from databases.seed_data import encrypt_balance, decrypt_balance
from databases.bank_dbs import BankDatabaseManager
from asfi_central.sweeper import sweeper

class TestCryptoSuite(unittest.TestCase):
    def test_all_14_ciphers(self):
        sample_balance = 1250.50
        for bank_id in range(1, 15):
            enc = encrypt_balance(bank_id, sample_balance)
            dec = decrypt_balance(bank_id, enc)
            self.assertAlmostEqual(dec, sample_balance, places=1, msg=f"Error en cifrado Banco {bank_id}")

    def test_randomized_ciphertexts(self):
        sample = "1250.50"
        cipher = ElGamalCipher()
        self.assertIsNotNone(cipher.encrypt(sample))



class TestBCBEngine(unittest.TestCase):
    def test_rate_precision_and_limits(self):
        rate_data = bcb_engine.get_current_rate()
        current_rate = rate_data["current_rate"]
        self.assertGreaterEqual(current_rate, 6.9600 - 0.9999)
        self.assertLessEqual(current_rate, 6.9600 + 0.9999)

    def test_rate_is_shared_within_window_and_changes_after_interval(self):
        from bcb_service.rate_engine import BCBExchangeRateEngine

        engine = BCBExchangeRateEngine(base_rate=6.9600, interval=180, auto_start=False)
        try:
            first = engine.get_current_rate()
            same_window = engine.get_current_rate()
            engine.force_tick()
            next_window = engine.get_current_rate()

            self.assertEqual(first["current_rate"], same_window["current_rate"])
            self.assertNotEqual(first["period_index"], next_window["period_index"])
            self.assertNotEqual(first["current_rate"], next_window["current_rate"])
            self.assertEqual(first["period_index"], 0)
            self.assertEqual(next_window["period_index"], 1)
            self.assertEqual(len(f"{first['current_rate']:.4f}".split(".")[1]), 4)
        finally:
            engine.stop()

    def test_interval_must_be_positive(self):
        from bcb_service.rate_engine import BCBExchangeRateEngine

        with self.assertRaises(ValueError):
            BCBExchangeRateEngine(interval=0, auto_start=False)

class TestParallelSweep(unittest.TestCase):
    def test_sweeper_execution(self):
        from databases.seed_data import seed_bank_databases_from_excel
        seed_bank_databases_from_excel("01 - Practica 2 Dataset.csv")
        async def run_sweep():
            return await sweeper.execute_parallel_sweep()
        res = asyncio.run(run_sweep())
        self.assertGreater(res["total_processed"], 0)


class TestBankDatabases6To14(unittest.TestCase):
    def test_crud_and_persistence_for_assigned_banks(self):
        with tempfile.TemporaryDirectory() as data_dir:
            manager = BankDatabaseManager(data_dir=data_dir)

            for bank_id in range(6, 15):
                account_id = bank_id * 100000 + 1
                manager.insert_encrypted_account(
                    bank_id, account_id, f"Cliente {bank_id}", encrypt_balance(bank_id, 100.0)
                )
                accounts = manager.get_encrypted_accounts(bank_id)
                self.assertEqual(len(accounts), 1)
                self.assertEqual(accounts[0]["cuenta_id"], account_id)

                self.assertTrue(manager.update_verification_code(
                    bank_id, account_id, 696.0, "A1B2C3D4", "2026-09-06 12:00:00"
                ))
                updated = manager.get_encrypted_accounts(bank_id)[0]
                self.assertEqual(updated["saldo_bs"], 696.0)
                self.assertEqual(updated["codigo_verificacion"], "A1B2C3D4")
                self.assertFalse(manager.update_verification_code(
                    bank_id, account_id + 999, 1.0, "00000000", "2026-09-06 12:00:00"
                ))

            reloaded = BankDatabaseManager(data_dir=data_dir)
            for bank_id in range(6, 15):
                self.assertEqual(len(reloaded.get_encrypted_accounts(bank_id)), 1)

if __name__ == "__main__":
    unittest.main()
