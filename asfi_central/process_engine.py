"""
ASFI Central Processing Engine.
Handles decryption, currency conversion, 8-char hex verification code generation, audit logging, and ASFI DB persistence.
"""

import secrets
import datetime
from bcb_service.rate_engine import bcb_engine
from databases.seed_data import decrypt_balance
from databases.asfi_db import asfi_db
from databases.bank_dbs import bank_db_manager

class ASFICentralProcessEngine:
    def generate_verification_code(self) -> str:
        """Genera código alfanumérico hexadecimal de 8 caracteres (0–9, A–F)."""
        return secrets.token_hex(4).upper()

    def process_bank_account_payload(self, bank_id: int, account_data: dict, exchange_rate: float = None):
        if exchange_rate is None:
            exchange_rate = bcb_engine.get_current_rate()["current_rate"]

        cuenta_id = account_data["cuenta_id"]
        saldo_cifrado = account_data["saldo_usd_cifrado"]

        # 1. Desencriptar el saldo utilizando la llave del banco
        saldo_usd = decrypt_balance(bank_id, saldo_cifrado)

        # 2. Convertir a bolivianos (Bs.) con el tipo de cambio del BCB
        saldo_bs = round(saldo_usd * exchange_rate, 4)

        # 3. Generar Código de Verificación Hexadecimal de 8 caracteres
        verification_code = self.generate_verification_code()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 4. Registrar en la Base de Datos Central de la ASFI y Log de Auditoría
        asfi_db.record_transaction(
            cuenta_id=cuenta_id,
            banco_id=bank_id,
            saldo_usd=saldo_usd,
            saldo_bs=saldo_bs,
            exchange_rate=exchange_rate,
            verification_code=verification_code,
            timestamp=timestamp
        )

        # 5. Sincronizar y actualizar el saldo en la base de datos del banco correspondiente
        bank_db_manager.update_verification_code(
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
            "timestamp": timestamp
        }

asfi_process_engine = ASFICentralProcessEngine()
