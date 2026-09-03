"""
Unit tests for Cryptography Engine, BCB Engine, Bank DBs, and Parallel Sweeper.
"""

import unittest
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crypto import (
    CaesarCipher, AtbashCipher, VigenereCipher, PlayfairCipher, HillCipher,
    DESCipher, TripleDESCipher, BlowfishCipher, TwofishCipher, AESCipher, ChaCha20Cipher,
    RSACipher, ElGamalCipher, ECCCipher
)
from bcb_service.rate_engine import bcb_engine
from databases.seed_data import encrypt_balance, decrypt_balance
from asfi_central.sweeper import sweeper

class TestCryptoSuite(unittest.TestCase):
    def test_all_14_ciphers(self):
        sample_balance = 1250.50
        for bank_id in range(1, 15):
            enc = encrypt_balance(bank_id, sample_balance)
            dec = decrypt_balance(bank_id, enc)
            self.assertAlmostEqual(dec, sample_balance, places=1, msg=f"Error en cifrado Banco {bank_id}")

class TestBCBEngine(unittest.TestCase):
    def test_rate_precision_and_limits(self):
        rate_data = bcb_engine.get_current_rate()
        current_rate = rate_data["current_rate"]
        self.assertGreaterEqual(current_rate, 6.9600 - 0.9999)
        self.assertLessEqual(current_rate, 6.9600 + 0.9999)

class TestParallelSweep(unittest.TestCase):
    def test_sweeper_execution(self):
        from databases.seed_data import seed_bank_databases_from_excel
        seed_bank_databases_from_excel("cuentas_bancarias_muestra.csv")
        async def run_sweep():
            return await sweeper.execute_parallel_sweep()
        res = asyncio.run(run_sweep())
        self.assertGreater(res["total_processed"], 0)

if __name__ == "__main__":
    unittest.main()
