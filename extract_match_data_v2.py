#!/usr/bin/env python3
"""
Script optimizado para extraer datos de árbitros y jugadores de cada partido
y generar un CSV con toda la información
"""

import time
import csv
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

def setup_driver():
    """Configura y retorna el driver de Chrome"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    return webdriver.Chrome(options=chrome_options)

def extract_match_id(url):
    """Extrae el ID del partido de la URL"""
    match = re.search(r'/match/view/([a-z0-9]+)', url)
    return match.group(1) if match else ""

def extract_jornada(soup):
    """Extrae el número de jornada del partido"""
    try:
        # Buscar el texto que contiene "Matchweek" o similar
        for text in soup.stripped_strings:
            if 'Primera División' in text:
                # El formato suele ser "Primera División25 October 2025 18:30"
                # Buscar siguiente elemento que pueda contener la jornada
                continue
        return ""
    except:
        return ""

def extract_match_data(driver, url, match_number):
    """Extrae todos los datos de un partido"""

    try:
        print(f"\n[{match_number}] Cargando: {url}")
        driver.get(url)
        time.sleep(5)  # Esperar a que cargue completamente

        # Obtener HTML con BeautifulSoup para parsing más fácil
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        match_id = extract_match_id(url)
        players_data = []

        # Extraer árbitro
        arbitro = ""
        referee_element = soup.find('dt', string='Referee')
        if referee_element and referee_element.find_next_sibling('dd'):
            arbitro = referee_element.find_next_sibling('dd').text.strip()
            print(f"  Árbitro: {arbitro}")
        else:
            print(f"  ⚠️  Árbitro no encontrado")

        # Extraer nombres de equipos
        team_names = []
        team_imgs = soup.find_all('img', alt=True)
        for img in team_imgs:
            alt = img.get('alt', '')
            if alt and 'Opta' not in alt and len(alt) > 2 and alt not in team_names:
                # Filtrar nombres que parecen equipos
                if any(word in alt.lower() for word in ['cf', 'fc', 'club', 'madrid', 'barcelona', 'athletic']):
                    team_names.append(alt)

        if len(team_names) >= 2:
            equipo_local = team_names[0]
            equipo_visitante = team_names[1]
            print(f"  {equipo_local} vs {equipo_visitante}")
        else:
            equipo_local = ""
            equipo_visitante = ""
            print(f"  ⚠️  Equipos no encontrados claramente")

        # Extraer jornada
        jornada = ""
        jornada_text = soup.find(string=re.compile(r'Matchweek|Jornada|Round'))
        if jornada_text:
            match_jornada = re.search(r'\d+', jornada_text)
            if match_jornada:
                jornada = match_jornada.group()

        # Buscar todas las tablas de estadísticas
        tables = soup.find_all('table')

        for table_idx, table in enumerate(tables):
            # Buscar el header de la tabla
            thead = table.find('thead')
            if not thead:
                continue

            # Extraer nombres de columnas
            headers = []
            header_row = thead.find('tr')
            if header_row:
                for th in header_row.find_all('th'):
                    abbr = th.find('abbr')
                    if abbr and abbr.get('title'):
                        headers.append(abbr.get('title'))
                    else:
                        headers.append(th.text.strip())

            # Si no hay headers válidos, saltar esta tabla
            if not headers or all(h == '' for h in headers):
                continue

            print(f"  Tabla {table_idx + 1}: {len(headers)} columnas")

            # Determinar el equipo de esta tabla (basado en el orden)
            equipo_jugador = equipo_local if table_idx <= 1 else equipo_visitante

            # Extraer filas de jugadores
            tbody = table.find('tbody')
            if not tbody:
                continue

            rows = tbody.find_all('tr')
            for row in rows:
                # Buscar el nombre del jugador (primer <th class="Opta-Player">)
                player_th = row.find('th', class_='Opta-Player')
                if not player_th:
                    continue

                jugador = player_th.text.strip()

                # Filtrar filas que no son jugadores (Total, etc.)
                if jugador.lower() in ['total', 'team total', 'equipo']:
                    continue

                # Extraer estadísticas
                stats_cells = row.find_all('td', class_='Opta-Stat')

                # Crear registro del jugador
                player_data = {
                    'Aux': match_number,
                    'Jornada': jornada,
                    'ID_PARTIDO': match_id,
                    'Arbitro': arbitro,
                    'Equipo_local': equipo_local,
                    'Equipo_Visitante': equipo_visitante,
                    'Equipo_Jugador': equipo_jugador,
                    'Jugador': jugador
                }

                # Agregar cada estadística con su nombre
                for i, cell in enumerate(stats_cells):
                    stat_name = headers[i + 1] if i + 1 < len(headers) else f'Stat_{i}'
                    stat_value = cell.get('data-srt', cell.text.strip())
                    player_data[stat_name] = stat_value

                players_data.append(player_data)

        print(f"  ✓ Extraídos {len(players_data)} registros de jugadores")
        return players_data

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return []

def save_to_csv(data, filename):
    """Guarda los datos en un archivo CSV"""

    if not data:
        print("⚠️  No hay datos para guardar")
        return

    # Obtener todas las claves únicas
    all_keys = set()
    for record in data:
        all_keys.update(record.keys())

    # Ordenar claves con prioridad
    priority_fields = ['Aux', 'Jornada', 'ID_PARTIDO', 'Arbitro', 'Equipo_local',
                      'Equipo_Visitante', 'Equipo_Jugador', 'Jugador']

    fieldnames = []
    for field in priority_fields:
        if field in all_keys:
            fieldnames.append(field)
            all_keys.remove(field)

    # Agregar el resto de campos alfabéticamente
    fieldnames.extend(sorted(list(all_keys)))

    # Escribir CSV
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"  ✓ Guardado en: {filename}")

def main():
    """Función principal"""

    # Leer URLs
    print("Leyendo URLs de partidos...")
    with open('match_urls.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"Total de partidos a procesar: {len(urls)}\n")

    driver = setup_driver()
    all_data = []

    try:
        for i, url in enumerate(urls, 1):
            match_data = extract_match_data(driver, url, i)
            all_data.extend(match_data)

            # Guardar progreso cada 10 partidos
            if i % 10 == 0:
                print(f"\n💾 Guardando progreso... ({i}/{len(urls)})")
                save_to_csv(all_data, 'match_data_progress.csv')

            # Pausa entre peticiones
            time.sleep(2)

        # Guardar datos finales
        print(f"\n{'='*80}")
        print("💾 Guardando datos finales...")
        save_to_csv(all_data, 'BBDD_partidos_completo.csv')
        print(f"✓ Total de registros: {len(all_data)}")
        print(f"✓ Archivo: BBDD_partidos_completo.csv")
        print(f"{'='*80}\n")

    finally:
        driver.quit()
        print("✓ Proceso completado")

if __name__ == "__main__":
    main()
