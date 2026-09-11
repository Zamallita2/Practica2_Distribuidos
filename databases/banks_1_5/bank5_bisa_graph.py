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

try:
    import networkx as nx
    from networkx.readwrite import json_graph
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
        def has_edge(self, u, v):
            return any(x[0] == u and x[1] == v for x in self.edges)
        def get_edge_data(self, u, v):
            for edge_u, edge_v, data in self.edges:
                if edge_u == u and edge_v == v:
                    return data
            return None
        @property
        def nodes(self):
            return self.nodes_data
        def __contains__(self, item):
            return item in self.nodes_data



class BankBISAGraphAdapter:
    """Adaptador de grafo (NetworkX / SimpleGraph fallback, persistido en JSON) para el Banco BISA S.A."""

    engine_mode = "real"

    def __init__(self, data_dir: str = "bank_data"):
        os.makedirs(data_dir, exist_ok=True)
        self.graph_path = os.path.join(data_dir, "bank5_bisa_graph.json")
        self.graph = nx.DiGraph() if HAS_NETWORKX else SimpleGraph()
        self.create_schema()

    def create_schema(self):
        self.graph = nx.DiGraph() if HAS_NETWORKX else SimpleGraph()
        self._persist()

    def _persist(self):
        if HAS_NETWORKX:
            data = json_graph.node_link_data(self.graph, edges="edges")
        else:
            data = {
                "nodes": [{"id": k, **v} for k, v in self.graph.nodes_data.items()],
                "edges": [{"source": u, "target": v, **w} for u, v, w in self.graph.edges]
            }
        with open(self.graph_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self):
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, "r") as f:
                    data = json.load(f)
                if HAS_NETWORKX:
                    self.graph = json_graph.node_link_graph(data, directed=True, edges="edges")
                else:
                    g = SimpleGraph()
                    for n in data.get("nodes", []):
                        n_id = n.pop("id", "")
                        g.add_node(n_id, **n)
                    for e in data.get("edges", []):
                        u, v = e.pop("source", ""), e.pop("target", "")
                        g.add_edge(u, v, **e)
                    self.graph = g
            except (json.JSONDecodeError, ValueError):
                pass

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
        nodes_iter = self.graph.nodes(data=True) if HAS_NETWORKX else self.graph.nodes_data.items()
        for _, data in nodes_iter:
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
        node_dict = self.graph.nodes[account_node] if HAS_NETWORKX else self.graph.nodes_data[account_node]
        node_dict["saldo_bs"] = saldo_bs
        node_dict["codigo_verificacion"] = verification_code
        node_dict["fecha_conversion"] = timestamp
        self._persist()
        return True



if __name__ == "__main__":
    adapter = BankBISAGraphAdapter()
    print(f"Banco BISA S.A. (Grafo NetworkX) -> esquema creado en '{adapter.graph_path}' [engine_mode={adapter.engine_mode}]")
