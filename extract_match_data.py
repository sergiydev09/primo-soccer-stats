#!/usr/bin/env python3
"""
Script para extraer datos de árbitros y jugadores de cada partido
y generar un CSV con toda la información
"""

import time
import csv
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def setup_driver():
    """Configura y retorna el driver de Chrome"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    return driver

def extract_match_id(url):
    """Extrae el ID del partido de la URL"""
    match = re.search(r'/match/view/([a-z0-9]+)', url)
    return match.group(1) if match else ""

def extract_match_data(driver, url, match_number):
    """Extrae todos los datos de un partido"""

    try:
        print(f"\n[{match_number}] Cargando: {url}")
        driver.get(url)

        # Esperar a que la página cargue
        time.sleep(3)

        match_id = extract_match_id(url)

        # Extraer información del partido
        match_info = {
            'id': match_id,
            'arbitro': '',
            'equipo_local': '',
            'equipo_visitante': '',
            'jornada': ''
        }

        # Intentar obtener el árbitro
        try:
            # Buscar el árbitro en diferentes posibles ubicaciones
            referee_element = driver.find_element(By.XPATH, "//div[contains(text(), 'Referee') or contains(text(), 'Árbitro')]")
            match_info['arbitro'] = referee_element.text.replace('Referee:', '').replace('Árbitro:', '').strip()
        except:
            try:
                # Método alternativo
                referee_element = driver.find_element(By.CSS_SELECTOR, ".referee, .match-official")
                match_info['arbitro'] = referee_element.text.strip()
            except:
                print(f"  ⚠️  No se pudo extraer árbitro")

        # Extraer nombres de equipos
        try:
            teams = driver.find_elements(By.CSS_SELECTOR, ".team-name, .match-team-name")
            if len(teams) >= 2:
                match_info['equipo_local'] = teams[0].text.strip()
                match_info['equipo_visitante'] = teams[1].text.strip()
        except:
            print(f"  ⚠️  No se pudieron extraer nombres de equipos")

        # Extraer jornada
        try:
            matchweek = driver.find_element(By.XPATH, "//span[contains(text(), 'Matchweek') or contains(text(), 'Jornada')]")
            match_info['jornada'] = re.search(r'\d+', matchweek.text).group()
        except:
            print(f"  ⚠️  No se pudo extraer jornada")

        # Extraer datos de jugadores
        players_data = []

        # Buscar tablas de estadísticas de jugadores
        try:
            # Hacer clic en la pestaña de estadísticas si existe
            stats_tabs = driver.find_elements(By.XPATH, "//a[contains(text(), 'Statistics') or contains(text(), 'Stats') or contains(text(), 'Estadísticas')]")
            if stats_tabs:
                stats_tabs[0].click()
                time.sleep(2)

            # Buscar tablas de jugadores
            player_tables = driver.find_elements(By.CSS_SELECTOR, "table.player-stats, table.match-stats, .player-list table")

            for table in player_tables:
                rows = table.find_elements(By.TAG_NAME, "tr")

                # Extraer headers (nombres de estadísticas)
                headers = []
                header_row = rows[0] if rows else None
                if header_row:
                    header_cells = header_row.find_elements(By.TAG_NAME, "th")
                    headers = [cell.text.strip() for cell in header_cells]

                # Extraer datos de jugadores
                for row in rows[1:]:  # Saltar header
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if cells:
                        player_data = {
                            'aux': match_number,
                            'jornada': match_info['jornada'],
                            'id_partido': match_id,
                            'arbitro': match_info['arbitro'],
                            'equipo_local': match_info['equipo_local'],
                            'equipo_visitante': match_info['equipo_visitante'],
                            'equipo_jugador': '',  # Se determinará según la tabla
                            'jugador': cells[0].text.strip() if cells else ''
                        }

                        # Agregar estadísticas
                        for i, cell in enumerate(cells[1:], 1):
                            stat_name = headers[i] if i < len(headers) else f'stat_{i}'
                            player_data[stat_name] = cell.text.strip()

                        players_data.append(player_data)

        except Exception as e:
            print(f"  ⚠️  Error extrayendo datos de jugadores: {e}")

        print(f"  ✓ Extraídos {len(players_data)} registros de jugadores")
        return players_data

    except Exception as e:
        print(f"  ✗ Error procesando partido: {e}")
        return []

def main():
    """Función principal"""

    # Leer URLs de partidos
    print("Leyendo URLs de partidos...")
    with open('match_urls.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"Total de partidos a procesar: {len(urls)}")

    # Configurar driver
    driver = setup_driver()

    all_data = []

    try:
        # Procesar cada partido
        for i, url in enumerate(urls, 1):
            match_data = extract_match_data(driver, url, i)
            all_data.extend(match_data)

            # Pausa entre peticiones para no sobrecargar el servidor
            time.sleep(2)

            # Guardar progreso cada 10 partidos
            if i % 10 == 0:
                print(f"\n💾 Guardando progreso... ({i}/{len(urls)} partidos procesados)")
                save_to_csv(all_data, 'match_data_progress.csv')

        # Guardar datos finales
        print(f"\n{'='*80}")
        print("💾 Guardando datos finales...")
        save_to_csv(all_data, 'match_data_final.csv')
        print(f"✓ Datos guardados exitosamente")
        print(f"✓ Total de registros: {len(all_data)}")
        print(f"{'='*80}")

    finally:
        driver.quit()
        print("\n✓ Proceso completado")

def save_to_csv(data, filename):
    """Guarda los datos en un archivo CSV"""

    if not data:
        print("⚠️  No hay datos para guardar")
        return

    # Obtener todas las claves únicas de todos los registros
    all_keys = set()
    for record in data:
        all_keys.update(record.keys())

    # Ordenar claves para tener un orden consistente
    fieldnames = sorted(list(all_keys))

    # Mover campos importantes al inicio
    priority_fields = ['aux', 'jornada', 'id_partido', 'arbitro', 'equipo_local',
                      'equipo_visitante', 'equipo_jugador', 'jugador']

    for field in reversed(priority_fields):
        if field in fieldnames:
            fieldnames.remove(field)
            fieldnames.insert(0, field)

    # Escribir CSV
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"  ✓ Guardado en: {filename}")

if __name__ == "__main__":
    main()
