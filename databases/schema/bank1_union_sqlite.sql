-- =============================================================================
-- SCRIPT DE CREACION DE BASE DE DATOS: BANCO UNION S.A.
-- Motor: SQLite (Relacional) | Algoritmo de cifrado asignado: Cesar
-- Practica 2: Plataforma Distribuida de Conversion Monetaria Interbancaria
-- Integrante 1: Bases de Datos Bancos 1-5 (Tarea 2)
-- =============================================================================

CREATE TABLE IF NOT EXISTS CuentasBancarias (
    CuentaId INTEGER PRIMARY KEY,
    ClienteNombre TEXT NOT NULL,
    SaldoUSDCifrado TEXT NOT NULL,
    SaldoBs REAL DEFAULT 0.0,
    CodigoVerificacion TEXT DEFAULT '',
    FechaConversion TEXT DEFAULT ''
);
