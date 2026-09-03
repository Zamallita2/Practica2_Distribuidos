"""
Script to test loading 01 - Practica 2 Dataset.csv and sampling 1% stratifying by IdBanco.
"""

import csv
from collections import defaultdict
import math

def inspect_and_sample_csv(csv_path: str = "01 - Practica 2 Dataset.csv", sample_rate: float = 0.01):
    bank_rows = defaultdict(list)
    
    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                b_id = int(row["IdBanco"])
                bank_rows[b_id].append(row)
            except (ValueError, KeyError):
                continue

    print(f"📊 Resumen del Dataset Total ({csv_path}):")
    total_all = 0
    total_sampled = 0
    sampled_records = []

    for b_id in sorted(bank_rows.keys()):
        rows = bank_rows[b_id]
        total_b = len(rows)
        # Muestra del 1% (mínimo 1 registro)
        sample_n = max(1, math.ceil(total_b * sample_rate))
        sampled_b = rows[:sample_n]
        
        total_all += total_b
        total_sampled += len(sampled_b)
        sampled_records.extend(sampled_b)
        print(f"   - Banco #{b_id:2d}: {total_b:6d} cuentas totales -> 1% muestra: {len(sampled_b):4d} cuentas")

    print(f"\n✅ Total Cuentas CSV: {total_all}")
    print(f"🎯 Total Muestra 1% Equitativa: {total_sampled} cuentas")
    return sampled_records

if __name__ == "__main__":
    inspect_and_sample_csv()
