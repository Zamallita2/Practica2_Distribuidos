"""
Generate sample dataset (CSV or Excel) for 14 banks with representative accounts if no input dataset file is provided.
"""

import random
import os
import csv

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

def generate_sample_excel(output_path: str = "cuentas_bancarias_muestra.csv", records_per_bank: int = 20):
    nombres = [
        "Juan Pérez", "Maria Rodriguez", "Carlos Mamani", "Ana Quispe", "Luis Flores",
        "Sofia Vargas", "Diego Morales", "Elena Gutierres", "Gabriel Mendoza", "Lucia Guzman",
        "Mateo Cabrera", "Camila Fernandez", "Hugo Torrez", "Valeria Choque", "Fernando Silva"
    ]
    
    data = []
    account_counter = 10001
    
    for bank_id in range(1, 15):
        for _ in range(records_per_bank):
            data.append({
                "CuentaId": account_counter,
                "BancoId": bank_id,
                "ClienteNombre": random.choice(nombres),
                "SaldoUSD": round(random.uniform(500.0, 50000.0), 2)
            })
            account_counter += 1

    if output_path.endswith('.xlsx') and HAS_PANDAS:
        df = pd.DataFrame(data)
        df.to_excel(output_path, index=False)
    else:
        # Fallback a CSV
        output_path = output_path.replace('.xlsx', '.csv')
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["CuentaId", "BancoId", "ClienteNombre", "SaldoUSD"])
            writer.writeheader()
            writer.writerows(data)

    print(f"✅ Dataset de muestra generado exitosamente en: {output_path} ({len(data)} registros)")
    return output_path

if __name__ == "__main__":
    generate_sample_excel()

