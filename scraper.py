#!/usr/bin/env python3
"""
Extractor de Datos de Partidos - Primera División 2025-2026
Uso: python3 scraper.py [urls|data|all]
"""

import sys
import time
import csv
import re
import math
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

def setup_driver():
    """Configura el driver de Chrome"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    return webdriver.Chrome(options=chrome_options)

def extract_urls():
    """Extrae URLs de todos los partidos"""
    print("="*80)
    print("EXTRAYENDO URLs DE PARTIDOS")
    print("="*80)

    url = "https://optaplayerstats.statsperform.com/en_GB/soccer/primera-divisi%C3%B3n-2025-2026/80zg2v1cuqcfhphn56u4qpyqc/opta-player-stats"

    driver = setup_driver()
    print(f"\nCargando: {url}")
    driver.get(url)
    time.sleep(5)

    # Scroll para cargar contenido dinámico
    print("Haciendo scroll...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    # Buscar URLs
    all_links = driver.find_elements(By.TAG_NAME, "a")
    match_urls = set()
    pattern = re.compile(r'/match/view/[a-z0-9]+')

    for link in all_links:
        href = link.get_attribute("href")
        if href and pattern.search(href):
            match_urls.add(href)

    match_urls = sorted(list(match_urls))
    driver.quit()

    # Guardar URLs
    with open('match_urls.txt', 'w') as f:
        for url in match_urls:
            f.write(url + '\n')

    print(f"\n✓ {len(match_urls)} URLs guardadas en: match_urls.txt\n")
    return match_urls

def extract_match_data(driver, url, match_number):
    """Extrae datos de un partido"""
    print(f"[{match_number}] Procesando partido...")
    driver.get(url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    match_id = re.search(r'/match/view/([a-z0-9]+)', url).group(1)

    # Extraer árbitro
    arbitro = ""
    referee_element = soup.find('dt', string='Referee')
    if referee_element and referee_element.find_next_sibling('dd'):
        arbitro = referee_element.find_next_sibling('dd').text.strip()

    # Extraer equipos
    team_names = []
    for img in soup.find_all('img', alt=True):
        alt = img.get('alt', '')
        if alt and 'Opta' not in alt and len(alt) > 2 and alt not in team_names:
            if any(word in alt.lower() for word in ['cf', 'fc', 'club', 'madrid', 'barcelona', 'athletic']):
                team_names.append(alt)

    equipo_local = team_names[0] if len(team_names) >= 1 else ""
    equipo_visitante = team_names[1] if len(team_names) >= 2 else ""

    # Extraer jornada
    jornada = ""
    jornada_text = soup.find(string=re.compile(r'Matchweek|Jornada|Round'))
    if jornada_text:
        match_jornada = re.search(r'\d+', jornada_text)
        if match_jornada:
            jornada = match_jornada.group()

    # Extraer datos de jugadores
    players_data = []
    tables = soup.find_all('table')

    for table_idx, table in enumerate(tables):
        thead = table.find('thead')
        if not thead:
            continue

        # Headers
        headers = []
        header_row = thead.find('tr')
        if header_row:
            for th in header_row.find_all('th'):
                abbr = th.find('abbr')
                headers.append(abbr.get('title') if abbr and abbr.get('title') else th.text.strip())

        if not headers or all(h == '' for h in headers):
            continue

        equipo_jugador = equipo_local if table_idx <= 1 else equipo_visitante

        # Filas de jugadores
        tbody = table.find('tbody')
        if not tbody:
            continue

        for row in tbody.find_all('tr'):
            player_th = row.find('th', class_='Opta-Player')
            if not player_th:
                continue

            jugador = player_th.text.strip()
            if jugador.lower() in ['total', 'team total', 'equipo']:
                continue

            stats_cells = row.find_all('td', class_='Opta-Stat')

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

            for i, cell in enumerate(stats_cells):
                stat_name = headers[i + 1] if i + 1 < len(headers) else f'Stat_{i}'
                player_data[stat_name] = cell.get('data-srt', cell.text.strip())

            players_data.append(player_data)

    print(f"  ✓ {len(players_data)} jugadores extraídos")
    return players_data

def process_batch(batch_data):
    """Procesa un lote de URLs con una única instancia del driver"""
    batch_id, urls_with_indices = batch_data
    print(f"🚀 Iniciando worker {batch_id} con {len(urls_with_indices)} partidos")
    
    driver = setup_driver()
    batch_results = []
    
    try:
        for i, url in urls_with_indices:
            try:
                match_data = extract_match_data(driver, url, i)
                batch_results.extend(match_data)
            except Exception as e:
                print(f"❌ Error en partido {i}: {str(e)}")
                continue
    finally:
        driver.quit()
        print(f"🏁 Worker {batch_id} finalizado")
        
    return batch_results

def extract_all_data(limit=None, workers=None):
    """Extrae datos de todos los partidos en paralelo"""
    print("="*80)
    print("EXTRAYENDO DATOS DE TODOS LOS PARTIDOS (PARALELO)")
    print("="*80)

    # Leer URLs
    try:
        with open('match_urls.txt', 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("❌ Archivo match_urls.txt no encontrado")
        print("   Ejecuta primero: python3 scraper.py urls")
        return

    if limit:
        urls = urls[:limit]

    total_urls = len(urls)
    print(f"\nTotal de partidos: {total_urls}\n")

    # Configuración de paralelismo
    if workers:
        max_workers = workers
    else:
        # Usamos 4 workers por defecto, o menos si hay pocos partidos
        max_workers = min(4, total_urls)
    
    if max_workers < 1: max_workers = 1
    
    # Dividir URLs en lotes
    batch_size = math.ceil(total_urls / max_workers)
    batches = []
    
    for i in range(max_workers):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, total_urls)
        if start_idx >= total_urls:
            break
            
        # Crear lista de tuplas (indice_original, url)
        batch_urls = []
        for j in range(start_idx, end_idx):
            batch_urls.append((j + 1, urls[j]))
            
        batches.append((i + 1, batch_urls))

    print(f"Iniciando {len(batches)} workers para procesar {total_urls} partidos...")
    
    all_data = []
    
    # Ejecutar en paralelo
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_batch = {executor.submit(process_batch, batch): batch for batch in batches}
        
        for future in concurrent.futures.as_completed(future_to_batch):
            try:
                data = future.result()
                all_data.extend(data)
                
                # Guardar progreso parcial (opcional, pero puede ser conflictivo con múltiples procesos escribiendo)
                # En este caso, solo guardamos cuando un batch termina
                print(f"� Batch completado. Total registros acumulados: {len(all_data)}")
                
            except Exception as exc:
                print(f'Generó una excepción: {exc}')

    # Guardar datos finales
    print("\n" + "="*80)
    print("💾 Guardando datos finales...")
    save_csv(all_data, 'BBDD_partidos_completo.csv')
    print(f"✓ {len(all_data)} registros guardados")
    print(f"✓ Archivo: BBDD_partidos_completo.csv")
    print("="*80 + "\n")

def save_csv(data, filename):
    """Guarda datos en CSV"""
    if not data:
        return

    all_keys = set()
    for record in data:
        all_keys.update(record.keys())

    priority_fields = ['Aux', 'Jornada', 'ID_PARTIDO', 'Arbitro', 'Equipo_local',
                      'Equipo_Visitante', 'Equipo_Jugador', 'Jugador']

    fieldnames = [f for f in priority_fields if f in all_keys]
    fieldnames.extend(sorted([k for k in all_keys if k not in priority_fields]))

    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Extractor de Datos de Partidos')
    parser.add_argument('command', choices=['urls', 'data', 'all'], help='Comando a ejecutar')
    parser.add_argument('--limit', type=int, help='Limitar número de partidos (para pruebas)')
    parser.add_argument('--workers', type=int, help='Número de workers en paralelo')
    
    args = parser.parse_args()

    start_time = time.time()

    if args.command == 'urls':
        extract_urls()
    elif args.command == 'data':
        extract_all_data(limit=args.limit, workers=args.workers)
    elif args.command == 'all':
        extract_urls()
        extract_all_data(limit=args.limit, workers=args.workers)
        
    duration = time.time() - start_time
    print(f"\n⏱️ Tiempo total de ejecución: {duration:.2f} segundos")

if __name__ == "__main__":
    main()
