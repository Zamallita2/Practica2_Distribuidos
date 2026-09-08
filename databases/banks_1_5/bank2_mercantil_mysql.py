"""
Banco Mercantil Santa Cruz S.A. - Motor de Base de Datos: MySQL / MariaDB (Relacional).
Algoritmo de cifrado asignado: Atbash.
Tarea 2 - Integrante 1.

Se conecta a un servidor MySQL/MariaDB real (ver docker-compose.yml, servicio
`mysql`) usando el driver pymysql. Si el driver no esta instalado o el
servidor no responde -- por ejemplo, en una maquina de desarrollo sin
Docker -- este adaptador recurre automaticamente a un SQLite local
equivalente para que el resto del pipeline (poblamiento, barrido, pruebas)
siga funcionando sin bloquear el desarrollo. El modo activo queda expuesto
en `engine_mode` ("real" o "local_fallback").
"""

import os
import sqlite3

try:
    import pymysql
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False

MYSQL_HOST = os.environ.get("BANK2_MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("BANK2_MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("BANK2_MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("BANK2_MYSQL_PASSWORD", "root123")
MYSQL_DATABASE = os.environ.get("BANK2_MYSQL_DATABASE", "banco_mercantil")

SCHEMA_SQL_MYSQL = """
CREATE TABLE IF NOT EXISTS CuentasBancarias (
    CuentaId BIGINT PRIMARY KEY,
    ClienteNombre VARCHAR(255) NOT NULL,
    SaldoUSDCifrado TEXT NOT NULL,
    SaldoBs DOUBLE DEFAULT 0.0,
    CodigoVerificacion VARCHAR(8) DEFAULT '',
    FechaConversion VARCHAR(32) DEFAULT ''
)
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


class BankMercantilMySQLAdapter:
    """Adaptador relacional para el Banco Mercantil Santa Cruz S.A.

    engine_mode == "real"           -> conectado a un servidor MySQL/MariaDB real.
    engine_mode == "local_fallback" -> MySQL no disponible; usa SQLite local equivalente.
    """

    def __init__(self, data_dir: str = "bank_data"):
        os.makedirs(data_dir, exist_ok=True)
        self.fallback_path = os.path.join(data_dir, "bank2_mercantil_fallback.db")
        self.engine_mode = "local_fallback"
        if HAS_PYMYSQL:
            try:
                probe = pymysql.connect(
                    host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
                    password=MYSQL_PASSWORD, connect_timeout=2,
                )
                probe.close()
                self.engine_mode = "real"
            except Exception:
                self.engine_mode = "local_fallback"
        self.create_schema()

    def _connect_mysql(self):
        conn = pymysql.connect(
            host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
            password=MYSQL_PASSWORD, connect_timeout=5,
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE}")
        conn.select_db(MYSQL_DATABASE)
        return conn

    def _connect_fallback(self):
        return sqlite3.connect(self.fallback_path)

    def create_schema(self):
        if self.engine_mode == "real":
            conn = self._connect_mysql()
            with conn.cursor() as cursor:
                cursor.execute(SCHEMA_SQL_MYSQL)
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
            conn = self._connect_mysql()
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO CuentasBancarias (CuentaId, ClienteNombre, SaldoUSDCifrado, SaldoBs, CodigoVerificacion, FechaConversion)
                    VALUES (%s, %s, %s, 0.0, '', '')
                    ON DUPLICATE KEY UPDATE ClienteNombre = VALUES(ClienteNombre), SaldoUSDCifrado = VALUES(SaldoUSDCifrado)
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
            conn = self._connect_mysql()
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
            conn = self._connect_mysql()
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
    adapter = BankMercantilMySQLAdapter()
    print(f"Banco Mercantil Santa Cruz S.A. (MySQL/MariaDB) -> esquema creado [engine_mode={adapter.engine_mode}]")
