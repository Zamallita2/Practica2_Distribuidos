"""
ASFI Central Processing Engine & Master Orchestrator (Tarea 9)
Coordinación del flujo completo entre ASFI, BCB y los 14 bancos:
- Extracción de saldos cifrados.
- Descifrado de información con llaves criptográficas del banco.
- Conversión a bolivianos (Bs.) con cotización BCB en t₀.
- Generación de código verificador de 8 caracteres hexadecimales (0–9, A–F).
- Sincronización y actualización en la base del banco correspondiente.
- Registro en base central ASFI, tabla AuditLogs y archivo físico asfi_audit.log.
- Tolerancia a bancos desconectados o no disponibles.
"""

import secrets
import datetime
import os
import logging
from config import AUDIT_LOG_FILE, BANKS
from bcb_service.rate_engine import bcb_engine
from databases.seed_data import decrypt_balance
from databases.asfi_db import asfi_db
from databases.bank_dbs import bank_db_manager

# Configuración del logger de archivo para auditoría física
audit_logger = logging.getLogger("ASFIAudit")
audit_logger.setLevel(logging.INFO)
if not audit_logger.handlers:
    file_handler = logging.FileHandler(AUDIT_LOG_FILE, encoding="utf-8")
    formatter = logging.Formatter("[AUDIT LOG] %(asctime)s | Tasa: %(message)s")
    file_handler.setFormatter(formatter)
    audit_logger.addHandler(file_handler)

class ASFICentralProcessEngine:
    def generate_verification_code(self) -> str:
        """Genera un código alfanumérico hexadecimal único de 8 caracteres (0–9, A–F)."""
        return secrets.token_hex(4).upper()

    def process_bank_account_payload(self, bank_id: int, account_data: dict, exchange_rate: float = None, update_bank_db: bool = True):
        """
        Procesa una cuenta bancaria individual: descifrado, conversión, código hex,
        persistencia en ASFI DB, sincronización opcional con el banco y registro de auditoría.
        """
        if exchange_rate is None:
            exchange_rate = bcb_engine.get_current_rate()["current_rate"]

        cuenta_id = account_data["cuenta_id"]
        saldo_cifrado = account_data["saldo_usd_cifrado"]

        # 1. Descifrar saldo USD usando el algoritmo específico del banco
        try:
            saldo_usd = decrypt_balance(bank_id, saldo_cifrado)
        except Exception as e:
            raise ValueError(f"Error al descifrar cuenta {cuenta_id} de Banco {bank_id}: {str(e)}")

        # 2. Convertir a bolivianos (Bs.) con 4 decimales de precisión
        saldo_bs = round(saldo_usd * exchange_rate, 4)

        # 3. Generar Código de Verificación Hexadecimal de 8 caracteres
        verification_code = self.generate_verification_code()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 4. Registrar en Base de Datos Central ASFI y Tabla AuditLogs
        asfi_db.record_transaction(
            cuenta_id=cuenta_id,
            banco_id=bank_id,
            saldo_usd=saldo_usd,
            saldo_bs=saldo_bs,
            exchange_rate=exchange_rate,
            verification_code=verification_code,
            timestamp=timestamp
        )

        # 5. Escribir registro en archivo de auditoría física asfi_audit.log
        audit_log_msg = f"{exchange_rate:.4f} | CuentaId: {cuenta_id} | BancoId: {bank_id} | HexVerif: {verification_code}"
        audit_logger.info(audit_log_msg)

        # 6. Sincronizar y actualizar el saldo en la base de datos del banco correspondiente (si está activado)
        synced = False
        if update_bank_db:
            synced = bank_db_manager.update_verification_code(
                bank_id=bank_id,
                cuenta_id=cuenta_id,
                saldo_bs=saldo_bs,
                verification_code=verification_code,
                timestamp=timestamp
            )

        return {
            "cuenta_id": cuenta_id,
            "banco_id": bank_id,
            "saldo_usd": saldo_usd,
            "saldo_bs": saldo_bs,
            "tipo_cambio": exchange_rate,
            "codigo_verificacion": verification_code,
            "timestamp": timestamp,
            "banco_sincronizado": synced
        }

    def run_full_orchestration_cycle(self):
        """
        Coordinación del flujo completo entre ASFI, BCB y los 14 bancos (Tarea 9).
        Ejecuta el barrido paralelo, procesa transacciones y valida consistencia.
        """
        from asfi_central.sweeper import sweeper

        # Obtener cotización oficial del BCB
        rate_info = bcb_engine.get_current_rate()
        current_rate = rate_info["current_rate"]

        # Ejecutar barrido paralelo asíncrono
        import asyncio
        sweep_result = asyncio.run(sweeper.execute_parallel_sweep())

        # Validar consistencia entre la base central ASFI y las bases bancarias
        asfi_accounts = asfi_db.get_all_accounts()
        verified_count = 0
        inconsistencies = 0

        for row in asfi_accounts:
            cuenta_id, banco_id, saldo_usd, saldo_bs_asfi, fecha, code_asfi = row
            bank_accounts = bank_db_manager.get_encrypted_accounts(banco_id)
            bank_acc = next((a for a in bank_accounts if a["cuenta_id"] == cuenta_id), None)

            if not bank_acc:
                inconsistencies += 1
                continue

            code_bank = bank_acc.get("codigo_verificacion", "")
            saldo_bs_bank = bank_acc.get("saldo_bs", 0.0)

            if code_asfi == code_bank and round(saldo_bs_asfi, 2) == round(saldo_bs_bank, 2):
                verified_count += 1
            else:
                inconsistencies += 1

        return {
            "rate_info": rate_info,
            "sweep_result": sweep_result,
            "total_asfi_accounts": len(asfi_accounts),
            "verified_consistent": verified_count,
            "inconsistencies": inconsistencies
        }

asfi_process_engine = ASFICentralProcessEngine()

