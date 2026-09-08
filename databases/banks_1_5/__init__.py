"""
Adaptadores de Base de Datos - Bancos 1 al 5 (Tarea 2, Integrante 1).

Cada banco usa un motor de persistencia distinto, tal como exige la
consigna de heterogeneidad criptografica/tecnologica:

  Banco 1 (Union)     -> SQLite      (Relacional)
  Banco 2 (Mercantil)  -> MySQL/MariaDB (Relacional)
  Banco 3 (BNB)        -> PostgreSQL (Relacional)
  Banco 4 (BCP)        -> MongoDB    (No Relacional / Documental)
  Banco 5 (BISA)       -> Grafo (NetworkX / Neo4j), nodos Cliente y Cuenta

Los adaptadores de MySQL, PostgreSQL y MongoDB intentan conectarse a un
servidor real (ver docker-compose.yml) y, si no esta disponible, recurren a
un motor local equivalente para que el resto del sistema siga funcionando
en una maquina de desarrollo sin esa infraestructura.
"""

from .bank1_union_sqlite import BankUnionSQLiteAdapter
from .bank2_mercantil_mysql import BankMercantilMySQLAdapter
from .bank3_bnb_postgres import BankBNBPostgresAdapter
from .bank4_bcp_mongo import BankBCPMongoAdapter
from .bank5_bisa_graph import BankBISAGraphAdapter

__all__ = [
    "BankUnionSQLiteAdapter",
    "BankMercantilMySQLAdapter",
    "BankBNBPostgresAdapter",
    "BankBCPMongoAdapter",
    "BankBISAGraphAdapter",
]
