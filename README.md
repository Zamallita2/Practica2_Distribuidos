# 🏛️ Plataforma Distribuida de Conversión Monetaria Interbancaria (ASFI - BCB)

Sistema distribuido seguro y heterogéneo para la consolidación y conversión de cuentas en dólares (USD) a bolivianos (Bs.) de las 14 entidades financieras participantes de Bolivia, con cifrado criptográfico heterogéneo, cotización dinámica del Banco Central de Bolivia (BCB), barrido paralelo asíncrono y registros de auditoría en la ASFI.

---

## 📢 Resumen General de Tareas por Integrante (Para Presentación / Lectura Rápida)

Si necesitas compartir con tu equipo qué debe hacer cada uno de forma rápida y sin rodeos:

- **👤 Integrante 1 (Algoritmos Clásicos & Bancos del 1 al 5)**:
  - Implementa los algoritmos de encriptación clásicos: César, Atbash, Vigenère, Playfair y Hill.
  - Administra las bases de datos de los Bancos 1 al 5 (Unión, Mercantil, BNB, BCP y BISA).
  - Encargado de la **Base de Datos orientada a Grafos** para el Banco BISA (modelando nodos `Cliente` y `Cuenta` con relaciones de propiedad).

- **👤 Integrante 2 (Algoritmos Avanzados, Bancos del 6 al 14 & Simulador de Cotización BCB)**:
  - Implementa el **Simulador del Valor del Dólar (BCB)** que fluctúa la cotización automáticamente cada 3 minutos en un rango de $\pm 0.9999$ con 4 decimales.
  - Implementa los algoritmos simétricos y asimétricos: DES, 3DES, Blowfish, Twofish, AES, RSA, ElGamal, ECC y ChaCha20.
  - Administra las bases de datos de los Bancos 6 al 14 (Ganadero, Económico, Prodem, Solidario, Fortaleza, FIE, PYME, BDP y Nación Argentina).

- **👤 Integrante 3 (ASFI Central, Barrido Paralelo & Orquestador de Transacciones)**:
  - Diseña la **Base de Datos Central Relacional de la ASFI** (`Bancos`, `Cuentas` consolidadas y `AuditLogs`).
  - Desarrolla el motor de **Barrido Paralelo Asíncrono** que extrae en tiempo real la información de los 14 bancos de forma simultánea a una misma cotización $t_0$.
  - Implementa el descifrado, la conversión a bolivianos, la generación del **código verificador de 8 caracteres hexadecimales** para sincronización con los bancos y los registros de auditoría.

---

## 👥 División Técnica Detallada (Sin Bloqueos Ni Dependencias)

```
+-----------------------------------------------------------------------------------+
|                            INTEGRANTE 1: Crypto & Bancos 1-5                      |
| - Módulo Criptográfico Clásico y Matemático (crypto/classical.py)                 |
| - Bancos 1 al 5: Unión, Mercantil, BNB, BCP, BISA                                 |
| - DBs: SQLite, MySQL, PostgreSQL, MongoDB, NetworkX Graph DB                      |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
|                            INTEGRANTE 2: BCB Engine & Bancos 6-14                 |
| - Simulador de Cotización BCB (bcb_service/rate_engine.py)                        |
| - Bancos 6 al 14: Ganadero, Económico, Prodem, Soli, Fortaleza, FIE, PYME, BDP, BNA |
| - Cifrados Simétricos / Asimétricos: DES, 3DES, Blowfish, Twofish, AES, RSA, ECC...|
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
|                            INTEGRANTE 3: ASFI Central & Sweeper Paralelo         |
| - Base de Datos Centralizada ASFI (databases/asfi_db.py)                          |
| - Motor de Barrido Paralelo Asíncrono (asfi_central/sweeper.py)                   |
| - Orquestador ASFI, Auditoría y Código Verificador (asfi_central/process_engine.py)|
+-----------------------------------------------------------------------------------+
```

---

## 🗺️ Mapeo General de Entidades, Cifrados y Motores de BD

| ID | Entidad Financiera | Algoritmo Cifrado | Tipo de BD | Motor de BD | Asignado a |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | Banco Unión S.A. | Cifrado César | Relacional (1) | SQLite | **Integrante 1** |
| **2** | Banco Mercantil Santa Cruz S.A. | Cifrado Atbash | Relacional (2) | MySQL / MariaDB | **Integrante 1** |
| **3** | Banco Nacional de Bolivia S.A. | Cifrado Vigenère | Relacional (3) | PostgreSQL | **Integrante 1** |
| **4** | Banco de Crédito de Bolivia S.A. | Cifrado Playfair | No Relacional (1) | MongoDB | **Integrante 1** |
| **5** | Banco BISA S.A. | Cifrado Hill | **Grafo (No Relacional 2)** | NetworkX / Neo4j | **Integrante 1** |
| **6** | Banco Ganadero S.A. | DES | Relacional | SQLite | **Integrante 2** |
| **7** | Banco Económico S.A. | 3DES | Relacional | PostgreSQL | **Integrante 2** |
| **8** | Banco Prodem S.A. | Blowfish | No Relacional | MongoDB | **Integrante 2** |
| **9** | Banco Solidario S.A. | Twofish | Relacional | MySQL | **Integrante 2** |
| **10** | Banco Fortaleza S.A. | AES | Relacional | PostgreSQL | **Integrante 2** |
| **11** | Banco FIE S.A. | RSA | Relacional | SQLite | **Integrante 2** |
| **12** | Banco PYME de la Comunidad S.A. | ElGamal | Relacional | MySQL | **Integrante 2** |
| **13** | Banco BDP S.A.M. | ECC | Relacional | PostgreSQL | **Integrante 2** |
| **14** | Banco de la Nación Argentina | ChaCha20 | No Relacional | JSON / DuckDB | **Integrante 2** |

---

## 🔄 Comandos de Población de Datos con Muestreo Configurable (%)

Puedes volver a extraer cualquier porcentaje del dataset CSV (`01 - Practica 2 Dataset.csv`) usando los siguientes comandos:

### 🔹 Extraer el 1% por defecto (Estratificado por Banco):
```bash
python3 scripts/seed_all.py
```

### 🔹 Extraer un Porcentaje Personalizado (ej. 1%, 2.5%, 5%):
```bash
# Para extraer exactamente el 1%:
python3 scripts/seed_all.py --percent 1.0

# Para extraer el 2.5%:
python3 scripts/seed_all.py --percent 2.5

# Para extraer el 5%:
python3 scripts/seed_all.py --percent 5.0
```

---

## 🛠️ Estructura del Repositorio

```
.
├── 01 - Practica 2 Dataset.csv                      <- Dataset oficial con cuentas bancarias
├── 01 - Practica 2 Algoritmos de Encriptacion.txt  <- Especificación oficial del proyecto
├── README.md                                        <- Documentación técnica del proyecto
├── config.py                                        <- Parámetros globales y catálogo
├── requirements.txt                                 <- Dependencias de Python
├── crypto/                                          <- Cifrados Criptográficos
│   ├── classical.py                                 <- César, Atbash, Vigenère, Playfair, Hill
│   ├── symmetric.py                                 <- DES, 3DES, Blowfish, Twofish, AES, ChaCha20
│   └── asymmetric.py                                <- RSA, ElGamal, ECC
├── bcb_service/                                     <- Servicio BCB
│   └── rate_engine.py                               <- Motor de cambio dinámico (±0.9999)
├── databases/                                       <- Capa de Persistencia
│   ├── asfi_db.py                                   <- BD Central ASFI
│   ├── bank_dbs.py                                  <- Adaptadores 14 Bancos (Relacional, NoSQL, Grafo)
│   └── seed_data.py                                 <- Ingesta y muestreo configurable desde CSV
├── banks/                                           <- Microservicios Bancarios API
│   └── bank_router.py                               <- Endpoints /api/bank/{id}/accounts y /verify
├── asfi_central/                                    <- Orquestador Central ASFI
│   ├── sweeper.py                                   <- Barrido Paralelo Asíncrono
│   └── process_engine.py                            <- Descifrado, Conversión, Hex Code & Auditoría
├── scripts/                                         <- Scripts de Ejecución
│   ├── generate_sample_excel.py                     <- Generador de Dataset de prueba auxiliar
│   ├── seed_all.py                                  <- Poblador configurable de las 14 BDs
│   └── run_system.py                                <- Ejecutor Maestro de la Simulación
└── tests/                                           <- Suite de Pruebas Unitarias
    └── test_system.py
```

---

## 🚀 Guía Rápida de Ejecución

1. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Poblar las 14 bases de datos con el 1% del CSV**:
   ```bash
   python3 scripts/seed_all.py --percent 1.0
   ```

3. **Ejecutar la Simulación Distribuida Completa**:
   ```bash
   python3 scripts/run_system.py
   ```

4. **Ejecutar Pruebas Unitarias**:
   ```bash
   python3 -m unittest discover tests
   ```
