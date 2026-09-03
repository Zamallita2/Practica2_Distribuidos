"""
Master Execution Script for ASFI Distributed Monetary Conversion Platform.
Performs 1% stratified data seeding check from 01 - Practica 2 Dataset.csv, BCB rate fetch, ASFI parallel sweep, data validation, and audit display.
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from databases.seed_data import seed_bank_databases_from_csv
from asfi_central.sweeper import sweeper
from databases.asfi_db import asfi_db
from databases.bank_dbs import bank_db_manager
from bcb_service.rate_engine import bcb_engine

async def run_full_simulation():
    print("=========================================================================")
    print("🏛️   PLATAFORMA DISTRIBUIDA DE CONVERSIÓN MONETARIA (ASFI - BCB)")
    print("=========================================================================\n")

    # 1. Asegurar que las 14 BDs estén pobladas con el 1% del CSV
    print("📌 1. Poblando las 14 Bases de Datos Bancarias con el 1% equitativo del CSV...")
    seed_bank_databases_from_csv("01 - Practica 2 Dataset.csv", 0.01)

    # 2. Consultar cotización del BCB
    print("\n📌 2. Consultando cotización en el Banco Central de Bolivia (BCB)...")
    rate_info = bcb_engine.get_current_rate()
    print(f"   - Cotización Actual: {rate_info['current_rate']} BOB/USD")
    print(f"   - Próxima fluctuación en: {rate_info['seconds_until_next_change']} segundos")

    # 3. Ejecutar Barrido Paralelo ASFI
    print("\n📌 3. Ejecutando Barrido Paralelo ASFI en los 14 Bancos...")
    res = await sweeper.execute_parallel_sweep()

    # 4. Validar Consistencia ASFI vs Bancos
    print("📌 4. Validando consistencia entre la Base Central ASFI y los 14 Bancos...")
    asfi_accounts = asfi_db.get_all_accounts()
    inconsistencies = 0

    for row in asfi_accounts:
        cuenta_id, banco_id, saldo_usd, saldo_bs_asfi, fecha, code_asfi = row
        bank_accounts = bank_db_manager.get_encrypted_accounts(banco_id)
        bank_acc = next((a for a in bank_accounts if a["cuenta_id"] == cuenta_id), None)
        
        if not bank_acc:
            print(f"❌ Error: Cuenta {cuenta_id} no encontrada en Banco {banco_id}")
            inconsistencies += 1
            continue

        code_bank = bank_acc.get("codigo_verificacion", "")
        saldo_bs_bank = bank_acc.get("saldo_bs", 0.0)

        if code_asfi != code_bank or round(saldo_bs_asfi, 2) != round(saldo_bs_bank, 2):
            print(f"⚠️ Inconsistencia en Cuenta {cuenta_id}: ASFI(Bs={saldo_bs_asfi}, Hex={code_asfi}) vs BANCO(Bs={saldo_bs_bank}, Hex={code_bank})")
            inconsistencies += 1

    if inconsistencies == 0:
        print(f"✅ ¡CONSISTENCIA PERFECTA VALIDADA! {len(asfi_accounts)} cuentas verificadas en 14 bancos.")
    else:
        print(f"⚠️ Se encontraron {inconsistencies} inconsistencias.")

    # 5. Resumen de Auditoría
    print("\n📌 5. Muestra de Registros de Auditoría ASFI (AuditLogs):")
    audit_rows = asfi_db.get_audit_logs()[:5]
    for log in audit_rows:
        print(f"   [LOG #{log[0]}] {log[1]} | TipoCambio={log[2]} | Cuenta={log[3]} | Banco={log[4]}")

    print("\n=========================================================================")
    print("✨  SIMULACIÓN FINALIZADA CON ÉXITO")
    print("=========================================================================\n")

if __name__ == "__main__":
    asyncio.run(run_full_simulation())
