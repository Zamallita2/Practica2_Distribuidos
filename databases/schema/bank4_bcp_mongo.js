// =============================================================================
// SCRIPT DE CREACION DE BASE DE DATOS: BANCO DE CREDITO DE BOLIVIA S.A. (BCP)
// Motor: MongoDB (No Relacional / Documental) | Algoritmo asignado: Playfair
// Practica 2: Plataforma Distribuida de Conversion Monetaria Interbancaria
// Integrante 1: Bases de Datos Bancos 1-5 (Tarea 2)
//
// Uso: mongosh banco_bcp bank4_bcp_mongo.js
// (la misma validacion/coleccion se crea automaticamente vía pymongo en
//  databases/banks_1_5/bank4_bcp_mongo.py cuando el servidor esta disponible)
// =============================================================================

db.createCollection("CuentasBancarias", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["cuenta_id", "cliente_nombre", "saldo_usd_cifrado"],
            properties: {
                cuenta_id: { bsonType: ["long", "int"] },
                cliente_nombre: { bsonType: "string" },
                saldo_usd_cifrado: { bsonType: "string" },
                saldo_bs: { bsonType: "double" },
                codigo_verificacion: { bsonType: "string" },
                fecha_conversion: { bsonType: "string" }
            }
        }
    }
});

db.CuentasBancarias.createIndex({ cuenta_id: 1 }, { unique: true });
