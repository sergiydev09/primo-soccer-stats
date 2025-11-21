#!/usr/bin/env python3
"""Test de extracción con un solo partido"""

import sys
# Importar el módulo principal
from extract_match_data_v2 import setup_driver, extract_match_data, save_to_csv

def main():
    # Leer primera URL
    with open('match_urls.txt', 'r') as f:
        first_url = f.readline().strip()

    print("Probando extracción con un partido...\n")
    driver = setup_driver()

    try:
        data = extract_match_data(driver, first_url, 1)

        if data:
            print(f"\n{'='*80}")
            print("DATOS EXTRAÍDOS:")
            print(f"{'='*80}\n")
            print(f"Total de registros: {len(data)}\n")
            print("Primer registro:")
            for key, value in list(data[0].items())[:15]:
                print(f"  {key}: {value}")

            # Guardar en CSV de prueba
            save_to_csv(data, 'test_match_data.csv')
            print("\n✓ Prueba exitosa!")
        else:
            print("\n✗ No se extrajeron datos")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
