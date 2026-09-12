"""
Banco de Credito de Bolivia S.A. (BCP) - Motor de Base de Datos: MongoDB (No Relacional).
Algoritmo de cifrado asignado: Playfair.
Tarea 2 - Integrante 1.

Se conecta a un servidor MongoDB real (ver docker-compose.yml, servicio
`mongodb`) usando el driver pymongo. Si el driver no esta instalado o el
servidor no responde, recurre automaticamente a un almacen de documentos JSON
local equivalente para que el resto del pipeline siga funcionando sin
bloquear el desarrollo. El modo activo queda expuesto en `engine_mode`
("real" o "local_fallback").
"""

import os
import json
import threading

try:
    from pymongo import MongoClient
    HAS_PYMONGO = True
except ImportError:
    HAS_PYMONGO = False

MONGO_HOST = os.environ.get("BANK4_MONGO_HOST", "localhost")
MONGO_PORT = int(os.environ.get("BANK4_MONGO_PORT", "27017"))
MONGO_DATABASE = os.environ.get("BANK4_MONGO_DATABASE", "banco_bcp")


class BankBCPMongoAdapter:
    """Adaptador documental para el Banco de Credito de Bolivia S.A.

    engine_mode == "real"           -> conectado a un servidor MongoDB real.
    engine_mode == "local_fallback" -> MongoDB no disponible; usa un documento JSON local equivalente.
    """

    def __init__(self, data_dir: str = "bank_data"):
        os.makedirs(data_dir, exist_ok=True)
        self.fallback_path = os.path.join(data_dir, "bank4_bcp_fallback.json")
        self.engine_mode = "local_fallback"
        self._client = None
        self._collection = None
        self._lock = threading.Lock()
        if HAS_PYMONGO:
            try:
                client = MongoClient(MONGO_HOST, MONGO_PORT, serverSelectionTimeoutMS=2000)
                client.admin.command("ping")
                self._client = client
                self._collection = client[MONGO_DATABASE]["CuentasBancarias"]
                self.engine_mode = "real"
            except Exception:
                self.engine_mode = "local_fallback"
        self.create_schema()

    def create_schema(self):
        if self.engine_mode == "real":
            self._collection.delete_many({})
            self._collection.create_index("cuenta_id", unique=True)
        else:
            with self._lock:
                with open(self.fallback_path, "w") as f:
                    json.dump([], f)

    def _load_fallback(self):
        if not os.path.exists(self.fallback_path):
            return []
        try:
            with open(self.fallback_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            return []

    def _save_fallback(self, data):
        with open(self.fallback_path, "w") as f:
            json.dump(data, f, indent=2)

    def insert_encrypted_account(self, cuenta_id: int, cliente_nombre: str, saldo_cifrado: str):
        document = {
            "cuenta_id": cuenta_id,
            "cliente_nombre": cliente_nombre,
            "saldo_usd_cifrado": saldo_cifrado,
            "saldo_bs": 0.0,
            "codigo_verificacion": "",
            "fecha_conversion": "",
        }
        if self.engine_mode == "real":
            self._collection.update_one({"cuenta_id": cuenta_id}, {"$set": document}, upsert=True)
        else:
            with self._lock:
                data = [d for d in self._load_fallback() if d["cuenta_id"] != cuenta_id]
                data.append(document)
                self._save_fallback(data)

    def get_encrypted_accounts(self):
        if self.engine_mode == "real":
            return [
                {
                    "cuenta_id": doc["cuenta_id"],
                    "cliente_nombre": doc["cliente_nombre"],
                    "saldo_usd_cifrado": doc["saldo_usd_cifrado"],
                    "saldo_bs": doc.get("saldo_bs", 0.0),
                    "codigo_verificacion": doc.get("codigo_verificacion", ""),
                }
                for doc in self._collection.find({}, {"_id": 0})
            ]
        with self._lock:
            return self._load_fallback()

    def update_verification_code(self, cuenta_id: int, saldo_bs: float, verification_code: str, timestamp: str) -> bool:
        if self.engine_mode == "real":
            result = self._collection.update_one(
                {"cuenta_id": cuenta_id},
                {"$set": {"saldo_bs": saldo_bs, "codigo_verificacion": verification_code, "fecha_conversion": timestamp}},
            )
            return result.matched_count > 0
        else:
            with self._lock:
                data = self._load_fallback()
                updated = False
                for item in data:
                    if item["cuenta_id"] == cuenta_id:
                        item["saldo_bs"] = saldo_bs
                        item["codigo_verificacion"] = verification_code
                        item["fecha_conversion"] = timestamp
                        updated = True
                self._save_fallback(data)
                return updated


if __name__ == "__main__":
    adapter = BankBCPMongoAdapter()
    print(f"Banco de Credito de Bolivia S.A. (MongoDB) -> esquema creado [engine_mode={adapter.engine_mode}]")
