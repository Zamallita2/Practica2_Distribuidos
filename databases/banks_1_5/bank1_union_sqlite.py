"""
Banco Union S.A. - Motor de Base de Datos: SQLite (Relacional).
Algoritmo de cifrado asignado: Cesar.
Tarea 2 - Integrante 1.

SQLite es un motor embebido real (no un mock): no requiere servidor, por lo
que este adaptador siempre opera en modo "real".
"""

import os
import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS CuentasBancarias (
    CuentaId INTEGER PRIMARY KEY,
    ClienteNombre TEXT NOT NULL,
    SaldoUSDCifrado TEXT NOT NULL,
    SaldoBs REAL DEFAULT 0.0,
    CodigoVerificacion TEXT DEFAULT '',
    FechaConversion TEXT DEFAULT ''
);
"""


class BankUnionSQLiteAdapter:
    """Adaptador relacional (SQLite) para el Banco Union S.A."""

    engine_mode = "real"

    def __init__(self, data_dir: str = "bank_data"):
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = os.path.join(data_dir, "bank1_union.db")
        self.create_schema()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def create_schema(self):
        conn = self._connect()
        conn.executescript(SCHEMA_SQL)
        conn.execute("DELETE FROM CuentasBancarias")
        conn.commit()
        conn.close()

    def insert_encrypted_account(self, cuenta_id: int, cliente_nombre: str, saldo_cifrado: str):
        conn = self._connect()
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
        conn = self._connect()
        cursor = conn.execute(
            "SELECT CuentaId, ClienteNombre, SaldoUSDCifrado, SaldoBs, CodigoVerificacion FROM CuentasBancarias"
        )
        rows = cursor.fetchall()
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
        conn = self._connect()
        cursor = conn.execute(
            """
            UPDATE CuentasBancarias
            SET SaldoBs = ?, CodigoVerificacion = ?, FechaConversion = ?
            WHERE CuentaId = ?
            """,
            (saldo_bs, verification_code, timestamp, cuenta_id),
        )
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated


if __name__ == "__main__":
    adapter = BankUnionSQLiteAdapter()
    print(f"Banco Union S.A. (SQLite) -> esquema creado en '{adapter.db_path}' [engine_mode={adapter.engine_mode}]")
