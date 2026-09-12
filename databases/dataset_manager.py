"""
Gestión del dataset CSV activo, borrado de BDs y rutas de upload.
"""

import os
import sqlite3
import json
from config import ASFI_DB_PATH, AUDIT_LOG_FILE

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPLOAD_DIR = os.path.join(ROOT_DIR, "uploads")
DEFAULT_CSV = os.path.join(ROOT_DIR, "01 - Practica 2 Dataset.csv")
ACTIVE_DATASET_FILE = os.path.join(UPLOAD_DIR, "active_dataset.json")

os.makedirs(UPLOAD_DIR, exist_ok=True)


def _read_active_meta():
    if os.path.exists(ACTIVE_DATASET_FILE):
        try:
            with open(ACTIVE_DATASET_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    path = DEFAULT_CSV if os.path.exists(DEFAULT_CSV) else None
    return {
        "path": path,
        "filename": os.path.basename(path) if path else None,
        "source": "default" if path else None,
    }


def get_active_dataset_path() -> str:
    meta = _read_active_meta()
    path = meta.get("path")
    if path and os.path.exists(path):
        return path
    if os.path.exists(DEFAULT_CSV):
        return DEFAULT_CSV
    return DEFAULT_CSV


def get_dataset_info() -> dict:
    path = get_active_dataset_path()
    meta = _read_active_meta()
    exists = os.path.exists(path) if path else False
    size = os.path.getsize(path) if exists else 0
    return {
        "path": path,
        "filename": os.path.basename(path) if path else None,
        "exists": exists,
        "size_bytes": size,
        "source": meta.get("source", "default"),
        "uploaded_at": meta.get("uploaded_at"),
    }


def set_active_dataset(path: str, source: str = "upload", uploaded_at: str = None) -> dict:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    meta = {
        "path": os.path.abspath(path),
        "filename": os.path.basename(path),
        "source": source,
        "uploaded_at": uploaded_at,
    }
    with open(ACTIVE_DATASET_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return get_dataset_info()


def save_uploaded_csv(filename: str, raw_bytes: bytes) -> dict:
    safe = os.path.basename(filename or "dataset.csv")
    if not safe.lower().endswith(".csv"):
        safe = safe + ".csv"
    dest = os.path.join(UPLOAD_DIR, safe)
    with open(dest, "wb") as f:
        f.write(raw_bytes)
    import time
    return set_active_dataset(dest, source="upload", uploaded_at=time.strftime("%Y-%m-%d %H:%M:%S"))


def wipe_all_databases(data_dir: str = "bank_data") -> dict:
    """Borra datos de ASFI + 14 bancos (archivos locales y esquemas de adaptadores)."""
    from databases.bank_dbs import bank_db_manager

    cleared = {"asfi": False, "audit_log": False, "bank_files": [], "adapters_reset": []}

    # ASFI central
    if os.path.exists(ASFI_DB_PATH):
        conn = sqlite3.connect(ASFI_DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM AuditLogs")
        cur.execute("DELETE FROM Cuentas")
        conn.commit()
        conn.close()
        cleared["asfi"] = True

    # Audit log file
    try:
        open(AUDIT_LOG_FILE, "w", encoding="utf-8").close()
        cleared["audit_log"] = True
    except Exception:
        pass

    # Reset stores (limpia tablas / JSON de los 14 bancos)
    bank_db_manager._init_bank_stores(reset=True)
    cleared["adapters_reset"] = list(range(1, 15))

    # Contar archivos en bank_data
    data_path = os.path.join(ROOT_DIR, data_dir) if not os.path.isabs(data_dir) else data_dir
    if os.path.isdir(data_path):
        cleared["bank_files"] = sorted(os.listdir(data_path))

    return {"success": True, **cleared, "message": "Bases de datos limpiadas. Listo para un nuevo seed."}
