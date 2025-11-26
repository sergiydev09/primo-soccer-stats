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
import argparse
import multiprocessing
import concurrent.futures
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# Configuración de ligas
LEAGUES = {
    'spain': {
        'name': 'Primera División',
        'url': 'https://optaplayerstats.statsperform.com/en_GB/soccer/primera-divisi%C3%B3n-2025-2026/80zg2v1cuqcfhphn56u4qpyqc/opta-player-stats',
        'csv_file': 'BBDD_partidos_spain.csv',
        'urls_file': 'match_urls_spain.txt'
    },
    'england': {
        'name': 'Premier League',
        'url': 'https://optaplayerstats.statsperform.com/en_GB/soccer/premier-league-2025-2026/51r6ph2woavlbbpk8f29nynf8/opta-player-stats',
        'csv_file': 'BBDD_partidos_england.csv',
        'urls_file': 'match_urls_england.txt'
    },
    'germany': {
        'name': 'Bundesliga',
        'url': 'https://optaplayerstats.statsperform.com/en_GB/soccer/bundesliga-2025-2026/2bchmrj23l9u42d68ntcekob8/opta-player-stats',
        'csv_file': 'BBDD_partidos_germany.csv',
        'urls_file': 'match_urls_germany.txt'
    },
    'italy': {
        'name': 'Serie A',
        'url': 'https://optaplayerstats.statsperform.com/en_GB/soccer/serie-a-2025-2026/emdmtfr1v8rey2qru3xzfwges/opta-player-stats',
        'csv_file': 'BBDD_partidos_italy.csv',
        'urls_file': 'match_urls_italy.txt'
    },
    'france': {
        'name': 'Ligue 1',
        'url': 'https://optaplayerstats.statsperform.com/en_GB/soccer/ligue-1-2025-2026/dbxs75cag7zyip5re0ppsanmc/opta-player-stats',
        'csv_file': 'BBDD_partidos_france.csv',
        'urls_file': 'match_urls_france.txt'
    }
}

def setup_driver():
    """Configura el driver de Chrome"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    # Deshabilitar imágenes para cargar más rápido
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    return webdriver.Chrome(options=chrome_options)

def extract_urls(league_config):
    """Extrae URLs de todos los partidos"""
    print("="*80)
    print(f"EXTRAYENDO URLs DE PARTIDOS - {league_config['name']}")
    print("="*80)

    url = league_config['url']

    driver = setup_driver()
    print(f"\nCargando: {url}")
    driver.get(url)
    time.sleep(5)

    # Scroll para cargar contenido dinámico
    print("Haciendo scroll...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    no_change_count = 0
    max_scrolls = 30  # Aumentado de 5 a 30
    scroll_count = 0
    
    while scroll_count < max_scrolls and no_change_count < 3:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            no_change_count += 1
            print(f"  Sin cambios ({no_change_count}/3)")
        else:
            no_change_count = 0
            print(f"  Contenido cargado (scroll {scroll_count + 1})")
        
        last_height = new_height
        scroll_count += 1
    
    print(f"Scroll completado después de {scroll_count} intentos")

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
    with open(league_config['urls_file'], 'w') as f:
        for url in match_urls:
            f.write(url + '\n')

    print(f"\n✓ {len(match_urls)} URLs guardadas en: {league_config['urls_file']}\n")
    return match_urls

def extract_match_data(driver, url, match_number):
    """Extrae datos de un partido"""
    driver.get(url)
    
    # Esperar a que cargue el contenido dinámico (header del partido)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "Opta-MatchHeader"))
        )
        # Esperar también a que haya al menos una tabla de jugadores
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "Opta-Player"))
        )
        time.sleep(1)
    except Exception as e:
        raise Exception(f"Timeout esperando carga de página: {str(e)}")

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    match_id = re.search(r'/match/view/([a-z0-9]+)', url).group(1)

    # Extraer árbitro
    arbitro = ""
    referee_element = soup.find('dt', string='Referee')
    if referee_element and referee_element.find_next_sibling('dd'):
        arbitro = referee_element.find_next_sibling('dd').text.strip()

    # Extraer equipos
    team_names = []
    # Intentar primero con texto (más fiable)
    name_elements = soup.find_all(class_='Opta-Team-Name')
    for el in name_elements:
        text = el.get_text(strip=True)
        if text and text not in team_names:
            team_names.append(text)
            
    # Si no encuentra texto, intentar con imágenes
    if len(team_names) < 2:
        for img in soup.find_all('img', alt=True):
            alt = img.get('alt', '')
            if alt and 'Opta' not in alt and len(alt) > 2 and alt not in team_names:
                if any(word in alt.lower() for word in ['cf', 'fc', 'club', 'madrid', 'barcelona', 'athletic', 'real', 'sporting', 'deportivo', 'sociedad', 'betis', 'sevilla', 'valencia', 'villarreal', 'osasuna', 'alavés', 'mallorca', 'girona', 'celta', 'rayo', 'palmas', 'almería', 'granada', 'cadiz', 'valladolid', 'leganés', 'espanyol', 'levante', 'eibar', 'oviedo', 'racing', 'zaragoza', 'burgos', 'ferrol', 'elche', 'tenerife', 'albacete', 'cartagena', 'mirandés', 'huesca', 'eldense', 'amorebieta', 'alcorcón', 'andorra']):
                    team_names.append(alt)

    equipo_local = team_names[0] if len(team_names) >= 1 else ""
    equipo_visitante = team_names[1] if len(team_names) >= 2 else ""
    
    # Extraer fecha
    fecha = ""
    # Buscar en todo el texto de la página
    page_text = soup.get_text(" ", strip=True)
    
    # Patrones de fecha:
    # 1. DD Month YYYY (e.g. 15 August 2024)
    # 2. Month DD, YYYY (e.g. August 15, 2024)
    # 3. DD/MM/YYYY
    date_patterns = [
        r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}',
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}'
    ]
    
    for pattern in date_patterns:
        date_match = re.search(pattern, page_text, re.IGNORECASE)
        if date_match:
            fecha = date_match.group()
            # Normalizar nombres de meses a 3 letras para consistencia
            fecha = fecha.replace('Sept', 'Sep').replace('September', 'Sep')
            fecha = fecha.replace('October', 'Oct').replace('November', 'Nov').replace('December', 'Dec')
            fecha = fecha.replace('January', 'Jan').replace('February', 'Feb').replace('March', 'Mar')  
            fecha = fecha.replace('April', 'Apr').replace('August', 'Aug')
            # May, Jun, Jul ya son de 3 letras
            break
    
    # Mostrar información del partido (solo si no hay barra de progreso activa)
    if not hasattr(extract_match_data, 'quiet_mode') or not extract_match_data.quiet_mode:
        print(f"[{match_number}] {fecha} | {equipo_local} vs {equipo_visitante}")

    # Extraer jornada
    jornada = ""
    # Buscar "Matchweek X" o "Round X"
    jornada_match = re.search(r'(?:Matchweek|Jornada|Round)\s+(\d+)', page_text, re.IGNORECASE)
    if jornada_match:
        jornada = jornada_match.group(1)

    # Extraer datos de jugadores
    players_data = []
    tables = soup.find_all('table')

    # Filtrar solo tablas de jugadores
    candidate_tables = []
    for table in tables:
        if table.find('th', class_='Opta-Player'):
            candidate_tables.append(table)
            
    # Seleccionar las tablas correctas (Home y Away)
    # A veces hay tablas duplicadas (resumen vs detalle) para el mismo equipo
    final_tables = []
    
    if candidate_tables:
        # La primera tabla siempre es el equipo local
        final_tables.append(candidate_tables[0])
        
        # Para la segunda tabla (visitante), buscamos una que tenga jugadores diferentes
        # Extraemos el primer jugador de la primera tabla para comparar
        first_table_players = set()
        tbody = candidate_tables[0].find('tbody')
        if tbody:
            for row in tbody.find_all('tr'):
                th = row.find('th', class_='Opta-Player')
                if th:
                    first_table_players.add(th.text.strip())
        
        for i in range(1, len(candidate_tables)):
            current_table = candidate_tables[i]
            # Verificar primer jugador de esta tabla
            tbody = current_table.find('tbody')
            if not tbody: continue
            
            is_duplicate = False
            for row in tbody.find_all('tr'):
                th = row.find('th', class_='Opta-Player')
                if th:
                    player_name = th.text.strip()
                    if player_name in first_table_players:
                        is_duplicate = True
                    break # Solo comprobamos el primer jugador
            
            if not is_duplicate:
                final_tables.append(current_table)
                break # Ya tenemos la tabla del visitante
                
    # Procesar las tablas seleccionadas
    for table_idx, table in enumerate(final_tables):
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

        equipo_jugador = equipo_local if table_idx == 0 else equipo_visitante

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
                'Fecha': fecha,
                'Jornada': jornada,
                'ID_PARTIDO': match_id,
                'Arbitro': arbitro,
                'Equipo_local': equipo_local,
                'Equipo_Visitante': equipo_visitante,
                'Jugador': jugador
            }

            for i, cell in enumerate(stats_cells):
                stat_name = headers[i + 1] if i + 1 < len(headers) else f'Stat_{i}'
                player_data[stat_name] = cell.get('data-srt', cell.text.strip())

            players_data.append(player_data)

    # Retornar datos y metadatos del partido
    return {
        'players': players_data,
        'fecha': fecha,
        'equipo_local': equipo_local,
        'equipo_visitante': equipo_visitante,
        'match_number': match_number
    }

def process_batch(batch_data, progress_counter=None, progress_lock=None):
    """Procesa un lote de URLs con una única instancia del driver"""
    batch_id, urls_with_indices = batch_data
    
    driver = setup_driver()
    batch_results = []
    failed_matches = []
    
    # Activar modo silencioso para extract_match_data
    extract_match_data.quiet_mode = True
    
    try:
        for i, url in urls_with_indices:
            try:
                result = extract_match_data(driver, url, i)
                if result and 'players' in result:
                    batch_results.extend(result['players'])
                    # Actualizar contador compartido
                    if progress_counter is not None and progress_lock is not None:
                        with progress_lock:
                            progress_counter.value += 1
                else:
                    failed_matches.append((i, url, "No se extrajeron datos"))
                    if progress_counter is not None and progress_lock is not None:
                        with progress_lock:
                            progress_counter.value += 1
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                failed_matches.append((i, url, error_msg))
                # Registrar en archivo
                with open('scraper_errors.log', 'a') as f:
                    f.write(f"Partido {i}: {url}\n")
                    f.write(f"Error: {error_msg}\n\n")
                if progress_counter is not None and progress_lock is not None:
                    with progress_lock:
                        progress_counter.value += 1
                continue
    finally:
        driver.quit()
        
    return batch_results, failed_matches

def extract_all_data(league_config, limit=None, workers=None):
    """Extrae datos de todos los partidos en paralelo"""
    print("="*80)
    print(f"EXTRAYENDO DATOS DE TODOS LOS PARTIDOS (PARALELO) - {league_config['name']}")
    print("="*80)

    # Leer URLs
    try:
        with open(league_config['urls_file'], 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ Archivo {league_config['urls_file']} no encontrado")
        print("   Ejecuta primero: python3 scraper.py urls --league <league>")
        return

    if limit:
        urls = urls[:limit]

    total_urls = len(urls)
    print(f"\nTotal de partidos: {total_urls}\n")

    # Configuración de paralelismo
    if workers:
        max_workers = workers
    else:
        # Usamos hasta 8 workers si es posible
        max_workers = min(8, total_urls)
    
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

    print(f"Iniciando {len(batches)} workers para procesar {total_urls} partidos...\n")
    
    all_data = []
    all_failed = []
    
    # Crear contador compartido y lock para el progreso
    manager = multiprocessing.Manager()
    progress_counter = manager.Value('i', 0)
    progress_lock = manager.Lock()
    
    # Ejecutar en paralelo con barra de progreso
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Enviar trabajos
        future_to_batch = {executor.submit(process_batch, batch, progress_counter, progress_lock): batch 
                          for batch in batches}
        
        # Monitorear progreso con tqdm
        with tqdm(total=total_urls, desc="Extrayendo partidos", unit="partido", 
                  bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') as pbar:
            
            # Actualizar barra mientras los trabajos se completan
            while progress_counter.value < total_urls:
                current = progress_counter.value
                pbar.n = current
                pbar.refresh()
                time.sleep(0.1)
                
            # Recoger resultados
            for future in concurrent.futures.as_completed(future_to_batch):
                try:
                    data, failed = future.result()
                    all_data.extend(data)
                    all_failed.extend(failed)
                except Exception as exc:
                    print(f'\n❌ Generó una excepción: {exc}')
            
            # Asegurar que la barra llegue a 100%
            pbar.n = total_urls
            pbar.refresh()
    
    # Mostrar resumen de errores si los hay
    if all_failed:
        print(f"\n⚠️ {len(all_failed)} partidos fallidos. Ver scraper_errors.log para detalles.")

    # Guardar datos finales
    print("\n" + "="*80)
    print("💾 Guardando datos finales...")
    save_csv(all_data, league_config['csv_file'])
    print(f"✓ {len(all_data)} registros guardados")
    print(f"✓ Archivo: {league_config['csv_file']}")
    print("="*80 + "\n")
    
    # Generar resumen de partidos por fecha
    print("\n" + "="*80)
    print("RESUMEN DE PARTIDOS PROCESADOS")
    print("="*80 + "\n")
    
    # Agrupar partidos por fecha
    from collections import defaultdict
    from datetime import datetime
    
    partidos_por_fecha = defaultdict(list)
    
    for record in all_data:
        fecha = record.get('Fecha', 'Sin fecha')
        aux = record.get('Aux', 0)
        local = record.get('Equipo_local', '')
        visitante = record.get('Equipo_Visitante', '')
        
        # Crear clave única para cada partido
        partido_key = (aux, fecha, local, visitante)
        
        if partido_key not in [p[0] for p in partidos_por_fecha[fecha]]:
            partidos_por_fecha[fecha].append((partido_key, 0))
    
    # Contar jugadores por partido
    for record in all_data:
        fecha = record.get('Fecha', 'Sin fecha')
        aux = record.get('Aux', 0)
        local = record.get('Equipo_local', '')
        visitante = record.get('Equipo_Visitante', '')
        partido_key = (aux, fecha, local, visitante)
        
        for i, (pk, count) in enumerate(partidos_por_fecha[fecha]):
            if pk == partido_key:
                partidos_por_fecha[fecha][i] = (pk, count + 1)
                break
    
    # Ordenar fechas (más reciente primero)
    def parse_date(date_str):
        # Intentar varios formatos de fecha
        formats = [
            '%d %b %Y',      # 15 Aug 2025
            '%d %B %Y',      # 15 August 2025
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        # Si ninguno funciona, intentar con replace para normalizar
        try:
            # Normalizar "Sept" a "Sep"
            normalized = date_str.replace('Sept', 'Sep')
            return datetime.strptime(normalized, '%d %b %Y')
        except:
            # Último intento: imprimir para debug y retornar min
            print(f"⚠️ No se pudo parsear fecha: '{date_str}'")
            return datetime.min
    
    fechas_ordenadas = sorted(partidos_por_fecha.keys(), key=parse_date, reverse=True)
    
    # Mostrar resumen
    for fecha in fechas_ordenadas:
        print(f"\n📅 {fecha}")
        print("-" * 60)
        
        # Ordenar partidos por número (Aux)
        partidos = sorted(partidos_por_fecha[fecha], key=lambda x: x[0][0])
        
        for partido_key, num_jugadores in partidos:
            aux, _, local, visitante = partido_key
            # Acortar nombres de equipos si son muy largos
            if len(local) > 20:
                local = local[:17] + "..."
            if len(visitante) > 20:
                visitante = visitante[:17] + "..."
            print(f"  {local:25} vs  {visitante:25} ({num_jugadores} jugadores)")
    
    print("\n" + "="*80)

def save_csv(data, filename):
    """Guarda datos en CSV"""
    if not data:
        return

    all_keys = set()
    for record in data:
        all_keys.update(record.keys())

    priority_fields = ['Aux', 'Fecha', 'Jornada', 'ID_PARTIDO', 'Arbitro', 'Equipo_local',
                      'Equipo_Visitante', 'Jugador']

    fieldnames = [f for f in priority_fields if f in all_keys]
    fieldnames.extend(sorted([k for k in all_keys if k not in priority_fields]))

    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def main():
    parser = argparse.ArgumentParser(description='Scraper de datos de partidos')
    parser.add_argument('command', choices=['urls', 'data', 'all'], help='Comando a ejecutar')
    parser.add_argument('--league', type=str, default='spain', 
                       choices=['spain', 'england', 'germany', 'italy', 'france', 'both', 'all'],
                       help='Liga a procesar: spain, england, germany, italy, france, both (spain+england), o all (todas)')
    parser.add_argument('--limit', type=int, help='Limitar número de partidos (para pruebas)')
    parser.add_argument('--workers', type=int, help='Número de workers en paralelo')
    
    args = parser.parse_args()

    start_time = time.time()
    
    # Determinar qué ligas procesar
    if args.league == 'both':
        leagues_to_process = ['spain', 'england']
    elif args.league == 'all':
        leagues_to_process = ['spain', 'england', 'germany', 'italy', 'france']
    else:
        leagues_to_process = [args.league]
    
    # Procesar cada liga
    for league_key in leagues_to_process:
        league_config = LEAGUES[league_key]
        
        print("\n" + "#"*80)
        print(f"# PROCESANDO: {league_config['name'].upper()}")
        print("#"*80 + "\n")
        
        if args.command == 'urls':
            extract_urls(league_config)
        elif args.command == 'data':
            extract_all_data(league_config, limit=args.limit, workers=args.workers)
        elif args.command == 'all':
            extract_urls(league_config)
            extract_all_data(league_config, limit=args.limit, workers=args.workers)
        
    duration = time.time() - start_time
    print(f"\n⏱️ Tiempo total de ejecución: {duration:.2f} segundos")


if __name__ == "__main__":
    main()
