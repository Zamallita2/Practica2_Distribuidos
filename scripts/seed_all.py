"""
Script to seed all 14 bank databases with encrypted balances from CSV with a configurable sampling percentage.
Usage:
    python3 scripts/seed_all.py                 (Default 1%)
    python3 scripts/seed_all.py --percent 2.0   (Custom 2%)
    python3 scripts/seed_all.py 5               (Custom 5%)
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from databases.seed_data import seed_bank_databases_from_csv

def main():
    parser = argparse.ArgumentParser(description="Poblador de BDs con Muestra Parametrizable")
    parser.add_argument("percent_pos", type=float, nargs="?", default=None, help="Porcentaje posicional (ej: 1, 2, 5)")
    parser.add_argument("--percent", "-p", type=float, default=None, help="Porcentaje (ej: --percent 1.0, --percent 2.5)")
    parser.add_argument("--file", "-f", type=str, default="01 - Practica 2 Dataset.csv", help="Ruta del archivo CSV")
    args = parser.parse_args()

    val = args.percent if args.percent is not None else (args.percent_pos if args.percent_pos is not None else 1.0)
    rate = val / 100.0 if val >= 1.0 else val
    if rate <= 0:
        rate = 0.01

    pct_display = val if val >= 1.0 else val * 100
    print("==================================================")
    print(f"🌱 POBLADOR DE DATOS BANCARIOS ({pct_display:.2f}% DEL DATASET CSV)")
    print("==================================================")
    seed_bank_databases_from_csv(args.file, rate)

if __name__ == "__main__":
    main()
