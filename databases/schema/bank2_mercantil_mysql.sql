-- =============================================================================
-- SCRIPT DE CREACION DE BASE DE DATOS: BANCO MERCANTIL SANTA CRUZ S.A.
-- Motor: MySQL / MariaDB (Relacional) | Algoritmo de cifrado asignado: Atbash
-- Practica 2: Plataforma Distribuida de Conversion Monetaria Interbancaria
-- Integrante 1: Bases de Datos Bancos 1-5 (Tarea 2)
--
-- Uso: mysql -u root -p < bank2_mercantil_mysql.sql
-- (los mismos DDL se ejecutan automaticamente vía pymysql en
--  databases/banks_1_5/bank2_mercantil_mysql.py cuando el servidor esta disponible)
-- =============================================================================

CREATE DATABASE IF NOT EXISTS banco_mercantil
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE banco_mercantil;

CREATE TABLE IF NOT EXISTS CuentasBancarias (
    CuentaId BIGINT PRIMARY KEY,
    ClienteNombre VARCHAR(255) NOT NULL,
    SaldoUSDCifrado TEXT NOT NULL,
    SaldoBs DOUBLE DEFAULT 0.0,
    CodigoVerificacion VARCHAR(8) DEFAULT '',
    FechaConversion VARCHAR(32) DEFAULT ''
);
