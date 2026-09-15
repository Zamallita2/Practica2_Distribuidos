"""
Servidor Worker de Carga Distribuida LAN (ASFI Sistema Bancario)
=================================================================
Se registra con el Maestro y espera tareas. Al recibir un mini-CSV,
ejecuta la ingesta local en las bases de datos de los bancos asignados
y reporta el resultado al Maestro.

Uso:
  # En la PC secundaria (o en la misma PC para modo single-node):
  python -m distributed.worker_server [--master-ip 192.168.1.100]

  # El worker se autoregistra al levantar y empieza a pedir tareas.
"""

import os
import sys
import io
import csv
import json
import time
import base64
import socket
import threading
import http.server
import socketserver
import urllib.request
import urllib.parse
import urllib.error
import argparse
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

WORKER_PORT = 9001
MASTER_PORT = 8080   # Puerto del dashboard/API principal (siempre disponible)
POLL_INTERVAL = 2.0   # segundos entre solicitudes de tarea al maestro


class DistributedWorker:
    """
    Worker que pide tareas al Maestro, ejecuta la ingesta local
    y reporta los resultados.
    """
    def __init__(self, master_ip: str = "127.0.0.1"):
        self.master_ip = master_ip
        self._running = False
        self._lock = threading.Lock()
        self.current_task_id = None
        self.stats = {
            "tasks_completed": 0,
            "total_inserted": 0,
            "total_errors": 0,
            "uptime_start": time.time(),
        }

    @property
    def master_url(self):
        # Lee MASTER_PORT dinámicamente para que --master-port CLI funcione
        import distributed.worker_server as _mod
        return f"http://{self.master_ip}:{_mod.MASTER_PORT}"

    # ------------------------------------------------------------------ #
    # Comunicación con el Maestro                                         #
    # ------------------------------------------------------------------ #
    def _request_task(self) -> dict | None:
        """Solicita una tarea al Maestro vía GET /task."""
        try:
            url = f"{self.master_url}/task"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data if data.get("has_task") else None
        except Exception as ex:
            print(f"⚠️ [Worker] Error al solicitar tarea: {ex}")
            return None

    def _report_done(self, task_id: str, result: dict):
        """Reporta al Maestro que la tarea fue completada."""
        try:
            payload = json.dumps({"task_id": task_id, "result": result}).encode("utf-8")
            req = urllib.request.Request(
                f"{self.master_url}/done",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as ex:
            print(f"⚠️ [Worker] Error al reportar tarea {task_id}: {ex}")

    # ------------------------------------------------------------------ #
    # Ejecución de la ingesta local                                       #
    # ------------------------------------------------------------------ #
    def _execute_task(self, task: dict) -> dict:
        """
        Recibe la tarea del Maestro, guarda el mini-CSV en un archivo
        temporal y llama a seed_bank_databases_from_csv().
        """
        task_id = task["task_id"]
        bank_ids = task.get("bank_ids", [])
        csv_b64 = task["csv_b64"]
        row_count = task.get("row_count", 0)
        sample_rate = float(task.get("sample_rate", 1.0))

        print(f"\n🔧 [Worker] Ejecutando tarea {task_id}")
        print(f"   Bancos: {bank_ids} | Filas: {row_count}")

        try:
            # Decodificar el mini-CSV y guardarlo en un archivo temporal
            csv_bytes = base64.b64decode(csv_b64.encode("ascii"))
            csv_content = csv_bytes.decode("utf-8")

            # Guardar en archivo temporal (seed_data.py necesita un path)
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".csv", delete=False,
                encoding="utf-8", prefix=f"asfi_worker_{task_id}_"
            )
            tmp.write(csv_content)
            tmp.close()
            tmp_path = tmp.name

            t0 = time.time()
            try:
                from databases.seed_data import seed_bank_databases_from_csv
                result = seed_bank_databases_from_csv(tmp_path, sample_rate)
                elapsed = round(time.time() - t0, 3)
                result["elapsed_seconds"] = elapsed
                result["task_id"] = task_id
                result["bank_ids"] = bank_ids
                result["success"] = True
                print(f"   ✅ Tarea {task_id} completada: {result.get('total_inserted', 0)} cuentas en {elapsed}s")
                return result
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        except Exception as ex:
            print(f"   ❌ Error en tarea {task_id}: {ex}")
            return {
                "success": False,
                "task_id": task_id,
                "bank_ids": bank_ids,
                "error": str(ex),
                "total_inserted": 0,
                "insert_errors": 1,
            }

    # ------------------------------------------------------------------ #
    # Loop principal del worker                                           #
    # ------------------------------------------------------------------ #
    def run_polling_loop(self):
        """Loop que pide tareas al maestro periódicamente."""
        print(f"🤖 [Worker] Iniciado → Maestro en {self.master_url}")
        self._running = True
        while self._running:
            task = self._request_task()
            if task:
                with self._lock:
                    self.current_task_id = task["task_id"]
                result = self._execute_task(task)
                self._report_done(task["task_id"], result)
                with self._lock:
                    self.current_task_id = None
                    self.stats["tasks_completed"] += 1
                    self.stats["total_inserted"] += result.get("total_inserted", 0)
                    self.stats["total_errors"] += result.get("insert_errors", 0)
            else:
                time.sleep(POLL_INTERVAL)

    def stop(self):
        self._running = False

    def get_stats(self) -> dict:
        with self._lock:
            uptime = round(time.time() - self.stats["uptime_start"], 1)
            local_ip = _get_local_ip()
            return {
                "worker_ip": local_ip,
                "master_ip": self.master_ip,
                "current_task": self.current_task_id,
                "tasks_completed": self.stats["tasks_completed"],
                "total_inserted": self.stats["total_inserted"],
                "total_errors": self.stats["total_errors"],
                "uptime_seconds": uptime,
                "status": "busy" if self.current_task_id else "idle",
            }


def _get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


# Instancia global del worker
_worker_instance: DistributedWorker | None = None
_worker_thread: threading.Thread | None = None


# ------------------------------------------------------------------ #
# Servidor HTTP del Worker (para que el Maestro lo detecte y          #
# para consultar su estado)                                           #
# ------------------------------------------------------------------ #
class WorkerHTTPHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # Silenciar logs del servidor

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/status", "/ping"):
            if _worker_instance:
                self.send_json({"online": True, **_worker_instance.get_stats()})
            else:
                self.send_json({"online": True, "status": "idle", "worker_ip": _get_local_ip()})
        else:
            self.send_json({"error": "Endpoint no encontrado"}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        payload = {}
        if body:
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                pass

        if path == "/configure":
            # El maestro puede reconfigurar el worker (ej: cambiar master_ip)
            master_ip = payload.get("master_ip")
            if master_ip and _worker_instance:
                _worker_instance.master_ip = master_ip
                _worker_instance.master_url = f"http://{master_ip}:{MASTER_PORT}"
                self.send_json({"success": True, "master_ip": master_ip})
            else:
                self.send_json({"success": False, "error": "Worker no iniciado o master_ip faltante"})

        elif path == "/stop":
            if _worker_instance:
                _worker_instance.stop()
            self.send_json({"success": True, "message": "Worker detenido"})

        else:
            self.send_json({"error": "Endpoint no encontrado"}, 404)


class ThreadedWorkerServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def start_worker(master_ip: str = "127.0.0.1", port: int = WORKER_PORT) -> threading.Thread:
    """
    Inicia el worker HTTP y el loop de polling en hilos de fondo.
    Retorna el hilo del loop de polling para que el llamador pueda esperar.
    """
    global _worker_instance, _worker_thread

    _worker_instance = DistributedWorker(master_ip=master_ip)

    # Hilo del servidor HTTP (para que el Maestro pueda detectar al worker)
    server = ThreadedWorkerServer(("", port), WorkerHTTPHandler)
    http_thread = threading.Thread(target=server.serve_forever, daemon=True, name="Worker-HTTP")
    http_thread.start()
    print(f"🌐 [Worker] Servidor HTTP escuchando en 0.0.0.0:{port}")

    # Hilo del polling al Maestro
    _worker_thread = threading.Thread(
        target=_worker_instance.run_polling_loop,
        daemon=True,
        name="Worker-Polling"
    )
    _worker_thread.start()
    return _worker_thread


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Worker de Carga Distribuida LAN — ASFI")
    parser.add_argument("--master-ip", "-m", type=str, default="127.0.0.1",
                        help="IP del servidor Maestro (default: 127.0.0.1)")
    parser.add_argument("--master-port", "-P", type=int, default=MASTER_PORT,
                        help=f"Puerto del maestro (default: {MASTER_PORT} = dashboard)")
    parser.add_argument("--port", "-p", type=int, default=WORKER_PORT,
                        help=f"Puerto del worker (default: {WORKER_PORT})")
    args = parser.parse_args()

    print(f"========================================================")
    print(f"🤖  WORKER DISTRIBUIDO ASFI")
    print(f"   Maestro: {args.master_ip}:{args.master_port}")
    print(f"   Mi puerto (deteccion LAN): {args.port}")
    print(f"========================================================\n")

    # Sobreescribir MASTER_PORT con el valor del argumento
    import distributed.worker_server as _ws
    _ws.MASTER_PORT = args.master_port

    worker_thread = start_worker(master_ip=args.master_ip, port=args.port)
    try:
        worker_thread.join()
    except KeyboardInterrupt:
        print("\n🛑 Worker detenido.")
        if _worker_instance:
            _worker_instance.stop()
