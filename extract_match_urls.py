#!/usr/bin/env python3
"""
Script para extraer todas las URLs de partidos de Opta Player Stats
Primera División 2025-2026
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import re

def extract_match_urls():
    """Extrae todas las URLs de partidos de la página de Opta Player Stats"""

    # URL base
    base_url = "https://optaplayerstats.statsperform.com/en_GB/soccer/primera-divisi%C3%B3n-2025-2026/80zg2v1cuqcfhphn56u4qpyqc/opta-player-stats"

    # Configurar opciones de Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Ejecutar sin ventana visible
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    print("Iniciando navegador...")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Cargar la página
        print(f"Cargando página: {base_url}")
        driver.get(base_url)

        # Esperar a que la página cargue
        print("Esperando a que cargue el contenido...")
        time.sleep(3)

        # Hacer scroll para cargar contenido dinámico
        print("Haciendo scroll para cargar todo el contenido...")
        last_height = driver.execute_script("return document.body.scrollHeight")

        for _ in range(5):  # Hacer scroll varias veces
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # Volver arriba
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        # Guardar el HTML para debug
        print("Guardando HTML de la página...")
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        # Buscar todos los enlaces en la página
        all_links = driver.find_elements(By.TAG_NAME, "a")
        print(f"Total de enlaces encontrados en la página: {len(all_links)}")

        # Filtrar URLs que contienen '/match/view/'
        match_urls = set()
        pattern = re.compile(r'/match/view/[a-z0-9]+')

        for link in all_links:
            href = link.get_attribute("href")
            if href:
                # Debug: imprimir algunos enlaces para ver qué estamos obteniendo
                if len(match_urls) < 3 and '/match/' in href:
                    print(f"Ejemplo de enlace encontrado: {href}")

                if pattern.search(href):
                    match_urls.add(href)

        # Ordenar URLs
        match_urls = sorted(list(match_urls))

        # Imprimir resultados
        print(f"\n{'='*80}")
        print(f"Se encontraron {len(match_urls)} URLs de partidos:")
        print(f"{'='*80}\n")

        for i, url in enumerate(match_urls, 1):
            print(f"{i}. {url}")

        # Guardar en archivo
        output_file = "match_urls.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            for url in match_urls:
                f.write(url + '\n')

        print(f"\n{'='*80}")
        print(f"URLs guardadas en: {output_file}")
        print(f"{'='*80}")

        return match_urls

    except Exception as e:
        print(f"Error: {e}")
        return []

    finally:
        driver.quit()
        print("\nNavegador cerrado.")

if __name__ == "__main__":
    extract_match_urls()
