"""
Asymmetric Ciphers Implementation
Covers: RSA, ElGamal, ECC
Supports encryption of account balance payload and decryption.
"""

import base64
import json
import secrets

try:
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_OAEP
    HAS_RSA = True
except ImportError:
    HAS_RSA = False

try:
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_ECC = True
except ImportError:
    HAS_ECC = False


class RSACipher:
    def __init__(self):
        if HAS_RSA:
            self.key = RSA.generate(2048)
            self.public_key = self.key.publickey()
            self.cipher_enc = PKCS1_OAEP.new(self.public_key)
            self.cipher_dec = PKCS1_OAEP.new(self.key)

    def encrypt(self, text: str) -> str:
        data = str(text).encode('utf-8')
        if HAS_RSA:
            return base64.b64encode(self.cipher_enc.encrypt(data)).decode('utf-8')
        else:
            # Fallback mock RSA scheme using modular exponentiation
            p, q = 61, 53
            n = p * q
            e = 17
            enc = [pow(b, e, n) for b in data]
            return json.dumps(enc)

    def decrypt(self, text: str) -> str:
        if HAS_RSA:
            raw = base64.b64decode(text)
            return self.cipher_dec.decrypt(raw).decode('utf-8')
        else:
            p, q = 61, 53
            n = p * q
            d = 2753
            enc = json.loads(text)
            dec = bytes([pow(c, d, n) for c in enc])
            return dec.decode('utf-8')


class ElGamalCipher:
    """ElGamal Asymmetric Encryption Scheme"""
    def __init__(self, p: int = 7919, g: int = 2):
        self.p = p # Prime number
        self.g = g # Generator
        self.x = 1234 # Private key
        self.h = pow(g, self.x, p) # Public key: (p, g, h)

    def encrypt(self, text: str) -> str:
        # Encrypt byte array into pairs (c1, c2)
        data = str(text).encode('utf-8')
        k = secrets.randbelow(self.p - 2) + 1
        c1 = pow(self.g, k, self.p)
        s = pow(self.h, k, self.p)
        
        pairs = []
        for b in data:
            c2 = (b * s) % self.p
            pairs.append((c1, c2))
            
        return json.dumps(pairs)

    def decrypt(self, text: str) -> str:
        pairs = json.loads(text)
        decrypted_bytes = bytearray()
        for c1, c2 in pairs:
            s = pow(c1, self.x, self.p)
            # Modular inverse of s mod p
            s_inv = pow(s, self.p - 2, self.p)
            b = (c2 * s_inv) % self.p
            decrypted_bytes.append(b)
            
        return decrypted_bytes.decode('utf-8')


class ECCCipher:
    """ECC encryption using an ECIES-style ECDH, HKDF and AES-GCM envelope."""
    def __init__(self):
        if HAS_ECC:
            self.private_key = ec.generate_private_key(ec.SECP256R1())
            self.public_key = self.private_key.public_key()
        else:
            self.private_key = 0xA1B2C3D4E5F6
        
    def encrypt(self, text: str) -> str:
        data = str(text).encode('utf-8')
        if not HAS_ECC:
            mask = (self.private_key * 13) % 256
            return base64.b64encode(bytes([b ^ mask for b in data])).decode('utf-8')

        ephemeral_key = ec.generate_private_key(ec.SECP256R1())
        shared_secret = ephemeral_key.exchange(ec.ECDH(), self.public_key)
        aes_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b'ASFI-ECC').derive(shared_secret)
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(aes_key).encrypt(nonce, data, None)
        ephemeral_public = ephemeral_key.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.CompressedPoint
        )
        return base64.b64encode(ephemeral_public + nonce + ciphertext).decode('utf-8')

    def decrypt(self, text: str) -> str:
        raw = base64.b64decode(text)
        if not HAS_ECC:
            mask = (self.private_key * 13) % 256
            return bytes([b ^ mask for b in raw]).decode('utf-8')

        ephemeral_public = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw[:33])
        nonce = raw[33:45]
        ciphertext = raw[45:]
        shared_secret = self.private_key.exchange(ec.ECDH(), ephemeral_public)
        aes_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b'ASFI-ECC').derive(shared_secret)
        return AESGCM(aes_key).decrypt(nonce, ciphertext, None).decode('utf-8')
