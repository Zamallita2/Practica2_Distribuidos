// =============================================================================
// SCRIPT DE CREACION DE BASE DE DATOS: BANCO BISA S.A.
// Motor: Grafo (No Relacional) - Neo4j / NetworkX | Algoritmo asignado: Hill
// Practica 2: Plataforma Distribuida de Conversion Monetaria Interbancaria
// Integrante 1: Bases de Datos Bancos 1-5 (Tarea 2)
//
// Modelo: dos tipos de nodo, Cliente y Cuenta, unidos por la relacion
// POSEE_CUENTA (Cliente -> Cuenta), tal como exige la rubrica de grafos.
//
// Uso (si se dispone de un servidor Neo4j real):
//   cypher-shell -u neo4j -p password123 -f bank5_bisa_graph.cypher
// En ausencia de un servidor Neo4j, el motor equivalente en Python usa
// NetworkX (grafo dirigido embebido, persistido en JSON node-link) -- ver
// databases/banks_1_5/bank5_bisa_graph.py -- con la misma estructura de nodos
// y relaciones descrita aqui.
// =============================================================================

CREATE CONSTRAINT cliente_nombre_unique IF NOT EXISTS
FOR (c:Cliente) REQUIRE c.nombre IS UNIQUE;

CREATE CONSTRAINT cuenta_id_unique IF NOT EXISTS
FOR (c:Cuenta) REQUIRE c.cuenta_id IS UNIQUE;

// Ejemplo de insercion de un nodo Cliente y su Cuenta relacionada:
// MERGE (cliente:Cliente {nombre: $cliente_nombre})
// MERGE (cuenta:Cuenta {cuenta_id: $cuenta_id})
// SET cuenta.saldo_usd_cifrado = $saldo_cifrado,
//     cuenta.saldo_bs = 0.0,
//     cuenta.codigo_verificacion = '',
//     cuenta.fecha_conversion = ''
// MERGE (cliente)-[:POSEE_CUENTA]->(cuenta)
