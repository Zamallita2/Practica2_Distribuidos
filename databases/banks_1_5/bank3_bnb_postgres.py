"""
Banco Nacional de Bolivia S.A. (BNB) - Motor de Base de Datos: PostgreSQL (Relacional).
Algoritmo de cifrado asignado: Vigenere.
Tarea 2 - Integrante 1.

Se conecta a un servidor PostgreSQL real (ver docker-compose.yml, servicio
`postgres`) usando el driver psycopg2. Si el driver no esta instalado o el
servidor no responde, recurre automaticamente a un SQLite local equivalente
para que el resto del pipeline siga funcionando sin bloquear el desarrollo.
El modo activo queda expuesto en `engine_mode` ("real" o "local_fallback").
"""

import os
import sqlite3

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

PG_HOST = os.environ.get("BANK3_PG_HOST", "localhost")
PG_PORT = int(os.environ.get("BANK3_PG_PORT", "5432"))
PG_USER = os.environ.get("BANK3_PG_USER", "postgres")
PG_PASSWORD = os.environ.get("BANK3_PG_PASSWORD", "postgres123")
PG_DATABASE = os.environ.get("BANK3_PG_DATABASE", "banco_bnb")

SCHEMA_SQL_POSTGRES = """
CREATE TABLE IF NOT EXISTS CuentasBancarias (
    CuentaId BIGINT PRIMARY KEY,
    ClienteNombre VARCHAR(255) NOT NULL,
    SaldoUSDCifrado TEXT NOT NULL,
    SaldoBs DOUBLE PRECISION DEFAULT 0.0,
    CodigoVerificacion VARCHAR(8) DEFAULT '',
    FechaConversion VARCHAR(32) DEFAULT ''
);
"""

SCHEMA_SQL_SQLITE_FALLBACK = """
CREATE TABLE IF NOT EXISTS CuentasBancarias (
    CuentaId INTEGER PRIMARY KEY,
    ClienteNombre TEXT NOT NULL,
    SaldoUSDCifrado TEXT NOT NULL,
    SaldoBs REAL DEFAULT 0.0,
    CodigoVerificacion TEXT DEFAULT '',
    FechaConversion TEXT DEFAULT ''
);
"""


class BankBNBPostgresAdapter:
    """Adaptador relacional para el Banco Nacional de Bolivia S.A.

    engine_mode == "real"           -> conectado a un servidor PostgreSQL real.
    engine_mode == "local_fallback" -> PostgreSQL no disponible; usa SQLite local equivalente.
    """

    def __init__(self, data_dir: str = "bank_data"):
        os.makedirs(data_dir, exist_ok=True)
        self.fallback_path = os.path.join(data_dir, "bank3_bnb_fallback.db")
        self.engine_mode = "local_fallback"
        if HAS_PSYCOPG2:
            try:
                probe = psycopg2.connect(
                    host=PG_HOST, port=PG_PORT, user=PG_USER,
                    password=PG_PASSWORD, dbname="postgres", connect_timeout=2,
                )
                probe.close()
                self.engine_mode = "real"
            except Exception:
                self.engine_mode = "local_fallback"
        self.create_schema()

    def _connect_admin(self):
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER,
            password=PG_PASSWORD, dbname="postgres", connect_timeout=5,
        )
        conn.autocommit = True
        return conn

    def _ensure_database(self):
        conn = self._connect_admin()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (PG_DATABASE,))
            if cursor.fetchone() is None:
                cursor.execute(f'CREATE DATABASE "{PG_DATABASE}"')
        conn.close()

    def _connect_postgres(self):
        self._ensure_database()
        return psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER,
            password=PG_PASSWORD, dbname=PG_DATABASE, connect_timeout=5,
        )

    def _connect_fallback(self):
        return sqlite3.connect(self.fallback_path)

    def create_schema(self):
        if self.engine_mode == "real":
            conn = self._connect_postgres()
            with conn.cursor() as cursor:
                cursor.execute(SCHEMA_SQL_POSTGRES)
                cursor.execute("DELETE FROM CuentasBancarias")
            conn.commit()
            conn.close()
        else:
            conn = self._connect_fallback()
            conn.executescript(SCHEMA_SQL_SQLITE_FALLBACK)
            conn.execute("DELETE FROM CuentasBancarias")
            conn.commit()
            conn.close()

    def insert_encrypted_account(self, cuenta_id: int, cliente_nombre: str, saldo_cifrado: str):
        if self.engine_mode == "real":
            conn = self._connect_postgres()
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO CuentasBancarias (CuentaId, ClienteNombre, SaldoUSDCifrado, SaldoBs, CodigoVerificacion, FechaConversion)
                    VALUES (%s, %s, %s, 0.0, '', '')
                    ON CONFLICT (CuentaId) DO UPDATE SET
                        ClienteNombre = EXCLUDED.ClienteNombre,
                        SaldoUSDCifrado = EXCLUDED.SaldoUSDCifrado
                    """,
                    (cuenta_id, cliente_nombre, saldo_cifrado),
                )
            conn.commit()
            conn.close()
        else:
            conn = self._connect_fallback()
            conn.execute(
                """
                INSERT OR REPLACE INTO CuentasBancarias
                    (CuentaId, ClienteNombre, SaldoUSDCifrado, SaldoBs, CodigoVerificacion, FechaConversion)
                VALUES (?, ?, ?, 0.0, '', '')
                """,
                (cuenta_id, cliente_nombre, saldo_cifrado),
            )
            conn.commit()
            conn.close()

    def get_encrypted_accounts(self):
        if self.engine_mode == "real":
            conn = self._connect_postgres()
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT CuentaId, ClienteNombre, SaldoUSDCifrado, SaldoBs, CodigoVerificacion FROM CuentasBancarias"
                )
                rows = cursor.fetchall()
            conn.close()
        else:
            conn = self._connect_fallback()
            rows = conn.execute(
                "SELECT CuentaId, ClienteNombre, SaldoUSDCifrado, SaldoBs, CodigoVerificacion FROM CuentasBancarias"
            ).fetchall()
            conn.close()
        return [
            {
                "cuenta_id": r[0],
                "cliente_nombre": r[1],
                "saldo_usd_cifrado": r[2],
                "saldo_bs": r[3],
                "codigo_verificacion": r[4],
            }
            for r in rows
        ]

    def update_verification_code(self, cuenta_id: int, saldo_bs: float, verification_code: str, timestamp: str) -> bool:
        if self.engine_mode == "real":
            conn = self._connect_postgres()
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE CuentasBancarias SET SaldoBs=%s, CodigoVerificacion=%s, FechaConversion=%s WHERE CuentaId=%s",
                    (saldo_bs, verification_code, timestamp, cuenta_id),
                )
                updated = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return updated
        else:
            conn = self._connect_fallback()
            cursor = conn.execute(
                "UPDATE CuentasBancarias SET SaldoBs=?, CodigoVerificacion=?, FechaConversion=? WHERE CuentaId=?",
                (saldo_bs, verification_code, timestamp, cuenta_id),
            )
            conn.commit()
            updated = cursor.rowcount > 0
            conn.close()
            return updated


if __name__ == "__main__":
    adapter = BankBNBPostgresAdapter()
    print(f"Banco Nacional de Bolivia S.A. (PostgreSQL) -> esquema creado [engine_mode={adapter.engine_mode}]")
