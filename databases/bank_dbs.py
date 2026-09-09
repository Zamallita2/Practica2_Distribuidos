"""
Bank Database Adapters (14 Banks)
Supports: Relational (SQLite, MySQL, PostgreSQL schemas), NoSQL (Document/KV Store), and Graph DB (NetworkX / SimpleGraph).
"""

import sqlite3
import os
import json
from config import BANKS
from databases.banks_1_5 import (
    BankUnionSQLiteAdapter,
    BankMercantilMySQLAdapter,
    BankBNBPostgresAdapter,
    BankBCPMongoAdapter,
    BankBISAGraphAdapter,
)

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    class SimpleGraph:
        def __init__(self):
            self.nodes_data = {}
            self.edges = []
        def add_node(self, node_id, **kwargs):
            self.nodes_data[node_id] = kwargs
        def add_edge(self, u, v, **kwargs):
            self.edges.append((u, v, kwargs))
        def nodes(self, data=False):
            if data:
                return self.nodes_data.items()
            return self.nodes_data.keys()
        def __contains__(self, item):
            return item in self.nodes_data

# Bancos 1-5 (Tarea 2, Integrante 1): cada uno usa su propio motor de BD real
# (SQLite, MySQL, PostgreSQL, MongoDB, Grafo) en vez de la simulacion generica
# de abajo, que sigue aplicando tal cual para los Bancos 6-14.
BANKS_1_5_ADAPTER_CLASSES = {
    1: BankUnionSQLiteAdapter,
    2: BankMercantilMySQLAdapter,
    3: BankBNBPostgresAdapter,
    4: BankBCPMongoAdapter,
    5: BankBISAGraphAdapter,
}

class BankDatabaseManager:
    """Manages storage for each of the 14 banks using assigned database paradigms."""
    def __init__(self, data_dir: str = "bank_data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.graph_dbs = {} # Graph DB storage for Bank 5
        self.banks_1_5 = {
            b_id: adapter_cls(data_dir=self.data_dir)
            for b_id, adapter_cls in BANKS_1_5_ADAPTER_CLASSES.items()
        }
        self._init_bank_stores()

    def _init_bank_stores(self, reset: bool = False):
        if reset:
            for b_id, adapter in self.banks_1_5.items():
                adapter.create_schema()

        for b in BANKS:
            b_id = b["id"]
            if b_id in self.banks_1_5:
                continue
            if b["db_engine"] == "NetworkX/Neo4j" or "Grafo" in b["db_type"]:
                self.graph_dbs[b_id] = nx.DiGraph() if HAS_NETWORKX else SimpleGraph()
            elif "MongoDB" in b["db_engine"] or "JSON" in b["db_engine"]:
                json_path = os.path.join(self.data_dir, f"bank_{b_id}_nosql.json")
                if reset or not os.path.exists(json_path):
                    with open(json_path, "w") as f:
                        json.dump([], f)
            else:
                db_file = os.path.join(self.data_dir, f"bank_{b_id}.db")
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS CuentasBancarias (
                        CuentaId INTEGER PRIMARY KEY,
                        ClienteNombre TEXT NOT NULL,
                        SaldoUSDCifrado TEXT NOT NULL,
                        SaldoBs REAL DEFAULT 0.0,
                        CodigoVerificacion TEXT DEFAULT '',
                        FechaConversion TEXT DEFAULT ''
                    )
                """)
                if reset:
                    cursor.execute("DELETE FROM CuentasBancarias")
                conn.commit()
                conn.close()


    def insert_encrypted_account(self, bank_id: int, cuenta_id: int, cliente_nombre: str, saldo_cifrado: str):
        if bank_id in self.banks_1_5:
            self.banks_1_5[bank_id].insert_encrypted_account(cuenta_id, cliente_nombre, saldo_cifrado)
            return

        b_info = next((b for b in BANKS if b["id"] == bank_id), None)
        if not b_info:
            return

        if b_info["db_engine"] == "NetworkX/Neo4j" or "Grafo" in b_info["db_type"]:
            # Graph DB: Client Node --[HAS_ACCOUNT]--> Account Node
            G = self.graph_dbs[bank_id]
            client_node = f"Client_{cliente_nombre.replace(' ', '_')}"
            account_node = f"Account_{cuenta_id}"
            
            G.add_node(client_node, type="Cliente", nombre=cliente_nombre)
            G.add_node(account_node, type="Cuenta", cuenta_id=cuenta_id, saldo_cifrado=saldo_cifrado, saldo_bs=0.0, codigo_verificacion="", fecha_conversion="")
            G.add_edge(client_node, account_node, relation="POSEE_CUENTA")

        elif "MongoDB" in b_info["db_engine"] or "JSON" in b_info["db_engine"]:
            # NoSQL Document Store
            json_path = os.path.join(self.data_dir, f"bank_{bank_id}_nosql.json")
            data = []
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    data = json.load(f)
            
            # Upsert
            data = [d for d in data if d["cuenta_id"] != cuenta_id]
            data.append({
                "cuenta_id": cuenta_id,
                "cliente_nombre": cliente_nombre,
                "saldo_usd_cifrado": saldo_cifrado,
                "saldo_bs": 0.0,
                "codigo_verificacion": "",
                "fecha_conversion": ""
            })
            with open(json_path, "w") as f:
                json.dump(data, f, indent=2)

        else:
            # Relational Store
            db_file = os.path.join(self.data_dir, f"bank_{bank_id}.db")
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO CuentasBancarias (CuentaId, ClienteNombre, SaldoUSDCifrado, SaldoBs, CodigoVerificacion, FechaConversion)
                VALUES (?, ?, ?, 0.0, '', '')
            """, (cuenta_id, cliente_nombre, saldo_cifrado))
            conn.commit()
            conn.close()

    def get_encrypted_accounts(self, bank_id: int):
        if bank_id in self.banks_1_5:
            return self.banks_1_5[bank_id].get_encrypted_accounts()

        b_info = next((b for b in BANKS if b["id"] == bank_id), None)
        if not b_info:
            return []

        if b_info["db_engine"] == "NetworkX/Neo4j" or "Grafo" in b_info["db_type"]:
            G = self.graph_dbs.get(bank_id, nx.DiGraph() if HAS_NETWORKX else SimpleGraph())
            accounts = []
            for n, data in G.nodes(data=True):
                if data.get("type") == "Cuenta":
                    accounts.append({
                        "cuenta_id": data["cuenta_id"],
                        "saldo_usd_cifrado": data["saldo_cifrado"],
                        "saldo_bs": data.get("saldo_bs", 0.0),
                        "codigo_verificacion": data.get("codigo_verificacion", "")
                    })
            return accounts

        elif "MongoDB" in b_info["db_engine"] or "JSON" in b_info["db_engine"]:
            json_path = os.path.join(self.data_dir, f"bank_{bank_id}_nosql.json")
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    return json.load(f)
            return []

        else:
            db_file = os.path.join(self.data_dir, f"bank_{bank_id}.db")
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT CuentaId, ClienteNombre, SaldoUSDCifrado, SaldoBs, CodigoVerificacion FROM CuentasBancarias")
            rows = cursor.fetchall()
            conn.close()
            return [
                {
                    "cuenta_id": r[0],
                    "cliente_nombre": r[1],
                    "saldo_usd_cifrado": r[2],
                    "saldo_bs": r[3],
                    "codigo_verificacion": r[4]
                } for r in rows
            ]

    def update_verification_code(self, bank_id: int, cuenta_id: int, saldo_bs: float, verification_code: str, timestamp: str):
        if bank_id in self.banks_1_5:
            return self.banks_1_5[bank_id].update_verification_code(cuenta_id, saldo_bs, verification_code, timestamp)

        b_info = next((b for b in BANKS if b["id"] == bank_id), None)
        if not b_info:
            return False

        if b_info["db_engine"] == "NetworkX/Neo4j" or "Grafo" in b_info["db_type"]:
            G = self.graph_dbs.get(bank_id)
            account_node = f"Account_{cuenta_id}"
            if G and account_node in G:
                node_dict = G.nodes[account_node] if HAS_NETWORKX else G.nodes_data[account_node]
                node_dict["saldo_bs"] = saldo_bs
                node_dict["codigo_verificacion"] = verification_code
                node_dict["fecha_conversion"] = timestamp
                return True
            return False

        elif "MongoDB" in b_info["db_engine"] or "JSON" in b_info["db_engine"]:
            json_path = os.path.join(self.data_dir, f"bank_{bank_id}_nosql.json")
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    data = json.load(f)
                found = False
                for item in data:
                    if item["cuenta_id"] == cuenta_id:
                        item["saldo_bs"] = saldo_bs
                        item["codigo_verificacion"] = verification_code
                        item["fecha_conversion"] = timestamp
                        found = True
                if not found:
                    return False
                with open(json_path, "w") as f:
                    json.dump(data, f, indent=2)
                return True
            return False

        else:
            db_file = os.path.join(self.data_dir, f"bank_{bank_id}.db")
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE CuentasBancarias
                SET SaldoBs = ?, CodigoVerificacion = ?, FechaConversion = ?
                WHERE CuentaId = ?
            """, (saldo_bs, verification_code, timestamp, cuenta_id))
            updated = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return updated

bank_db_manager = BankDatabaseManager()
