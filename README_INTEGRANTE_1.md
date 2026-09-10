# 🏛️ Módulo Integrante 1: Cifrados Clásicos & Bases de Datos Bancos 1-5

Documentación específica del módulo perteneciente al **Integrante 1** (Tani) para la **Plataforma Distribuida de Conversión Monetaria Interbancaria (ASFI - BCB)**.

---

## 🟨 Tarea 1: Implementación de Cifrados Clásicos

Implementación de los 5 algoritmos de cifrado clásico asignados a los Bancos 1-5, con la mecánica matemática real de cada algoritmo (no una simulación genérica), adaptados mediante un alfabeto extendido para poder cifrar tanto nombres de clientes como saldos numéricos.

### 📋 Componentes Implementados

1. **César** (Banco Unión): desplazamiento modular `C = (P + shift) mod N`.
2. **Atbash** (Banco Mercantil): sustitución recíproca `C = (N-1) - P`, es su propio inverso.
3. **Vigenère** (Banco Nacional de Bolivia): polialfabético con clave repetida.
4. **Playfair** (Banco de Crédito de Bolivia): rejilla de dígrafos 5x8 con las reglas clásicas de fila/columna/rectángulo.
5. **Hill** (Banco BISA): multiplicación matricial 2x2 modular (generalizada a mod 256 para soportar cualquier texto UTF-8), con validación de que la matriz clave sea invertible.

### 📁 Archivos Relacionados

- **Módulo de Cifrados**: [crypto/classical.py](crypto/classical.py)
- **Pruebas Unitarias Tarea 1**: [tests/test_tarea1_classical_ciphers.py](tests/test_tarea1_classical_ciphers.py)

### 🚀 Ejecución

```bash
python -m crypto.classical                              # Demo rápida de cifrado/descifrado
python -m pytest tests/test_tarea1_classical_ciphers.py -v
```

---

## 🟨 Tarea 2: Bases de Datos de Bancos 1-5

Cada uno de los 5 bancos asignados usa un motor de persistencia **real y distinto**, en vez de una simulación genérica compartida:

| Banco | Motor | Tipo | Algoritmo |
|---|---|---|---|
| 1. Banco Unión S.A. | SQLite | Relacional | César |
| 2. Banco Mercantil Santa Cruz S.A. | MySQL / MariaDB | Relacional | Atbash |
| 3. Banco Nacional de Bolivia S.A. | PostgreSQL | Relacional | Vigenère |
| 4. Banco de Crédito de Bolivia S.A. | MongoDB | No Relacional (Documental) | Playfair |
| 5. Banco BISA S.A. | Grafo (NetworkX / Neo4j) | No Relacional (Grafo) | Hill |

### 📋 Componentes Implementados

1. **Adaptadores por banco** ([databases/banks_1_5/](databases/banks_1_5/)): cada uno expone la misma interfaz (`create_schema`, `insert_encrypted_account`, `get_encrypted_accounts`, `update_verification_code`) sobre su motor real correspondiente.
2. **Conexión real con fallback local**: los adaptadores de MySQL, PostgreSQL y MongoDB intentan conectarse al servidor real (ver `docker-compose.yml`) y, si no está disponible en la máquina de desarrollo, recurren automáticamente a un motor local equivalente (SQLite / JSON) para no bloquear el resto del pipeline. El modo activo queda expuesto en `adapter.engine_mode` (`"real"` o `"local_fallback"`).
3. **Banco BISA (grafo)**: modela dos tipos de nodo, `Cliente` y `Cuenta`, unidos por la relación dirigida `POSEE_CUENTA`, persistido en disco en formato JSON (node-link) para que sea una base de datos durable y no solo una estructura en memoria.
4. **Cinco scripts de creación de esquema** ([databases/schema/](databases/schema/)): un `.sql` por motor relacional (SQLite, MySQL, PostgreSQL), un `.js` para MongoDB y un `.cypher` para el modelo de grafo en Neo4j.
5. **Enrutamiento en `BankDatabaseManager`** ([databases/bank_dbs.py](databases/bank_dbs.py)): los Bancos 1-5 se despachan a estos adaptadores dedicados; los Bancos 6-14 (Integrante 2) siguen usando exactamente la misma lógica genérica que antes, sin cambios.

### 📁 Archivos Relacionados

- **Adaptadores Bancos 1-5**: [databases/banks_1_5/](databases/banks_1_5/)
- **Scripts de Creación de Esquema (5)**: [databases/schema/](databases/schema/)
- **Enrutamiento del Manager**: [databases/bank_dbs.py](databases/bank_dbs.py)
- **Infraestructura de Motores Reales**: [docker-compose.yml](docker-compose.yml)
- **Pruebas Unitarias Tarea 2**: [tests/test_tarea2_bank_databases_1_5.py](tests/test_tarea2_bank_databases_1_5.py)

### 🚀 Ejecución

```bash
# Con Docker (motores reales MySQL/PostgreSQL/MongoDB):
docker compose up -d

# Crear el esquema de un banco de forma aislada, p. ej. Banco Unión:
python -m databases.banks_1_5.bank1_union_sqlite

# Pruebas unitarias Tarea 2 (funcionan con o sin Docker, gracias al fallback local):
python -m pytest tests/test_tarea2_bank_databases_1_5.py -v
```
