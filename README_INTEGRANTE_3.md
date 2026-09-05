# 🏛️ Módulo Integrante 3: ASFI Central, Barrido Paralelo & Auditoría

Documentación específica del módulo perteneciente al **Integrante 3** (Zama) para la **Plataforma Distribuida de Conversión Monetaria Interbancaria (ASFI - BCB)**.

---

## 🟨 Tarea 7: Base de Datos Central ASFI

Este módulo implementa la arquitectura de base de datos relacional centralizada de la Autoridad de Supervisión del Sistema Financiero (ASFI), la cual consolida la información proveniente de las 14 entidades financieras del país.

### 📋 Componentes Implementados

1. **Tabla de Catálogo de Bancos (`Bancos`)**:
   - `BancoId` (PK): Identificador entero único del banco (1 a 14).
   - `Nombre`: Nombre oficial de la entidad financiera.
   - `AlgoritmoEncriptacion`: Algoritmo asignado por la ASFI a dicho banco (César, Atbash, Vigenère, Playfair, Hill, DES, 3DES, Blowfish, Twofish, AES, RSA, ElGamal, ECC, ChaCha20).

2. **Tabla de Cuentas Consolidadas (`Cuentas`)**:
   - `CuentaId` (PK): Número único de cuenta del ahorrista.
   - `BancoId` (FK -> `Bancos.BancoId`): Identificador del banco emisor.
   - `SaldoUSD`: Saldo original desencriptado en dólares (USD).
   - `SaldoBs`: Saldo oficial convertido a bolivianos (Bs.) según cotización oficial BCB al instante $t_0$.
   - `FechaConversion`: Timestamp exacto de la operación de conversión.
   - `CodigoVerificacion`: Código alfanumérico hexadecimal de 8 caracteres (`0–9, A–F`) generado dinámicamente.

3. **Tabla de Auditoría (`AuditLogs`)**:
   - `LogId` (PK): Identificador incremental del registro.
   - `Timestamp`: Fecha y hora de ejecución.
   - `ExchangeRate`: Tipo de cambio oficial BCB aplicado.
   - `CuentaId` (FK -> `Cuentas.CuentaId`): Cuenta auditada.
   - `BancoId` (FK -> `Bancos.BancoId`): Banco de origen.

4. **Reglas de Integridad y Restricciones**:
   - Activación explícita de `PRAGMA foreign_keys = ON;`.
   - Restricciones `CHECK` para garantizar que los saldos y tipos de cambio sean no negativos.
   - Operaciones atómicas de inserción/actualización con `ON CONFLICT(CuentaId) DO UPDATE`.

---

## 📁 Archivos Relacionados (Integrante 3)

- **Módulo Python BD ASFI**: [databases/asfi_db.py](databases/asfi_db.py)
- **Script SQL de Creación**: [databases/asfi_central_schema.sql](databases/asfi_central_schema.sql)
- **Motor de Barrido Paralelo**: [asfi_central/sweeper.py](asfi_central/sweeper.py)
- **Motor de Procesamiento & Auditoría**: [asfi_central/process_engine.py](asfi_central/process_engine.py)
- **Pruebas Unitarias Tarea 7**: [tests/test_tarea7_asfi_db.py](tests/test_tarea7_asfi_db.py)

---

## 🚀 Ejecución de Pruebas Tarea 7

Para validar el funcionamiento aislado del módulo de la Base de Datos Central ASFI:

```bash
python3 -m unittest tests/test_tarea7_asfi_db.py
```
