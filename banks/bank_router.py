"""
Bank Microservices API Routes.
Exposes encrypted account data and accepts ASFI verification codes for syncing.
"""

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
from databases.bank_dbs import bank_db_manager
from config import BANKS

router = APIRouter(prefix="/api/bank", tags=["Bancos"])

class VerificationPayload(BaseModel):
    cuenta_id: int
    saldo_bs: float
    codigo_verificacion: str
    fecha_conversion: str

@router.get("/{bank_id}/accounts")
def get_bank_accounts(bank_id: int = Path(..., ge=1, le=14)):
    b_info = next((b for b in BANKS if b["id"] == bank_id), None)
    if not b_info:
        raise HTTPException(status_code=404, detail="Banco no encontrado")

    accounts = bank_db_manager.get_encrypted_accounts(bank_id)
    return {
        "banco_id": bank_id,
        "banco_nombre": b_info["name"],
        "algoritmo": b_info["algorithm"],
        "db_engine": b_info["db_engine"],
        "total_cuentas": len(accounts),
        "cuentas": accounts
    }

@router.post("/{bank_id}/verify")
def verify_and_update_bank_account(payload: VerificationPayload, bank_id: int = Path(..., ge=1, le=14)):
    success = bank_db_manager.update_verification_code(
        bank_id=bank_id,
        cuenta_id=payload.cuenta_id,
        saldo_bs=payload.saldo_bs,
        verification_code=payload.codigo_verificacion,
        timestamp=payload.fecha_conversion
    )
    if not success:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada en el banco especificado")
    
    return {
        "status": "success",
        "message": f"Cuenta {payload.cuenta_id} actualizada en {bank_id} con código de verificación {payload.codigo_verificacion}"
    }
