import os

# Puerto base para el servicio de microservicios bancarios
BASE_PORT = 8000
BCB_PORT = 8100
ASFI_PORT = 8200

# Configuración del Banco Central de Bolivia (BCB)
BCB_BASE_EXCHANGE_RATE = 6.9600  # Tipo de cambio base USD -> BOB
BCB_UPDATE_INTERVAL_SECONDS = 5 # Fluctuación corta cada 5 segundos para pruebas y demostración dinámica en tiempo real
BCB_MAX_VARIATION = 0.9999

# Configuración ASFI
ASFI_DB_PATH = "asfi_central.db"
AUDIT_LOG_FILE = "asfi_audit.log"

# Seed / ingesta del dataset CSV
USE_FULL_DATASET = False          # True = 100% del CSV; False = usa SEED_SAMPLE_PERCENT
SEED_SAMPLE_PERCENT = 1.0         # Porcentaje por defecto cuando no se pasa --percent / UI

# Lista oficial de Entidades Financieras (Bancos), Algoritmos y Motores de BD
BANKS = [
    {
        "id": 1,
        "name": "Banco Unión S.A.",
        "accounts_count": 2247210,
        "algorithm": "César",
        "db_type": "Relacional",
        "db_engine": "SQLite",
        "assigned_member": "Integrante 1"
    },
    {
        "id": 2,
        "name": "Banco Mercantil Santa Cruz S.A.",
        "accounts_count": 1997520,
        "algorithm": "Atbash",
        "db_type": "Relacional",
        "db_engine": "MySQL/MariaDB",
        "assigned_member": "Integrante 1"
    },
    {
        "id": 3,
        "name": "Banco Nacional de Bolivia S.A.",
        "accounts_count": 1498140,
        "algorithm": "Vigenère",
        "db_type": "Relacional",
        "db_engine": "PostgreSQL",
        "assigned_member": "Integrante 1"
    },
    {
        "id": 4,
        "name": "Banco de Crédito de Bolivia S.A.",
        "accounts_count": 1398264,
        "algorithm": "Playfair",
        "db_type": "No Relacional",
        "db_engine": "MongoDB",
        "assigned_member": "Integrante 1"
    },
    {
        "id": 5,
        "name": "Banco BISA S.A.",
        "accounts_count": 1048698,
        "algorithm": "Hill",
        "db_type": "Grafo (No Relacional)",
        "db_engine": "NetworkX/Neo4j",
        "assigned_member": "Integrante 1"
    },
    {
        "id": 6,
        "name": "Banco Ganadero S.A.",
        "accounts_count": 948822,
        "algorithm": "DES",
        "db_type": "Relacional",
        "db_engine": "SQLite",
        "assigned_member": "Integrante 2"
    },
    {
        "id": 7,
        "name": "Banco Económico S.A.",
        "accounts_count": 848946,
        "algorithm": "3DES",
        "db_type": "Relacional",
        "db_engine": "PostgreSQL",
        "assigned_member": "Integrante 2"
    },
    {
        "id": 8,
        "name": "Banco Prodem S.A.",
        "accounts_count": 749070,
        "algorithm": "Blowfish",
        "db_type": "No Relacional",
        "db_engine": "MongoDB",
        "assigned_member": "Integrante 2"
    },
    {
        "id": 9,
        "name": "Banco Solidario S.A.",
        "accounts_count": 549318,
        "algorithm": "Twofish",
        "db_type": "Relacional",
        "db_engine": "MySQL",
        "assigned_member": "Integrante 2"
    },
    {
        "id": 10,
        "name": "Banco Fortaleza S.A.",
        "accounts_count": 349566,
        "algorithm": "AES",
        "db_type": "Relacional",
        "db_engine": "PostgreSQL",
        "assigned_member": "Integrante 2"
    },
    {
        "id": 11,
        "name": "Banco FIE S.A.",
        "accounts_count": 399504,
        "algorithm": "RSA",
        "db_type": "Relacional",
        "db_engine": "SQLite",
        "assigned_member": "Integrante 2"
    },
    {
        "id": 12,
        "name": "Banco PYME de la Comunidad S.A.",
        "accounts_count": 224721,
        "algorithm": "ElGamal",
        "db_type": "Relacional",
        "db_engine": "MySQL",
        "assigned_member": "Integrante 2"
    },
    {
        "id": 13,
        "name": "Banco de Desarrollo Productivo S.A.M.",
        "accounts_count": 99876,
        "algorithm": "ECC",
        "db_type": "Relacional",
        "db_engine": "PostgreSQL",
        "assigned_member": "Integrante 2"
    },
    {
        "id": 14,
        "name": "Banco de la Nación Argentina",
        "accounts_count": 19975,
        "algorithm": "ChaCha20",
        "db_type": "No Relacional",
        "db_engine": "JSON Key-Value / DuckDB",
        "assigned_member": "Integrante 2"
    }
]
