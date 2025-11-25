#!/usr/bin/env python3
"""
Script para verificar el orden de las fechas en el resumen
"""
from datetime import datetime
import csv

# Leer CSV
fechas = set()
with open('BBDD_partidos_completo.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        fecha = row.get('Fecha', '')
        if fecha:
            fechas.add(fecha)

# Ordenar fechas
def parse_date(date_str):
    try:
        return datetime.strptime(date_str, '%d %b %Y')
    except:
        return datetime.min

fechas_ordenadas = sorted(fechas, key=parse_date, reverse=True)

print("Fechas ordenadas (más reciente primero):")
print("=" * 50)
for fecha in fechas_ordenadas:
    print(f"  {fecha}")

print(f"\nTotal: {len(fechas_ordenadas)} fechas únicas")
