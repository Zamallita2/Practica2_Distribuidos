-- =============================================================================
-- SCRIPT DE CREACIÓN DE LA BASE DE DATOS RELACIONAL CENTRAL DE LA ASFI
-- Práctica 2: Plataforma Distribuida de Conversión Monetaria Interbancaria
-- Integrante 3: Módulo ASFI Central (Tarea 7)
-- =============================================================================

PRAGMA foreign_keys = ON;

-- 1. Tabla de Catálogo de Entidades Financieras (Bancos)
CREATE TABLE IF NOT EXISTS Bancos (
    BancoId INTEGER PRIMARY KEY,
    Nombre TEXT NOT NULL,
    AlgoritmoEncriptacion TEXT NOT NULL
);

-- 2. Tabla de Cuentas Consolidadas de Ahorristas
CREATE TABLE IF NOT EXISTS Cuentas (
    CuentaId BIGINT PRIMARY KEY,
    BancoId INTEGER NOT NULL,
    SaldoUSD REAL NOT NULL CHECK(SaldoUSD >= 0),
    SaldoBs REAL NOT NULL CHECK(SaldoBs >= 0),
    FechaConversion TEXT NOT NULL,
    CodigoVerificacion CHAR(8) NOT NULL,
    FOREIGN KEY (BancoId) REFERENCES Bancos(BancoId) ON DELETE CASCADE
);

-- 3. Tabla de Registros de Auditoría de Operaciones
CREATE TABLE IF NOT EXISTS AuditLogs (
    LogId INTEGER PRIMARY KEY AUTOINCREMENT,
    Timestamp TEXT NOT NULL,
    ExchangeRate REAL NOT NULL CHECK(ExchangeRate > 0),
    CuentaId BIGINT NOT NULL,
    BancoId INTEGER NOT NULL,
    FOREIGN KEY (BancoId) REFERENCES Bancos(BancoId),
    FOREIGN KEY (CuentaId) REFERENCES Cuentas(CuentaId)
);

-- 4. Inserción de Catálogo Base de 14 Entidades Financieras
INSERT OR IGNORE INTO Bancos (BancoId, Nombre, AlgoritmoEncriptacion) VALUES
(1, 'Banco Unión S.A.', 'Cifrado César'),
(2, 'Banco Mercantil Santa Cruz S.A.', 'Cifrado Atbash'),
(3, 'Banco Nacional de Bolivia S.A.', 'Cifrado Vigenère'),
(4, 'Banco de Crédito de Bolivia S.A.', 'Cifrado Playfair'),
(5, 'Banco BISA S.A.', 'Cifrado Hill'),
(6, 'Banco Ganadero S.A.', 'DES'),
(7, 'Banco Económico S.A.', '3DES'),
(8, 'Banco Prodem S.A.', 'Blowfish'),
(9, 'Banco Solidario S.A.', 'Twofish'),
(10, 'Banco Fortaleza S.A.', 'AES'),
(11, 'Banco FIE S.A.', 'RSA'),
(12, 'Banco PYME de la Comunidad S.A.', 'ElGamal'),
(13, 'Banco de Desarrollo Productivo S.A.M.', 'ECC'),
(14, 'Banco de la Nación Argentina', 'ChaCha20');
