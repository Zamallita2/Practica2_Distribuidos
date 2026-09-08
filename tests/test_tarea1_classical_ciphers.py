"""
Pruebas unitarias - Tarea 1: Cifrados Clasicos (Cesar, Atbash, Vigenere, Playfair, Hill).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crypto.classical import (
    CaesarCipher, AtbashCipher, VigenereCipher, PlayfairCipher, HillCipher,
)


class TestCaesarCipher(unittest.TestCase):
    def test_round_trip_text(self):
        cipher = CaesarCipher(shift=5)
        texto = "Banco Union S.A."
        self.assertEqual(cipher.decrypt(cipher.encrypt(texto)), texto)

    def test_round_trip_numeric_balance(self):
        cipher = CaesarCipher(shift=3)
        saldo = "1250.5000"
        self.assertEqual(cipher.decrypt(cipher.encrypt(saldo)), saldo)

    def test_shift_changes_text(self):
        cipher = CaesarCipher(shift=3)
        self.assertNotEqual(cipher.encrypt("ABC"), "ABC")


class TestAtbashCipher(unittest.TestCase):
    def test_is_self_inverse(self):
        cipher = AtbashCipher()
        texto = "Mercantil Santa Cruz"
        cifrado = cipher.encrypt(texto)
        self.assertEqual(cipher.encrypt(cifrado), texto)

    def test_round_trip_numeric_balance(self):
        cipher = AtbashCipher()
        saldo = "-348.2200"
        self.assertEqual(cipher.decrypt(cipher.encrypt(saldo)), saldo)


class TestVigenereCipher(unittest.TestCase):
    def test_round_trip_text(self):
        cipher = VigenereCipher(key="BANCOCENTRAL")
        texto = "Banco Nacional de Bolivia"
        self.assertEqual(cipher.decrypt(cipher.encrypt(texto)), texto)

    def test_round_trip_numeric_balance(self):
        cipher = VigenereCipher()
        saldo = "1498140.7654"
        self.assertEqual(cipher.decrypt(cipher.encrypt(saldo)), saldo)

    def test_empty_key_rejected(self):
        with self.assertRaises(ValueError):
            VigenereCipher(key="")


class TestPlayfairCipher(unittest.TestCase):
    def test_round_trip_grid_compatible_text(self):
        cipher = PlayfairCipher(key="ASFIBOLIVIA")
        texto = "CLIENTE 102938"
        self.assertEqual(cipher.decrypt(cipher.encrypt(texto)), texto)

    def test_round_trip_numeric_balance_with_repeated_digits(self):
        # "00" y otros digitos repetidos ejercitan la regla de relleno 'X'.
        cipher = PlayfairCipher()
        saldo = "1200.0000"
        self.assertEqual(cipher.decrypt(cipher.encrypt(saldo)), saldo)

    def test_encrypted_length_is_even(self):
        cipher = PlayfairCipher()
        cifrado = cipher.encrypt("349566")
        self.assertEqual(len(cifrado) % 2, 0)


class TestHillCipher(unittest.TestCase):
    def test_round_trip_text(self):
        cipher = HillCipher()
        texto = "Banco BISA S.A."
        self.assertEqual(cipher.decrypt(cipher.encrypt(texto)), texto)

    def test_round_trip_numeric_balance(self):
        cipher = HillCipher()
        saldo = "1048698.1234"
        self.assertEqual(cipher.decrypt(cipher.encrypt(saldo)), saldo)

    def test_rejects_non_invertible_matrix(self):
        # det = 2*4 - 4*2 = 0 -> gcd(0, 256) = 256, no invertible.
        with self.assertRaises(ValueError):
            HillCipher(key_matrix=[[2, 4], [4, 2]])


if __name__ == "__main__":
    unittest.main()
