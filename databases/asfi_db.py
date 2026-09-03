"""
ASFI Central Relational Database Management
Stores consolidated bank accounts, banks catalog, and audit logs.
"""

import sqlite3
import datetime
import os
from config import ASFI_DB_PATH, BANKS

class ASFICentralDatabase:
    def __init__(self, db_path: str = ASFI_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        # Tabla Bancos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Bancos (
                BancoId INTEGER PRIMARY KEY,
                Nombre TEXT NOT NULL,
                AlgoritmoEncriptacion TEXT NOT NULL
            )
        """)

        # Tabla Cuentas Consolidadas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Cuentas (
                CuentaId BIGINT PRIMARY KEY,
                BancoId INTEGER NOT NULL,
                SaldoUSD REAL NOT NULL,
                SaldoBs REAL NOT NULL,
                FechaConversion TEXT NOT NULL,
                CodigoVerificacion CHAR(8) NOT NULL,
                FOREIGN KEY (BancoId) REFERENCES Bancos(BancoId)
            )
        """)

        # Tabla AuditLogs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS AuditLogs (
                LogId INTEGER PRIMARY KEY AUTOINCREMENT,
                Timestamp TEXT NOT NULL,
                ExchangeRate REAL NOT NULL,
                CuentaId BIGINT NOT NULL,
                BancoId INTEGER NOT NULL
            )
        """)

        # Poblar catálogo de bancos si está vacío
        cursor.execute("SELECT COUNT(*) FROM Bancos")
        if cursor.fetchone()[0] == 0:
            for b in BANKS:
                cursor.execute(
                    "INSERT INTO Bancos (BancoId, Nombre, AlgoritmoEncriptacion) VALUES (?, ?, ?)",
                    (b["id"], b["name"], b["algorithm"])
                )

        conn.commit()
        conn.close()

    def record_transaction(self, cuenta_id: int, banco_id: int, saldo_usd: float, saldo_bs: float, exchange_rate: float, verification_code: str, timestamp: str = None):
        if not timestamp:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = self._get_connection()
        cursor = conn.cursor()

        # Insertar o actualizar cuenta en ASFI
        cursor.execute("""
            INSERT OR REPLACE INTO Cuentas (CuentaId, BancoId, SaldoUSD, SaldoBs, FechaConversion, CodigoVerificacion)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (cuenta_id, banco_id, saldo_usd, saldo_bs, timestamp, verification_code))

        # Registrar log de auditoría
        cursor.execute("""
            INSERT INTO AuditLogs (Timestamp, ExchangeRate, CuentaId, BancoId)
            VALUES (?, ?, ?, ?)
        """, (timestamp, exchange_rate, cuenta_id, banco_id))

        conn.commit()
        conn.close()

    def get_all_accounts(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Cuentas")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_audit_logs(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM AuditLogs ORDER BY LogId DESC")
        rows = cursor.fetchall()
        conn.close()
        return rows

asfi_db = ASFICentralDatabase()
