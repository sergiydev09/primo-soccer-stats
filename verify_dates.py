#!/usr/bin/env python3
"""
Script para verificar el orden de las fechas de una BBDD generada
Uso: python3 verify_dates.py [--league <liga>] [--season <YYYY-YYYY>]
"""
import argparse
import csv
import sys
from datetime import datetime

from scraper import ALL_LEAGUES, LEAGUES, current_season, normalize_season

parser = argparse.ArgumentParser(description='Verifica las fechas de una BBDD de partidos')
parser.add_argument('--league', type=str, default='spain', choices=ALL_LEAGUES,
                    help='Liga/Competición a verificar')
parser.add_argument('--season', type=normalize_season, default=None,
                    help=f'Temporada, p.ej. 2026-2027 (por defecto la temporada en curso: {current_season()})')
args = parser.parse_args()

season = args.season or current_season()
filename = f"BBDD_partidos_{args.league}_{season}.csv"

# Leer CSV
fechas = set()
try:
    with open(filename, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fecha = row.get('Fecha', '')
            if fecha:
                fechas.add(fecha)
except FileNotFoundError:
    sys.exit(f"❌ Archivo {filename} no encontrado.\n"
             f"   Genéralo con: python3 scraper.py all --league {args.league} --season {season}")

# Ordenar fechas
def parse_date(date_str):
    try:
        return datetime.strptime(date_str, '%d %b %Y')
    except ValueError:
        return datetime.min

fechas_ordenadas = sorted(fechas, key=parse_date, reverse=True)

print(f"{LEAGUES[args.league]['name']} {season} — fechas ordenadas (más reciente primero):")
print("=" * 50)
for fecha in fechas_ordenadas:
    print(f"  {fecha}")

print(f"\nTotal: {len(fechas_ordenadas)} fechas únicas")
