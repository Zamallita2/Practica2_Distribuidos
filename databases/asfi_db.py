"""
ASFI Central Relational Database Management (Tarea 7)
Diseño e implementación de la base de datos relacional central de la ASFI:
- Tabla y gestión de Bancos.
- Gestión de Cuentas consolidadas.
- Gestión de AuditLogs.
- Definición de relaciones y restricciones (Foreign Keys, Constraints).
- Configuración de la conexión con el sistema central.
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
        conn = sqlite3.connect(self.db_path)
        # Habilitar restricciones de llaves foráneas en SQLite
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        # 1. Tabla Bancos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Bancos (
                BancoId INTEGER PRIMARY KEY,
                Nombre TEXT NOT NULL,
                AlgoritmoEncriptacion TEXT NOT NULL
            )
        """)

        # 2. Tabla Cuentas Consolidadas con restricción Foreign Key a Bancos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Cuentas (
                CuentaId BIGINT PRIMARY KEY,
                BancoId INTEGER NOT NULL,
                SaldoUSD REAL NOT NULL CHECK(SaldoUSD >= 0),
                SaldoBs REAL NOT NULL CHECK(SaldoBs >= 0),
                FechaConversion TEXT NOT NULL,
                CodigoVerificacion CHAR(8) NOT NULL,
                FOREIGN KEY (BancoId) REFERENCES Bancos(BancoId) ON DELETE CASCADE
            )
        """)

        # 3. Tabla AuditLogs con restricciones Foreign Key
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS AuditLogs (
                LogId INTEGER PRIMARY KEY AUTOINCREMENT,
                Timestamp TEXT NOT NULL,
                ExchangeRate REAL NOT NULL CHECK(ExchangeRate > 0),
                CuentaId BIGINT NOT NULL,
                BancoId INTEGER NOT NULL,
                FOREIGN KEY (BancoId) REFERENCES Bancos(BancoId),
                FOREIGN KEY (CuentaId) REFERENCES Cuentas(CuentaId)
            )
        """)

        # Poblar catálogo oficial de 14 bancos si está vacío
        cursor.execute("SELECT COUNT(*) FROM Bancos")
        if cursor.fetchone()[0] == 0:
            for b in BANKS:
                cursor.execute(
                    "INSERT INTO Bancos (BancoId, Nombre, AlgoritmoEncriptacion) VALUES (?, ?, ?)",
                    (b["id"], b["name"], b["algorithm"])
                )

        conn.commit()
        conn.close()

    # --- GESTIÓN DE BANCOS ---
    def get_bancos(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT BancoId, Nombre, AlgoritmoEncriptacion FROM Bancos ORDER BY BancoId ASC")
        rows = cursor.fetchall()
        conn.close()
        return [{"banco_id": r[0], "nombre": r[1], "algoritmo": r[2]} for r in rows]

    def get_banco_by_id(self, banco_id: int):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT BancoId, Nombre, AlgoritmoEncriptacion FROM Bancos WHERE BancoId = ?", (banco_id,))
        r = cursor.fetchone()
        conn.close()
        if r:
            return {"banco_id": r[0], "nombre": r[1], "algoritmo": r[2]}
        return None

    # --- GESTIÓN DE CUENTAS CONSOLIDADAS ---
    def record_transaction(self, cuenta_id: int, banco_id: int, saldo_usd: float, saldo_bs: float, exchange_rate: float, verification_code: str, timestamp: str = None):
        if not timestamp:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = self._get_connection()
        cursor = conn.cursor()

        # Insertar o actualizar cuenta consolidada en ASFI
        cursor.execute("""
            INSERT INTO Cuentas (CuentaId, BancoId, SaldoUSD, SaldoBs, FechaConversion, CodigoVerificacion)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(CuentaId) DO UPDATE SET
                BancoId = excluded.BancoId,
                SaldoUSD = excluded.SaldoUSD,
                SaldoBs = excluded.SaldoBs,
                FechaConversion = excluded.FechaConversion,
                CodigoVerificacion = excluded.CodigoVerificacion
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
        cursor.execute("SELECT CuentaId, BancoId, SaldoUSD, SaldoBs, FechaConversion, CodigoVerificacion FROM Cuentas")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_account_by_id(self, cuenta_id: int):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT CuentaId, BancoId, SaldoUSD, SaldoBs, FechaConversion, CodigoVerificacion FROM Cuentas WHERE CuentaId = ?", (cuenta_id,))
        row = cursor.fetchone()
        conn.close()
        return row

    def get_accounts_by_bank(self, banco_id: int):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT CuentaId, BancoId, SaldoUSD, SaldoBs, FechaConversion, CodigoVerificacion FROM Cuentas WHERE BancoId = ?", (banco_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    # --- GESTIÓN DE AUDIT LOGS ---
    def get_audit_logs(self, limit: int = 100):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT LogId, Timestamp, ExchangeRate, CuentaId, BancoId FROM AuditLogs ORDER BY LogId DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_audit_logs_by_bank(self, banco_id: int, limit: int = 50):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT LogId, Timestamp, ExchangeRate, CuentaId, BancoId FROM AuditLogs WHERE BancoId = ? ORDER BY LogId DESC LIMIT ?", (banco_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return rows

asfi_db = ASFICentralDatabase()

