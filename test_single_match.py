#!/usr/bin/env python3
"""
Script de prueba para analizar la estructura de una página de partido
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def setup_driver():
    """Configura y retorna el driver de Chrome"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    return webdriver.Chrome(options=chrome_options)

def analyze_page_structure(url):
    """Analiza la estructura de una página de partido"""

    driver = setup_driver()

    try:
        print(f"Cargando: {url}\n")
        driver.get(url)
        time.sleep(5)

        # Guardar el HTML para inspección
        with open("match_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("✓ HTML guardado en: match_page.html\n")

        # Buscar información visible en la página
        print("="*80)
        print("ANÁLISIS DE ESTRUCTURA")
        print("="*80)

        # Buscar título
        try:
            title = driver.find_element(By.TAG_NAME, "h1")
            print(f"\nTítulo: {title.text}")
        except:
            print("\nTítulo: No encontrado")

        # Buscar todos los h2, h3
        headers = driver.find_elements(By.CSS_SELECTOR, "h2, h3, h4")
        if headers:
            print(f"\nEncabezados encontrados ({len(headers)}):")
            for h in headers[:10]:  # Mostrar primeros 10
                if h.text.strip():
                    print(f"  - {h.text.strip()}")

        # Buscar tablas
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"\nTablas encontradas: {len(tables)}")

        for i, table in enumerate(tables[:3], 1):  # Analizar primeras 3 tablas
            print(f"\n--- Tabla {i} ---")
            rows = table.find_elements(By.TAG_NAME, "tr")
            print(f"Filas: {len(rows)}")

            if rows:
                # Mostrar primera fila (header)
                first_row = rows[0]
                headers = first_row.find_elements(By.TAG_NAME, "th")
                if not headers:
                    headers = first_row.find_elements(By.TAG_NAME, "td")

                if headers:
                    print("Columnas:")
                    for h in headers[:10]:  # Primeras 10 columnas
                        print(f"  - {h.text.strip()}")

                # Mostrar una fila de datos
                if len(rows) > 1:
                    data_row = rows[1]
                    cells = data_row.find_elements(By.TAG_NAME, "td")
                    if cells:
                        print("\nEjemplo de datos (primera fila):")
                        for j, cell in enumerate(cells[:10], 1):
                            print(f"  Col {j}: {cell.text.strip()}")

        # Buscar enlaces/pestañas
        links = driver.find_elements(By.TAG_NAME, "a")
        print(f"\n\nEnlaces encontrados: {len(links)}")
        stat_links = [link for link in links if 'stat' in link.text.lower() or 'player' in link.text.lower()]
        if stat_links:
            print("Enlaces relacionados con estadísticas:")
            for link in stat_links[:5]:
                print(f"  - {link.text.strip()}")

        print("\n" + "="*80)

    finally:
        driver.quit()

if __name__ == "__main__":
    # Usar la primera URL del archivo
    with open('match_urls.txt', 'r') as f:
        first_url = f.readline().strip()

    analyze_page_structure(first_url)
