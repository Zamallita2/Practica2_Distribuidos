"""
Banco BISA S.A. - Motor de Base de Datos: Grafo (No Relacional).
Algoritmo de cifrado asignado: Hill.
Tarea 2 - Integrante 1.

Modelo de grafo con dos tipos de nodo:
  - Cliente: identificado por su nombre.
  - Cuenta:  identificado por CuentaId, con el saldo cifrado y los campos
             de conversion/verificacion.
Relacion dirigida Cliente -[POSEE_CUENTA]-> Cuenta.

Usa NetworkX (grafo dirigido embebido) como motor real -- no requiere
servidor -- y lo persiste en disco en formato node-link JSON para que sea
una base de datos durable y no solo una estructura en memoria. Si se cuenta
con un servidor Neo4j real, el mismo modelo de nodos/relaciones se replica
en databases/schema/bank5_bisa_graph.cypher.
"""

import os
import json
import networkx as nx
from networkx.readwrite import json_graph


class BankBISAGraphAdapter:
    """Adaptador de grafo (NetworkX, persistido en JSON) para el Banco BISA S.A."""

    engine_mode = "real"  # NetworkX es un motor de grafo real embebido.

    def __init__(self, data_dir: str = "bank_data"):
        os.makedirs(data_dir, exist_ok=True)
        self.graph_path = os.path.join(data_dir, "bank5_bisa_graph.json")
        self.graph = nx.DiGraph()
        self.create_schema()

    def create_schema(self):
        self.graph = nx.DiGraph()
        self._persist()

    def _persist(self):
        data = json_graph.node_link_data(self.graph, edges="edges")
        with open(self.graph_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self):
        if os.path.exists(self.graph_path):
            with open(self.graph_path, "r") as f:
                data = json.load(f)
            self.graph = json_graph.node_link_graph(data, directed=True, edges="edges")

    def insert_encrypted_account(self, cuenta_id: int, cliente_nombre: str, saldo_cifrado: str):
        self._load()
        client_node = f"Cliente_{cliente_nombre.replace(' ', '_')}"
        account_node = f"Cuenta_{cuenta_id}"

        self.graph.add_node(client_node, tipo="Cliente", nombre=cliente_nombre)
        self.graph.add_node(
            account_node,
            tipo="Cuenta",
            cuenta_id=cuenta_id,
            saldo_usd_cifrado=saldo_cifrado,
            saldo_bs=0.0,
            codigo_verificacion="",
            fecha_conversion="",
        )
        self.graph.add_edge(client_node, account_node, relacion="POSEE_CUENTA")
        self._persist()

    def get_encrypted_accounts(self):
        self._load()
        accounts = []
        for _, data in self.graph.nodes(data=True):
            if data.get("tipo") == "Cuenta":
                accounts.append({
                    "cuenta_id": data["cuenta_id"],
                    "saldo_usd_cifrado": data["saldo_usd_cifrado"],
                    "saldo_bs": data.get("saldo_bs", 0.0),
                    "codigo_verificacion": data.get("codigo_verificacion", ""),
                })
        return accounts

    def update_verification_code(self, cuenta_id: int, saldo_bs: float, verification_code: str, timestamp: str) -> bool:
        self._load()
        account_node = f"Cuenta_{cuenta_id}"
        if account_node not in self.graph:
            return False
        self.graph.nodes[account_node]["saldo_bs"] = saldo_bs
        self.graph.nodes[account_node]["codigo_verificacion"] = verification_code
        self.graph.nodes[account_node]["fecha_conversion"] = timestamp
        self._persist()
        return True


if __name__ == "__main__":
    adapter = BankBISAGraphAdapter()
    print(f"Banco BISA S.A. (Grafo NetworkX) -> esquema creado en '{adapter.graph_path}' [engine_mode={adapter.engine_mode}]")
