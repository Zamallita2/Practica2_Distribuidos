"""
Servidor Maestro de Carga Distribuida LAN (ASFI Sistema Bancario)
=================================================================
Divide el CSV del dataset en mini-CSVs por banco y distribuye la carga
entre workers detectados en la red local. Siempre se incluye a sí mismo
como worker (modo single-node también funciona).

Endpoints:
  GET  /status         → Estado del maestro, workers, progreso
  POST /start          → Inicia escaneo LAN y distribución del CSV
  GET  /task           → Un worker solicita su tarea (mini-CSV)
  POST /done           → Un worker reporta que terminó
  POST /stop           → Detiene la sesión distribuida actual

Uso:
  # Como módulo independiente en background:
  python -m distributed.master_server

  # Como librería desde web_server.py:
  from distributed.master_server import distributed_master
  distributed_master.start_distribution(csv_path, sample_rate)
"""

import os
import sys
import csv
import io
import json
import time
import socket
import base64
import threading
import http.server
import socketserver
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

MASTER_PORT = 9000
WORKER_PORT = 9001
SCAN_TIMEOUT = 0.4       # segundos por IP al escanear
SCAN_SUBNET_MAX = 255    # últimos 3 octetos a probar
TASK_TIMEOUT = 300       # segundos max que puede tardar un worker


class DistributedTask:
    """Representa una tarea asignada a un worker (un sub-CSV de un banco)."""
    def __init__(self, task_id: str, bank_ids: list, csv_b64: str, row_count: int):
        self.task_id = task_id
        self.bank_ids = bank_ids          # lista de bank_ids incluidos en este mini-CSV
        self.csv_b64 = csv_b64            # CSV codificado en Base64
        self.row_count = row_count
        self.assigned_worker = None       # IP del worker que la tomó
        self.status = "pending"           # pending | running | done | error
        self.result = None
        self.started_at = None
        self.finished_at = None


class DistributedMasterSession:
    """
    Gestiona una sesión de distribución completa:
    escaneo, asignación de tareas y recolección de resultados.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self.session_id = None
        self.tasks: dict[str, DistributedTask] = {}
        self.workers: list[str] = []          # IPs de workers disponibles
        self.status = "idle"                  # idle | scanning | distributing | done | error
        self.started_at = None
        self.finished_at = None
        self.error = None
        self.total_inserted = 0
        self.total_errors = 0
        self._task_queue: list[str] = []      # task_ids pendientes en cola FIFO

    # ------------------------------------------------------------------ #
    # Descubrimiento de workers en la LAN                                 #
    # ------------------------------------------------------------------ #
    def _check_worker(self, ip: str) -> bool:
        """Comprueba si hay un worker escuchando en ip:WORKER_PORT."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(SCAN_TIMEOUT)
            result = s.connect_ex((ip, WORKER_PORT))
            s.close()
            return result == 0
        except Exception:
            return False

    def _get_local_ips(self) -> list:
        """Retorna las IPs base de todas las interfaces de red activas."""
        subnets = set()
        try:
            hostname = socket.gethostname()
            ips = socket.getaddrinfo(hostname, None)
            for info in ips:
                ip = info[4][0]
                if ip.startswith("127.") or ":" in ip:
                    continue
                parts = ip.split(".")
                if len(parts) == 4:
                    subnets.add(".".join(parts[:3]))
        except Exception:
            pass
        # Fallback: intentar conexión UDP para detectar IP de salida
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                parts = ip.split(".")
                if len(parts) == 4:
                    subnets.add(".".join(parts[:3]))
        except Exception:
            pass
        return list(subnets) or ["192.168.1"]

    def scan_lan_for_workers(self, include_self: bool = True) -> list:
        """
        Escanea la subred local buscando workers en el puerto WORKER_PORT.
        Incluye siempre la IP local (127.0.0.1) si include_self=True.
        """
        with self._lock:
            self.status = "scanning"

        found = []
        subnets = self._get_local_ips()
        candidates = []
        for subnet in subnets:
            for i in range(1, SCAN_SUBNET_MAX + 1):
                candidates.append(f"{subnet}.{i}")

        print(f"🔍 [Maestro] Escaneando {len(candidates)} IPs en {len(subnets)} subredes (puerto {WORKER_PORT})...")

        with ThreadPoolExecutor(max_workers=64) as pool:
            futures = {pool.submit(self._check_worker, ip): ip for ip in candidates}
            for fut in as_completed(futures):
                ip = futures[fut]
                try:
                    if fut.result():
                        found.append(ip)
                        print(f"   ✅ Worker encontrado: {ip}:{WORKER_PORT}")
                except Exception:
                    pass

        if include_self:
            self_ip = "127.0.0.1"
            if self_ip not in found:
                found.insert(0, self_ip)
                print(f"   🏠 Nodo local incluido: {self_ip}:{WORKER_PORT}")

        with self._lock:
            self.workers = found

        print(f"📡 [Maestro] Workers disponibles: {len(found)}")
        return found

    # ------------------------------------------------------------------ #
    # División del CSV en mini-CSVs por banco                             #
    # ------------------------------------------------------------------ #
    @staticmethod
    def split_csv_by_bank(csv_path: str, sample_rate: float = 1.0) -> dict[int, tuple[str, int]]:
        """
        Lee el CSV completo y lo divide en mini-CSVs por banco.
        Retorna un dict: bank_id -> (csv_content_string, row_count)
        """
        import math
        from databases.seed_data import iter_dataset_rows, validate_account_record

        bank_rows: dict[int, list[dict]] = defaultdict(list)
        header_fields = None

        for row in iter_dataset_rows(csv_path):
            if header_fields is None:
                header_fields = list(row.keys())
            is_valid, _ = validate_account_record(row)
            if not is_valid:
                continue
            b_id = int(float(row["IdBanco"]))
            bank_rows[b_id].append(row)

        if not header_fields:
            return {}

        result = {}
        for b_id, rows in bank_rows.items():
            n = len(rows) if sample_rate >= 1.0 else max(1, math.ceil(len(rows) * sample_rate))
            sampled = rows[:n]
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=header_fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(sampled)
            result[b_id] = (buf.getvalue(), len(sampled))

        return result

    # ------------------------------------------------------------------ #
    # Distribución de tareas                                              #
    # ------------------------------------------------------------------ #
    def start_distribution(self, csv_path: str, sample_rate: float = 1.0, scan_lan: bool = True):
        """
        Punto de entrada principal: escanea LAN (opcional), divide el CSV
        y encola las tareas. Los workers las irán pidiendo con GET /task.
        """
        import uuid
        with self._lock:
            self.session_id = str(uuid.uuid4())[:8]
            self.tasks = {}
            self._task_queue = []
            self.total_inserted = 0
            self.total_errors = 0
            self.error = None
            self.started_at = time.time()
            self.finished_at = None
            self.status = "distributing"

        if scan_lan:
            self.scan_lan_for_workers()
        elif not self.workers:
            with self._lock:
                self.workers = ["127.0.0.1"]

        print(f"\n📦 [Maestro] Dividiendo CSV '{csv_path}' por banco (rate={sample_rate:.2%})...")
        bank_csvs = self.split_csv_by_bank(csv_path, sample_rate)

        if not bank_csvs:
            with self._lock:
                self.status = "error"
                self.error = "CSV vacío o sin filas válidas"
            return {"success": False, "error": self.error}

        # Agrupar bancos entre los workers disponibles (round-robin por cantidad de filas)
        workers_list = list(self.workers)
        n_workers = len(workers_list)
        # Ordenar bancos de mayor a menor para balancear mejor
        sorted_banks = sorted(bank_csvs.keys(), key=lambda b: bank_csvs[b][1], reverse=True)

        # Asignar cada banco a un worker (round-robin)
        worker_assignments: dict[str, list[int]] = {w: [] for w in workers_list}
        for i, b_id in enumerate(sorted_banks):
            worker_ip = workers_list[i % n_workers]
            worker_assignments[worker_ip].append(b_id)

        tasks_created = []
        import uuid
        for worker_ip, bank_ids in worker_assignments.items():
            if not bank_ids:
                continue
            # Combinar los mini-CSVs de los bancos asignados a este worker
            combined_rows = []
            combined_header = None
            for b_id in bank_ids:
                csv_str, _ = bank_csvs[b_id]
                reader = csv.DictReader(io.StringIO(csv_str))
                if combined_header is None:
                    combined_header = reader.fieldnames
                for row in reader:
                    combined_rows.append(row)

            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=combined_header, lineterminator="\n")
            writer.writeheader()
            writer.writerows(combined_rows)
            combined_csv = buf.getvalue()
            csv_b64 = base64.b64encode(combined_csv.encode("utf-8")).decode("ascii")

            task_id = f"task-{str(uuid.uuid4())[:8]}"
            task = DistributedTask(
                task_id=task_id,
                bank_ids=bank_ids,
                csv_b64=csv_b64,
                row_count=len(combined_rows),
            )
            task.assigned_worker = worker_ip
            tasks_created.append(task)

            with self._lock:
                self.tasks[task_id] = task
                self._task_queue.append(task_id)

            print(f"   📋 Tarea {task_id} → Worker {worker_ip} | Bancos {bank_ids} | {len(combined_rows)} filas")

        print(f"\n✅ [Maestro] {len(tasks_created)} tareas creadas para {n_workers} workers\n")
        return {
            "success": True,
            "session_id": self.session_id,
            "workers": workers_list,
            "tasks": len(tasks_created),
            "total_rows": sum(t.row_count for t in tasks_created),
        }

    # ------------------------------------------------------------------ #
    # API para workers: obtener y reportar tareas                         #
    # ------------------------------------------------------------------ #
    def get_next_task_for_worker(self, worker_ip: str) -> dict | None:
        """Un worker solicita su tarea. Retorna la tarea asignada a ese worker, si está pendiente."""
        with self._lock:
            for task_id in list(self._task_queue):
                task = self.tasks.get(task_id)
                if task and task.status == "pending" and (
                    task.assigned_worker is None or task.assigned_worker == worker_ip
                ):
                    task.status = "running"
                    task.started_at = time.time()
                    self._task_queue.remove(task_id)
                    return {
                        "task_id": task.task_id,
                        "bank_ids": task.bank_ids,
                        "csv_b64": task.csv_b64,
                        "row_count": task.row_count,
                        "sample_rate": 1.0,   # ya fue filtrado al crear la tarea
                    }
        return None

    def report_task_done(self, task_id: str, result: dict):
        """Un worker reporta que terminó su tarea."""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            task.status = "done" if result.get("success") else "error"
            task.result = result
            task.finished_at = time.time()
            self.total_inserted += result.get("total_inserted", 0)
            self.total_errors += result.get("insert_errors", 0)
            # Verificar si todas las tareas terminaron
            pending = [t for t in self.tasks.values() if t.status in ("pending", "running")]
            if not pending:
                self.status = "done"
                self.finished_at = time.time()
            return True

    def get_status(self) -> dict:
        with self._lock:
            tasks_summary = []
            for t in self.tasks.values():
                elapsed = None
                if t.started_at:
                    end = t.finished_at or time.time()
                    elapsed = round(end - t.started_at, 2)
                tasks_summary.append({
                    "task_id": t.task_id,
                    "bank_ids": t.bank_ids,
                    "worker": t.assigned_worker,
                    "status": t.status,
                    "row_count": t.row_count,
                    "inserted": t.result.get("total_inserted", 0) if t.result else 0,
                    "errors": t.result.get("insert_errors", 0) if t.result else 0,
                    "elapsed_seconds": elapsed,
                })
            elapsed_total = None
            if self.started_at:
                end = self.finished_at or time.time()
                elapsed_total = round(end - self.started_at, 2)
            return {
                "session_id": self.session_id,
                "status": self.status,
                "workers": self.workers,
                "tasks": tasks_summary,
                "total_inserted": self.total_inserted,
                "total_errors": self.total_errors,
                "elapsed_seconds": elapsed_total,
                "error": self.error,
            }


# Instancia global del maestro
distributed_master = DistributedMasterSession()


# ------------------------------------------------------------------ #
# Servidor HTTP del Maestro (opcional, para uso standalone)           #
# ------------------------------------------------------------------ #
class MasterHTTPHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # Silenciar logs por defecto

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
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/status":
            self.send_json(distributed_master.get_status())

        elif path == "/task":
            worker_ip = self.client_address[0]
            task = distributed_master.get_next_task_for_worker(worker_ip)
            if task:
                self.send_json({"has_task": True, **task})
            else:
                self.send_json({"has_task": False})

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

        if path == "/start":
            csv_path = payload.get("csv_path", "01 - Practica 2 Dataset.csv")
            sample_rate = float(payload.get("sample_rate", 1.0))
            scan_lan = bool(payload.get("scan_lan", True))
            # Correr en background para no bloquear la respuesta HTTP
            def _bg():
                distributed_master.start_distribution(csv_path, sample_rate, scan_lan)
            threading.Thread(target=_bg, daemon=True).start()
            self.send_json({"success": True, "message": "Distribución iniciada en background"})

        elif path == "/done":
            task_id = payload.get("task_id")
            result = payload.get("result", {})
            ok = distributed_master.report_task_done(task_id, result)
            self.send_json({"success": ok})

        elif path == "/stop":
            with distributed_master._lock:
                distributed_master.status = "idle"
                distributed_master.tasks = {}
                distributed_master._task_queue = []
            self.send_json({"success": True, "message": "Sesión distribuida detenida"})

        else:
            self.send_json({"error": "Endpoint no encontrado"}, 404)


class ThreadedMasterServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def run_master_server(port=MASTER_PORT):
    server = ThreadedMasterServer(("", port), MasterHTTPHandler)
    print(f"🌐 [Maestro] Servidor distribuido escuchando en 0.0.0.0:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    run_master_server()
