"""
Servidor Web HTTP REST y Dashboard Interactivo (ASFI Central - BCB - 14 Bancos)
Escucha en http://localhost:8080 y no requiere dependencias externas.
"""

import http.server
import socketserver
import json
import os
import sys
import asyncio
import urllib.parse
from http import HTTPStatus

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config import BANKS, AUDIT_LOG_FILE, ASFI_DB_PATH
from bcb_service.rate_engine import bcb_engine
from databases.seed_data import seed_bank_databases_from_csv
from databases.bank_dbs import bank_db_manager
from databases.asfi_db import asfi_db
from databases.dataset_manager import (
    get_dataset_info,
    get_active_dataset_path,
    save_uploaded_csv,
    wipe_all_databases,
)
from asfi_central.sweeper import sweeper
from asfi_central.cpu_monitor import cpu_monitor

PORT = 8080
STATIC_DIR = os.path.join(os.path.dirname(__file__), "web_dashboard")

# Consultas específicas por banco según motor/paradigma
BANK_QUERIES = {
    1: {
        "select": "SELECT CuentaId, ClienteNombre, SaldoUSDCifrado, SaldoBs, CodigoVerificacion FROM CuentasBancarias;",
        "update": "UPDATE CuentasBancarias SET SaldoBs = ?, CodigoVerificacion = ?, FechaConversion = ? WHERE CuentaId = ?;"
    },
    2: {
        "select": "SELECT CuentaId, ClienteNombre, SaldoUSDCifrado, SaldoBs, CodigoVerificacion FROM CuentasBancarias;",
        "update": "UPDATE CuentasBancarias SET SaldoBs = ?, CodigoVerificacion = ?, FechaConversion = ? WHERE CuentaId = ?;"
    },
    3: {
        "select": "SELECT CuentaId, ClienteNombre, SaldoUSDCifrado, SaldoBs, CodigoVerificacion FROM CuentasBancarias;",
        "update": "UPDATE CuentasBancarias SET SaldoBs = %s, CodigoVerificacion = %s, FechaConversion = %s WHERE CuentaId = %s;"
    },
    4: {
        "select": "db.bcp_accounts.find({}, {cuenta_id: 1, cliente_nombre: 1, saldo_usd_cifrado: 1, saldo_bs: 1, codigo_verificacion: 1});",
        "update": "db.bcp_accounts.updateOne({cuenta_id: 404}, {$set: {saldo_bs: 7238.8, codigo_verificacion: 'FEEDBEEF'}});"
    },
    5: {
        "select": "MATCH (c:Cliente)-[:POSEE_CUENTA]->(a:Cuenta) RETURN c.nombre, a.cuenta_id, a.saldo_usd_cifrado, a.saldo_bs, a.codigo_verificacion;",
        "update": "MATCH (a:Cuenta {cuenta_id: 505}) SET a.saldo_bs = 7238.8, a.codigo_verificacion = 'A1B2C3D4', a.fecha_conversion = timestamp();"
    }
}

for i in range(6, 15):
    b_type = next((b["db_engine"] for b in BANKS if b["id"] == i), "Relacional")
    if "MongoDB" in b_type or "JSON" in b_type:
        BANK_QUERIES[i] = {
            "select": f"db.bank_{i}_accounts.find({{}}, {{cuenta_id: 1, saldo_usd_cifrado: 1, saldo_bs: 1, codigo_verificacion: 1}});",
            "update": f"db.bank_{i}_accounts.updateOne({{cuenta_id: ID}}, {{$set: {{saldo_bs: BS, codigo_verificacion: 'HEX'}}}});"
        }
    else:
        BANK_QUERIES[i] = {
            "select": "SELECT CuentaId, ClienteNombre, SaldoUSDCifrado, SaldoBs, CodigoVerificacion FROM CuentasBancarias;",
            "update": "UPDATE CuentasBancarias SET SaldoBs = ?, CodigoVerificacion = ?, FechaConversion = ? WHERE CuentaId = ?;"
        }

class ASFIHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):

    def send_json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/' or path == '/index.html':
            filepath = os.path.join(STATIC_DIR, 'index.html')
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, "Dashboard HTML not found")
                return

        elif path == '/api/status':
            asfi_accs = asfi_db.get_all_accounts()
            self.send_json({
                "status": "online",
                "banks_count": len(BANKS),
                "asfi_accounts_count": len(asfi_accs)
            })

        elif path == '/api/bcb-rate':
            rate = bcb_engine.get_current_rate()
            self.send_json(rate)

        elif path == '/api/cpu-stats':
            self.send_json(cpu_monitor.sample())

        elif path == '/api/dataset':
            self.send_json(get_dataset_info())

        elif path == '/api/banks':
            result = []
            for b in BANKS:
                b_id = b["id"]
                queries = BANK_QUERIES.get(b_id, {})
                accounts = bank_db_manager.get_encrypted_accounts(b_id)
                result.append({
                    "id": b_id,
                    "name": b["name"],
                    "algorithm": b["algorithm"],
                    "db_type": b["db_type"],
                    "db_engine": b["db_engine"],
                    "select_query": queries.get("select", ""),
                    "update_query": queries.get("update", ""),
                    "total_accounts": len(accounts),
                    "sample_accounts": accounts[:15]
                })
            self.send_json(result)

        elif path == '/api/audit-logs':
            db_logs = asfi_db.get_audit_logs()
            formatted = []
            for row in db_logs:
                # row: (log_id, timestamp, exchange_rate, cuenta_id, banco_id, verification_code)
                formatted.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "rate": row[2],
                    "account_id": row[3],
                    "bank_id": row[4],
                    "hex_code": row[5] if len(row) > 5 else ""
                })
            self.send_json(formatted)

        else:
            self.send_error(404, "Endpoint not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        payload = {}
        if post_data:
            try:
                payload = json.loads(post_data.decode('utf-8'))
            except Exception:
                pass

        if path == '/api/bcb-interval':
            interval = int(payload.get("interval", 5))
            if interval > 0:
                bcb_engine.set_interval(interval)
            self.send_json({"success": True, "new_interval": bcb_engine.interval, "rate": bcb_engine.get_current_rate()})

        elif path == '/api/seed':
            try:
                percent = float(payload.get("percent", 1.0))
                sample_rate = percent / 100.0 if percent >= 1.0 else percent
                csv_path = payload.get("csv_path") or get_active_dataset_path()
                if not os.path.exists(csv_path):
                    self.send_json({"success": False, "error": f"CSV no encontrado: {csv_path}"}, status=HTTPStatus.BAD_REQUEST)
                    return
                stats = seed_bank_databases_from_csv(csv_path, sample_rate)
                self.send_json({"success": True, "csv_path": csv_path, "dataset": get_dataset_info(), **stats})
            except Exception as ex:
                self.send_json({"success": False, "error": str(ex)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        elif path == '/api/wipe-dbs':
            try:
                result = wipe_all_databases()
                self.send_json(result)
            except Exception as ex:
                self.send_json({"success": False, "error": str(ex)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        elif path == '/api/upload-csv':
            try:
                filename = self.headers.get('X-Filename', 'dataset.csv')
                if not post_data:
                    self.send_json({"success": False, "error": "Archivo vacío"}, status=HTTPStatus.BAD_REQUEST)
                    return
                info = save_uploaded_csv(filename, post_data)
                self.send_json({"success": True, "dataset": info, "bytes": len(post_data)})
            except Exception as ex:
                self.send_json({"success": False, "error": str(ex)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        elif path == '/api/query-asfi':
            query_str = str(payload.get("query", "")).strip()
            try:
                import sqlite3
                conn = sqlite3.connect(ASFI_DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                sql = query_str if query_str else "SELECT * FROM Cuentas LIMIT 50;"
                cursor.execute(sql)
                if sql.lstrip().upper().startswith("SELECT") or not query_str:
                    rows = cursor.fetchall()
                    results = [dict(row) for row in rows]
                    conn.close()
                    self.send_json({"success": True, "db_type": "ASFI Central (SQLite)", "count": len(results), "results": results})
                else:
                    conn.commit()
                    affected = cursor.rowcount
                    conn.close()
                    self.send_json({"success": True, "db_type": "ASFI Central (SQLite)", "count": affected, "results": [{"Mensaje": f"Consulta ejecutada con éxito. Filas afectadas: {affected}"}]})
            except Exception as ex:
                self.send_json({"error": str(ex)})

        elif path == '/api/query-bank':
            bank_id = int(payload.get("bank_id", 1))
            query_str = str(payload.get("query", "")).strip()

            try:
                # Bancos 1 a 5 (Adaptadores Específicos)
                if bank_id in bank_db_manager.banks_1_5:
                    adapter = bank_db_manager.banks_1_5[bank_id]
                    
                    # Banco 2 (Mercantil MySQL) y Banco 3 (BNB Postgres)
                    # Usa motor real si Docker está arriba; si no, el SQLite de contingencia.
                    if bank_id in (2, 3):
                        default_sql = "SELECT CuentaId, ClienteNombre, SaldoUSDCifrado, SaldoBs, CodigoVerificacion FROM CuentasBancarias LIMIT 20;"
                        sql = query_str if query_str else default_sql
                        is_select = (not query_str) or sql.lstrip().upper().startswith("SELECT")

                        if getattr(adapter, "engine_mode", "local_fallback") == "real":
                            if bank_id == 2:
                                conn = adapter._connect_mysql()
                                cursor = conn.cursor()
                                cursor.execute(sql)
                                if is_select:
                                    cols = [d[0] for d in cursor.description]
                                    results = [dict(zip(cols, row)) for row in cursor.fetchall()]
                                    conn.close()
                                    self.send_json({"success": True, "db_type": "Relacional (MySQL real)", "count": len(results), "results": results})
                                else:
                                    conn.commit()
                                    affected = cursor.rowcount
                                    conn.close()
                                    self.send_json({"success": True, "db_type": "Relacional (MySQL real)", "count": affected, "results": [{"Mensaje": f"Ejecutado con éxito. Filas afectadas: {affected}"}]})
                            else:
                                conn = adapter._connect_postgres()
                                cursor = conn.cursor()
                                cursor.execute(sql)
                                if is_select:
                                    cols = [d[0] for d in cursor.description]
                                    results = [dict(zip(cols, row)) for row in cursor.fetchall()]
                                    conn.close()
                                    self.send_json({"success": True, "db_type": "Relacional (PostgreSQL real)", "count": len(results), "results": results})
                                else:
                                    conn.commit()
                                    affected = cursor.rowcount
                                    conn.close()
                                    self.send_json({"success": True, "db_type": "Relacional (PostgreSQL real)", "count": affected, "results": [{"Mensaje": f"Ejecutado con éxito. Filas afectadas: {affected}"}]})
                        else:
                            fallback_file = getattr(adapter, "fallback_path", None)
                            if fallback_file and os.path.exists(fallback_file):
                                import sqlite3
                                conn = sqlite3.connect(fallback_file)
                                conn.row_factory = sqlite3.Row
                                cursor = conn.cursor()
                                cursor.execute(sql)
                                if is_select:
                                    rows = cursor.fetchall()
                                    results = [dict(row) for row in rows]
                                    conn.close()
                                    self.send_json({"success": True, "db_type": "Relacional (local_fallback SQLite)", "count": len(results), "results": results})
                                else:
                                    conn.commit()
                                    affected = cursor.rowcount
                                    conn.close()
                                    self.send_json({"success": True, "db_type": "Relacional (local_fallback SQLite)", "count": affected, "results": [{"Mensaje": f"Ejecutado con éxito. Filas afectadas: {affected}"}]})
                            else:
                                accounts = adapter.get_encrypted_accounts()
                                self.send_json({"success": True, "db_type": f"Relacional ({adapter.engine_mode})", "count": len(accounts), "results": accounts[:50]})

                    elif bank_id == 1:
                        db_file = getattr(adapter, "db_path", os.path.join(bank_db_manager.data_dir, "bank_1.db"))
                        import sqlite3
                        conn = sqlite3.connect(db_file)
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        cursor.execute(query_str if query_str else "SELECT * FROM CuentasBancarias LIMIT 20;")
                        rows = cursor.fetchall()
                        results = [dict(row) for row in rows]
                        conn.close()
                        self.send_json({"success": True, "db_type": "Relacional (SQLite)", "count": len(results), "results": results})

                    elif bank_id == 4:
                        accounts = adapter.get_encrypted_accounts()
                        self.send_json({"success": True, "db_type": "NoSQL (MongoDB Store)", "count": len(accounts), "results": accounts})

                    elif bank_id == 5:
                        accounts = adapter.get_encrypted_accounts()
                        results = []
                        for acc in accounts:
                            results.append({
                                "NodoCuentaID": acc.get("cuenta_id"),
                                "Cliente": acc.get("cliente_nombre"),
                                "SaldoUSDCifrado": acc.get("saldo_usd_cifrado"),
                                "SaldoBs": acc.get("saldo_bs"),
                                "CodigoVerificacion": acc.get("codigo_verificacion")
                            })
                        self.send_json({"success": True, "db_type": "Grafo (NetworkX / Neo4j)", "count": len(results), "results": results})

                # Bancos 6 a 14 (Genéricos SQLite / NoSQL / Grafo)
                elif bank_id in (4, 8, 14):
                    json_path = os.path.join(bank_db_manager.data_dir, f"bank_{bank_id}_nosql.json")
                    if not os.path.exists(json_path):
                        json_path = f"bank_{bank_id}_nosql.json"
                    if os.path.exists(json_path):
                        with open(json_path, "r") as f:
                            data = json.load(f)

                        filtered = data
                        if query_str and not query_str.upper().startswith("SELECT * FROM") and not query_str.startswith("db."):
                            q_lower = query_str.lower()
                            # Soporta filtrado por subcadena o clave:valor
                            if ":" in query_str:
                                k, v = [x.strip() for x in query_str.split(":", 1)]
                                filtered = [d for d in data if str(d.get(k, "")).lower() == v.lower()]
                            elif "=" in query_str and "where" in q_lower:
                                # Parsear cláusula WHERE básica ej: WHERE cuenta_id = 100123
                                where_clause = query_str[q_lower.find("where")+5:].strip()
                                if "=" in where_clause:
                                    k, v = [x.strip(" '\"") for x in where_clause.split("=", 1)]
                                    filtered = [d for d in data if str(d.get(k, "")).lower() == v.lower() or str(d.get("cuenta_id", "")).lower() == v.lower()]
                            else:
                                filtered = [d for d in data if q_lower in json.dumps(d).lower()]

                        self.send_json({"success": True, "db_type": "NoSQL (JSON Store)", "count": len(filtered), "results": filtered})
                    else:
                        self.send_json({"error": f"Almacén NoSQL para Banco #{bank_id} no encontrado."})

                else:
                    import sqlite3
                    db_file = os.path.join(bank_db_manager.data_dir, f"bank_{bank_id}.db")
                    if not os.path.exists(db_file):
                        db_file = f"bank_{bank_id}.db"

                    if os.path.exists(db_file):
                        conn = sqlite3.connect(db_file)
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        cursor.execute(query_str if query_str else "SELECT * FROM CuentasBancarias;")
                        if query_str.upper().startswith("SELECT") or not query_str:
                            rows = cursor.fetchall()
                            results = [dict(row) for row in rows]
                            conn.close()
                            self.send_json({"success": True, "db_type": "Relacional (SQLite)", "count": len(results), "results": results})
                        else:
                            conn.commit()
                            affected = cursor.rowcount
                            conn.close()
                            self.send_json({"success": True, "db_type": "Relacional (SQLite)", "count": affected, "results": [{"Mensaje": f"Consulta ejecutada con éxito. Filas afectadas: {affected}"}]})
                    else:
                        self.send_json({"error": f"Base de datos SQLite del Banco #{bank_id} no existe en disco."})
            except Exception as ex:
                self.send_json({"error": str(ex)})

        elif path == '/api/run-sweep':
            use_dynamic = payload.get("dynamic_rate", True)
            update_db = payload.get("update_bank_db", True)
            reset_first = payload.get("reset_first", False)
            sweep_res = asyncio.run(sweeper.execute_parallel_sweep(
                use_dynamic_rate=use_dynamic,
                update_bank_db=update_db,
                reset_first=reset_first
            ))
            self.send_json(sweep_res)

        else:
            self.send_error(404, "Endpoint not found")

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

def run_server(port=PORT):
    server_address = ('', port)
    httpd = ThreadedHTTPServer(server_address, ASFIHTTPRequestHandler)
    print(f"=========================================================================")
    print(f"🌐  SERVIDOR WEB DASHBOARD ASFI - INICIADO EN HTTP://LOCALHOST:{port}")
    print(f"=========================================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor web detenido.")
        httpd.server_close()

if __name__ == "__main__":
    if "--test" in sys.argv:
        print("✅ Módulo web_server importado y verificado correctamente.")
        sys.exit(0)
    run_server()
