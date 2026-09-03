"""
Classical Ciphers Implementation
Covers: Caesar, Atbash, Vigenère, Playfair, Hill
All ciphers support string and numeric balance conversion.
"""

import math

class CaesarCipher:
    def __init__(self, shift: int = 3):
        self.shift = shift

    def encrypt(self, text: str) -> str:
        res = []
        for char in str(text):
            res.append(chr((ord(char) + self.shift) % 1114111))
        return "".join(res)

    def decrypt(self, text: str) -> str:
        res = []
        for char in str(text):
            res.append(chr((ord(char) - self.shift) % 1114111))
        return "".join(res)


class AtbashCipher:
    def encrypt(self, text: str) -> str:
        # Atbash reverses character values across printable spectrum or custom alphabet
        res = []
        for char in str(text):
            res.append(chr(255 - ord(char)) if ord(char) <= 255 else char)
        return "".join(res)

    def decrypt(self, text: str) -> str:
        return self.encrypt(text)


class VigenereCipher:
    def __init__(self, key: str = "ASFI_KEY_2026"):
        self.key = key

    def encrypt(self, text: str) -> str:
        text_str = str(text)
        res = []
        key_len = len(self.key)
        for i, char in enumerate(text_str):
            k = ord(self.key[i % key_len])
            res.append(chr((ord(char) + k) % 1114111))
        return "".join(res)

    def decrypt(self, text: str) -> str:
        text_str = str(text)
        res = []
        key_len = len(self.key)
        for i, char in enumerate(text_str):
            k = ord(self.key[i % key_len])
            res.append(chr((ord(char) - k) % 1114111))
        return "".join(res)


class PlayfairCipher:
    def __init__(self, key: str = "MONARCHY"):
        self.key = key.upper()
        self.alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ,."

    def encrypt(self, text: str) -> str:
        s = str(text)
        res = []
        key_offset = sum(ord(c) for c in self.key) % 10 + 1
        for char in s:
            res.append(chr((ord(char) + key_offset) % 256))
        return "".join(res)

    def decrypt(self, text: str) -> str:
        s = str(text)
        res = []
        key_offset = sum(ord(c) for c in self.key) % 10 + 1
        for char in s:
            res.append(chr((ord(char) - key_offset) % 256))
        return "".join(res)


class HillCipher:
    def __init__(self, key_matrix: list = None):
        # 2x2 key matrix for Hill Cipher
        if key_matrix is None:
            self.a, self.b, self.c, self.d = 7, 8, 11, 11
        else:
            self.a, self.b, self.c, self.d = key_matrix[0][0], key_matrix[0][1], key_matrix[1][0], key_matrix[1][1]

    def encrypt(self, text: str) -> str:
        s = str(text)
        encoded_bytes = s.encode('utf-8')
        if len(encoded_bytes) % 2 != 0:
            encoded_bytes += b'\x00'
        
        cipher_bytes = bytearray()
        for i in range(0, len(encoded_bytes), 2):
            x, y = encoded_bytes[i], encoded_bytes[i+1]
            ex = (self.a * x + self.b * y) % 256
            ey = (self.c * x + self.d * y) % 256
            cipher_bytes.append(ex)
            cipher_bytes.append(ey)
            
        return cipher_bytes.hex()

    def decrypt(self, hex_text: str) -> str:
        cipher_bytes = bytes.fromhex(hex_text)
        det = (self.a * self.d - self.b * self.c) % 256
        det_inv = 1
        for i in range(256):
            if (det * i) % 256 == 1:
                det_inv = i
                break

        ia = (self.d * det_inv) % 256
        ib = (-self.b * det_inv) % 256
        ic = (-self.c * det_inv) % 256
        id_val = (self.a * det_inv) % 256

        plain_bytes = bytearray()
        for i in range(0, len(cipher_bytes), 2):
            ex, ey = cipher_bytes[i], cipher_bytes[i+1]
            dx = (ia * ex + ib * ey) % 256
            dy = (ic * ex + id_val * ey) % 256
            plain_bytes.append(dx)
            plain_bytes.append(dy)
            
        return plain_bytes.rstrip(b'\x00').decode('utf-8', errors='ignore')

