-- =============================================================================
-- SCRIPT DE CREACION DE BASE DE DATOS: BANCO NACIONAL DE BOLIVIA S.A. (BNB)
-- Motor: PostgreSQL (Relacional) | Algoritmo de cifrado asignado: Vigenere
-- Practica 2: Plataforma Distribuida de Conversion Monetaria Interbancaria
-- Integrante 1: Bases de Datos Bancos 1-5 (Tarea 2)
--
-- Uso: psql -U postgres -d banco_bnb -f bank3_bnb_postgres.sql
-- (los mismos DDL se ejecutan automaticamente vía psycopg2 en
--  databases/banks_1_5/bank3_bnb_postgres.py cuando el servidor esta disponible)
-- =============================================================================

CREATE TABLE IF NOT EXISTS CuentasBancarias (
    CuentaId BIGINT PRIMARY KEY,
    ClienteNombre VARCHAR(255) NOT NULL,
    SaldoUSDCifrado TEXT NOT NULL,
    SaldoBs DOUBLE PRECISION DEFAULT 0.0,
    CodigoVerificacion VARCHAR(8) DEFAULT '',
    FechaConversion VARCHAR(32) DEFAULT ''
);
