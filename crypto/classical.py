"""
Cifrados Clasicos: Cesar, Atbash, Vigenere, Playfair, Hill.

Los tres primeros comparten un alfabeto extendido (mayusculas, minusculas,
digitos y los simbolos ".,-+_ ") para poder cifrar tanto nombres de clientes
como saldos numericos (ej. "1250.5000"), conservando exactamente la mecanica
matematica del algoritmo original (aritmetica modular sobre el tamano del
alfabeto). Playfair usa una rejilla de digrafos (mayusculas + digitos +
".,- ") tal como el algoritmo clasico exige. Hill generaliza la
multiplicacion matricial 2x2 modular al espacio de bytes (mod 256), lo que
le permite cifrar cualquier cadena UTF-8 conservando la misma matemática
(matriz de clave invertible, determinante coprimo con el modulo).
"""

import string

# ---------------------------------------------------------------------------
# Alfabeto compartido por Cesar, Atbash y Vigenere.
# ---------------------------------------------------------------------------
ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits + ".,-+_ "
ALPHABET_SIZE = len(ALPHABET)
_INDEX = {ch: i for i, ch in enumerate(ALPHABET)}


class CaesarCipher:
    """Cifrado por desplazamiento: C = (P + shift) mod N.

    Los caracteres que no pertenecen al alfabeto de trabajo (por ejemplo
    acentos) se dejan sin modificar, tal como el Cesar clasico no altera
    signos de puntuacion fuera de su alfabeto.
    """

    def __init__(self, shift: int = 3):
        self.shift = shift % ALPHABET_SIZE

    def _shift_text(self, text: str, shift: int) -> str:
        result = []
        for char in str(text):
            idx = _INDEX.get(char)
            if idx is None:
                result.append(char)
            else:
                result.append(ALPHABET[(idx + shift) % ALPHABET_SIZE])
        return "".join(result)

    def encrypt(self, text: str) -> str:
        return self._shift_text(text, self.shift)

    def decrypt(self, text: str) -> str:
        return self._shift_text(text, -self.shift)


class AtbashCipher:
    """Sustitucion reciproca: C = (N - 1) - P. Es su propio inverso."""

    def encrypt(self, text: str) -> str:
        result = []
        for char in str(text):
            idx = _INDEX.get(char)
            result.append(char if idx is None else ALPHABET[ALPHABET_SIZE - 1 - idx])
        return "".join(result)

    def decrypt(self, text: str) -> str:
        return self.encrypt(text)


class VigenereCipher:
    """Cifrado polialfabetico clasico con clave repetida.

    Solo los caracteres presentes en el alfabeto de trabajo avanzan el
    cursor de la clave, igual que el Vigenere clasico ignora los signos de
    puntuacion que quedan fuera de su alfabeto al alinear la clave.
    """

    def __init__(self, key: str = "ASFIKEY2026"):
        if not key:
            raise ValueError("La clave Vigenere no puede estar vacia")
        self.key = key

    def _key_shift(self, key_position: int) -> int:
        key_char = self.key[key_position % len(self.key)]
        return _INDEX.get(key_char, 0)

    def encrypt(self, text: str) -> str:
        result = []
        key_pos = 0
        for char in str(text):
            idx = _INDEX.get(char)
            if idx is None:
                result.append(char)
                continue
            result.append(ALPHABET[(idx + self._key_shift(key_pos)) % ALPHABET_SIZE])
            key_pos += 1
        return "".join(result)

    def decrypt(self, text: str) -> str:
        result = []
        key_pos = 0
        for char in str(text):
            idx = _INDEX.get(char)
            if idx is None:
                result.append(char)
                continue
            result.append(ALPHABET[(idx - self._key_shift(key_pos)) % ALPHABET_SIZE])
            key_pos += 1
        return "".join(result)


class PlayfairCipher:
    """Cifrado por digrafos sobre una rejilla 5x8 (40 celdas) generada a
    partir de una palabra clave, usando mayusculas, digitos y ".,- ".

    Reglas clasicas de Playfair:
      - Misma fila     -> se toma el caracter inmediato a la derecha (circular).
      - Misma columna  -> se toma el caracter inmediato abajo (circular).
      - Rectangulo     -> se intercambian las columnas manteniendo la fila.

    Limitacion clasica conocida: los digrafos dobles y el relleno de
    longitud impar se resuelven insertando el caracter de relleno 'X'. Como
    los datos que este banco cifra son siempre numericos (saldos), 'X' jamas
    aparece en el texto plano real, por lo que decrypt() puede eliminarlo de
    forma segura al reconstruir el texto original.
    """

    GRID_ALPHABET = string.ascii_uppercase + string.digits + ".,- "
    ROWS, COLS = 5, 8
    FILLER = "X"

    def __init__(self, key: str = "MONARCHY"):
        self.key = key.upper()
        self.grid = self._build_grid(self.key)
        self.position = {ch: divmod(i, self.COLS) for i, ch in enumerate(self.grid)}

    def _build_grid(self, key: str) -> str:
        seen = []
        for ch in key + self.GRID_ALPHABET:
            if ch in self.GRID_ALPHABET and ch not in seen:
                seen.append(ch)
        return "".join(seen)

    def _sanitize(self, text: str) -> str:
        upper = str(text).upper()
        return "".join(ch for ch in upper if ch in self.GRID_ALPHABET)

    def _digraphs(self, text: str):
        pairs = []
        chars = list(text)
        i = 0
        while i < len(chars):
            a = chars[i]
            if i + 1 < len(chars):
                b = chars[i + 1]
                if a == b:
                    pairs.append((a, self.FILLER))
                    i += 1
                else:
                    pairs.append((a, b))
                    i += 2
            else:
                pairs.append((a, self.FILLER))
                i += 1
        return pairs

    def encrypt(self, text: str) -> str:
        clean = self._sanitize(text)
        result = []
        for a, b in self._digraphs(clean):
            ra, ca = self.position[a]
            rb, cb = self.position[b]
            if ra == rb:
                result.append(self.grid[ra * self.COLS + (ca + 1) % self.COLS])
                result.append(self.grid[rb * self.COLS + (cb + 1) % self.COLS])
            elif ca == cb:
                result.append(self.grid[((ra + 1) % self.ROWS) * self.COLS + ca])
                result.append(self.grid[((rb + 1) % self.ROWS) * self.COLS + cb])
            else:
                result.append(self.grid[ra * self.COLS + cb])
                result.append(self.grid[rb * self.COLS + ca])
        return "".join(result)

    def decrypt(self, text: str) -> str:
        clean = self._sanitize(text)
        clean = clean[: len(clean) - len(clean) % 2]
        result = []
        for i in range(0, len(clean), 2):
            a, b = clean[i], clean[i + 1]
            ra, ca = self.position[a]
            rb, cb = self.position[b]
            if ra == rb:
                result.append(self.grid[ra * self.COLS + (ca - 1) % self.COLS])
                result.append(self.grid[rb * self.COLS + (cb - 1) % self.COLS])
            elif ca == cb:
                result.append(self.grid[((ra - 1) % self.ROWS) * self.COLS + ca])
                result.append(self.grid[((rb - 1) % self.ROWS) * self.COLS + cb])
            else:
                result.append(self.grid[ra * self.COLS + cb])
                result.append(self.grid[rb * self.COLS + ca])
        return "".join(result).replace(self.FILLER, "")


class HillCipher:
    """Cifrado de Hill: multiplicacion matricial 2x2 modular.

    Se generaliza el algoritmo clasico (que opera mod 26 sobre letras) al
    espacio de bytes (mod 256), lo que permite cifrar cualquier cadena
    UTF-8 -- nombres, saldos, simbolos -- con la misma matematica: una
    matriz de clave K de 2x2 cuyo determinante debe ser invertible modulo
    256 (gcd(det, 256) == 1), aplicada a bloques de 2 bytes del texto plano.
    """

    def __init__(self, key_matrix: list = None):
        if key_matrix is None:
            self.a, self.b, self.c, self.d = 7, 8, 11, 11
        else:
            self.a, self.b, self.c, self.d = (
                key_matrix[0][0], key_matrix[0][1],
                key_matrix[1][0], key_matrix[1][1],
            )
        self._validate_invertible()

    def _validate_invertible(self):
        det = (self.a * self.d - self.b * self.c) % 256
        if math_gcd(det, 256) != 1:
            raise ValueError(
                "La matriz clave de Hill no es invertible modulo 256 "
                f"(det={det}); elija otra matriz con gcd(det, 256) == 1."
            )

    def _mod_inverse(self, det: int) -> int:
        det %= 256
        for i in range(256):
            if (det * i) % 256 == 1:
                return i
        raise ValueError("El determinante no tiene inverso modulo 256")

    def encrypt(self, text: str) -> str:
        s = str(text)
        encoded_bytes = bytearray(s.encode("utf-8"))
        if len(encoded_bytes) % 2 != 0:
            encoded_bytes.append(0)

        cipher_bytes = bytearray()
        for i in range(0, len(encoded_bytes), 2):
            x, y = encoded_bytes[i], encoded_bytes[i + 1]
            ex = (self.a * x + self.b * y) % 256
            ey = (self.c * x + self.d * y) % 256
            cipher_bytes.append(ex)
            cipher_bytes.append(ey)

        return cipher_bytes.hex()

    def decrypt(self, hex_text: str) -> str:
        cipher_bytes = bytes.fromhex(hex_text)
        det = (self.a * self.d - self.b * self.c) % 256
        det_inv = self._mod_inverse(det)

        ia = (self.d * det_inv) % 256
        ib = (-self.b * det_inv) % 256
        ic = (-self.c * det_inv) % 256
        id_val = (self.a * det_inv) % 256

        plain_bytes = bytearray()
        for i in range(0, len(cipher_bytes), 2):
            ex, ey = cipher_bytes[i], cipher_bytes[i + 1]
            dx = (ia * ex + ib * ey) % 256
            dy = (ic * ex + id_val * ey) % 256
            plain_bytes.append(dx)
            plain_bytes.append(dy)

        return plain_bytes.rstrip(b"\x00").decode("utf-8", errors="ignore")


def math_gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


if __name__ == "__main__":
    print("=== Pruebas rapidas de funcionamiento: Cifrados Clasicos ===\n")

    # Cesar, Atbash, Vigenere y Hill soportan el alfabeto completo (texto y
    # numeros). Playfair usa una rejilla restringida (mayusculas, digitos y
    # ".,- "), asi que se prueba con muestras compatibles con su alfabeto.
    muestras_generales = ["HOLA MUNDO ASFI", "1250.5000", "-348.2200", "Cliente_102938"]
    muestras_playfair = ["HOLA MUNDO ASFI", "1250.5000", "-348.2200", "CLIENTE 102938"]

    ciphers = {
        "Cesar": (CaesarCipher(shift=7), muestras_generales),
        "Atbash": (AtbashCipher(), muestras_generales),
        "Vigenere": (VigenereCipher(key="BANCOCENTRAL"), muestras_generales),
        "Playfair": (PlayfairCipher(key="ASFIBOLIVIA"), muestras_playfair),
        "Hill": (HillCipher(), muestras_generales),
    }

    for nombre, (cipher, muestras) in ciphers.items():
        print(f"--- {nombre} ---")
        for texto in muestras:
            cifrado = cipher.encrypt(texto)
            descifrado = cipher.decrypt(cifrado)
            ok = "OK" if descifrado == texto else f"DIFERENTE (obtenido: {descifrado!r})"
            print(f"  texto={texto!r} -> cifrado={cifrado!r} -> descifrado={descifrado!r} [{ok}]")
        print()
