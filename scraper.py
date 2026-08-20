#!/usr/bin/env python3
"""
Extractor de Datos de Partidos - Ligas y competiciones europeas
Uso: python3 scraper.py [urls|data|all|seasons] [--league <liga>] [--season <YYYY-YYYY>]
"""

import sys
import os
import json
import time
import csv
import re
import math
import argparse
import multiprocessing
import concurrent.futures
from datetime import date
from urllib.parse import quote
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

BASE_URL = 'https://optaplayerstats.statsperform.com/en_GB/soccer'

# Estructura de salida organizada (rutas ancladas al directorio del proyecto)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_OPTA_DIR = os.path.join(BASE_DIR, 'data', 'opta')
URLS_DIR = os.path.join(DATA_OPTA_DIR, 'urls')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
SEASON_CACHE_FILE = os.path.join(CACHE_DIR, 'seasons_cache.json')
ERROR_LOG_FILE = os.path.join(LOGS_DIR, 'scraper_errors.log')


def ensure_parent_dir(path):
    """Crea el directorio contenedor de un archivo si no existe"""
    os.makedirs(os.path.dirname(path), exist_ok=True)


def opta_csv_path(league_key, season):
    return os.path.join(DATA_OPTA_DIR, f"BBDD_partidos_{league_key}_{season}.csv")


def opta_urls_path(league_key, season):
    return os.path.join(URLS_DIR, f"match_urls_{league_key}_{season}.txt")

# Configuración de ligas.
# 'seasons' mapea temporada -> ID de torneo de Opta, que cambia cada temporada.
# Las temporadas no listadas aquí se descubren automáticamente desde el selector
# de temporadas de la propia web y se cachean en seasons_cache.json.
LEAGUES = {
    'spain': {
        'name': 'Primera División',
        'slug': 'primera-división',
        'seasons': {
            '2025-2026': '80zg2v1cuqcfhphn56u4qpyqc',
            '2026-2027': '830epggffy1nfkfyrtpqdwhlg',
        }
    },
    'england': {
        'name': 'Premier League',
        'slug': 'premier-league',
        'seasons': {
            '2025-2026': '51r6ph2woavlbbpk8f29nynf8',
            '2026-2027': '6pdwluctev9iebv00r4qqukno',
        }
    },
    'germany': {
        'name': 'Bundesliga',
        'slug': 'bundesliga',
        'seasons': {
            '2025-2026': '2bchmrj23l9u42d68ntcekob8',
            '2026-2027': '8h5xijv2u4mlf5028gso6kw7o',
        }
    },
    'italy': {
        'name': 'Serie A',
        'slug': 'serie-a',
        'seasons': {
            '2025-2026': 'emdmtfr1v8rey2qru3xzfwges',
            '2026-2027': '60cryos85i4bp5ul34tt0brx0',
        }
    },
    'france': {
        'name': 'Ligue 1',
        'slug': 'ligue-1',
        'seasons': {
            '2025-2026': 'dbxs75cag7zyip5re0ppsanmc',
            '2026-2027': 'bqnc4ccgnrp6pb3bktqet0yz8',
        }
    },
    'ucl': {
        'name': 'UEFA Champions League',
        'slug': 'uefa-champions-league',
        'seasons': {
            '2025-2026': '2mr0u0l78k2gdsm79q56tb2fo',
            '2026-2027': '99jev9kv55deht65t6myggxlg',
        }
    },
    'uel': {
        'name': 'UEFA Europa League',
        'slug': 'uefa-europa-league',
        'seasons': {
            '2025-2026': '7ttpe5jzya3vjhjadiemjy7mc',
            '2026-2027': '1rpi0q64a7kut2wiuvecmgbv8',
        }
    },
    'spain2': {
        'name': 'Segunda División',
        'slug': 'segunda-división',
        'seasons': {
            '2025-2026': 'dko0hzifl1xv9c51s3ai017v8',
            '2026-2027': 'fgkxmpz2ewao1l63jrbkgg7o',
        }
    }
}

ALL_LEAGUES = ['spain', 'england', 'germany', 'italy', 'france', 'ucl', 'uel', 'spain2']

def current_season(today=None):
    """Temporada en curso. El corte es julio: en agosto de 2026 la temporada es 2026-2027"""
    today = today or date.today()
    start_year = today.year if today.month >= 7 else today.year - 1
    return f"{start_year}-{start_year + 1}"

def normalize_season(season):
    """Acepta '2026-2027', '2026/2027' o '2026' y devuelve '2026-2027'"""
    season = str(season).strip().replace('/', '-')
    if re.fullmatch(r'\d{4}', season):
        year = int(season)
        return f"{year}-{year + 1}"
    if not re.fullmatch(r'\d{4}-\d{4}', season):
        raise argparse.ArgumentTypeError(
            f"Temporada no válida: '{season}'. Formato esperado: 2026-2027")
    return season

def _load_season_cache():
    """Lee las temporadas descubiertas en ejecuciones anteriores"""
    if not os.path.exists(SEASON_CACHE_FILE):
        return {}
    try:
        with open(SEASON_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

def _save_season_cache(cache):
    try:
        ensure_parent_dir(SEASON_CACHE_FILE)
        with open(SEASON_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False, sort_keys=True)
    except OSError as e:
        print(f"⚠️ No se pudo guardar {SEASON_CACHE_FILE}: {e}")

def build_url(slug, season, tournament_id):
    """Construye la URL de Opta para una competición y temporada"""
    return f"{BASE_URL}/{quote(f'{slug}-{season}', safe='')}/{tournament_id}/opta-player-stats"

def discover_seasons(league_key):
    """Descubre las temporadas disponibles leyendo el selector de temporada de la web.

    Devuelve {'2026-2027': 'id_de_torneo', ...}
    """
    base = LEAGUES[league_key]
    reference = max(base['seasons'])
    reference_url = build_url(base['slug'], reference, base['seasons'][reference])

    driver = setup_driver()
    found = {}
    try:
        driver.get(reference_url)
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'select[name="season"]'))
            )
        except Exception:
            time.sleep(5)

        for select in driver.find_elements(By.CSS_SELECTOR, 'select[name="season"]'):
            for option in select.find_elements(By.TAG_NAME, 'option'):
                value = option.get_attribute('value') or ''
                match = re.search(r'/soccer/[^/]+?-(\d{4}-\d{4})/([a-z0-9]+)/', value)
                if match:
                    found[match.group(1)] = match.group(2)
    except Exception as e:
        print(f"⚠️ No se pudieron leer las temporadas de {base['name']}: {e}")
    finally:
        driver.quit()

    return found

def available_seasons(league_key, discover=True):
    """Temporadas conocidas (configuradas + cacheadas + descubiertas)"""
    seasons = dict(LEAGUES[league_key]['seasons'])
    seasons.update(_load_season_cache().get(league_key, {}))
    if discover:
        found = discover_seasons(league_key)
        if found:
            cache = _load_season_cache()
            cache.setdefault(league_key, {}).update(found)
            _save_season_cache(cache)
            seasons.update(found)
    return seasons

def resolve_tournament_id(league_key, season):
    """Obtiene el ID de torneo de una temporada, descubriéndolo si hace falta"""
    base = LEAGUES[league_key]

    if season in base['seasons']:
        return base['seasons'][season]

    cached = _load_season_cache().get(league_key, {}).get(season)
    if cached:
        return cached

    print(f"🔎 Buscando la temporada {season} de {base['name']} en la web...")
    seasons = available_seasons(league_key)
    if season in seasons:
        print(f"   ✓ Encontrada: {seasons[season]}")
        return seasons[season]

    disponibles = ', '.join(sorted(seasons)) or 'ninguna'
    raise SystemExit(
        f"❌ La temporada {season} no está disponible para {base['name']}.\n"
        f"   Temporadas disponibles: {disponibles}")

def build_league_config(league_key, season):
    """Config completa (URL y archivos) de una competición para una temporada"""
    base = LEAGUES[league_key]
    return {
        'key': league_key,
        'name': base['name'],
        'season': season,
        'url': build_url(base['slug'], season, resolve_tournament_id(league_key, season)),
        'csv_file': opta_csv_path(league_key, season),
        'urls_file': opta_urls_path(league_key, season)
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
    print(f"EXTRAYENDO URLs DE PARTIDOS - {league_config['name']} {league_config['season']}")
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
    ensure_parent_dir(league_config['urls_file'])
    with open(league_config['urls_file'], 'w') as f:
        for url in match_urls:
            f.write(url + '\n')

    if not match_urls:
        print(f"\n⚠️ No se encontró ningún partido de {league_config['name']} {league_config['season']}.")
        print("   Es normal si la temporada todavía no ha empezado.\n")
    else:
        print(f"\n✓ {len(match_urls)} URLs guardadas en: {league_config['urls_file']}\n")
    return match_urls

def extract_match_data(driver, url, match_number):
    """Extrae datos de un partido"""
    driver.get(url)
    
    # Esperar a que cargue el contenido dinámico (header del partido)
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "Opta-MatchHeader"))
        )
        # Esperar también a que haya al menos una tabla de jugadores
        WebDriverWait(driver, 20).until(
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


    # Extraer equipos con estrategia múltiple
    team_names = []
    
    # Estrategia 1: Buscar elementos con clase Opta-Team-Name
    name_elements = soup.find_all(class_='Opta-Team-Name')
    for el in name_elements:
        text = el.get_text(strip=True)
        if text and text not in team_names and len(text) > 2:
            team_names.append(text)
    
    # Estrategia 2: Si no se encontraron, buscar en enlaces <a> del filtro de equipos
    if len(team_names) < 2:
        # Buscar enlaces que contengan "filter" en su href o clase
        filter_links = soup.find_all('a', href=True)
        for link in filter_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            # Links de filtro suelen tener el team ID en el href
            if '/team/' in href or 'filter' in link.get('class', []):
                if text and text not in team_names and len(text) > 2:
                    # Evitar textos genéricos como "All", "Home", "Away"
                    if text.lower() not in ['all', 'home', 'away', 'filter']:
                        team_names.append(text)
    
    # Estrategia 3: Buscar en el header del partido
    if len(team_names) < 2:
        header = soup.find(class_='Opta-MatchHeader')
        if header:
            # Buscar todos los textos en el header que parezcan nombres de equipos
            header_text = header.get_text(" ", strip=True)
            # Separar por el marcador (números separados por guiones o espacios)
            # Buscar patrón: "Equipo1 X - Y Equipo2" o "Equipo1 X Y Equipo2"
            score_pattern = r'(\d+)\s*[-:]\s*(\d+)'
            parts = re.split(score_pattern, header_text)
            if len(parts) >= 4:
                team1 = parts[0].strip()
                team2 = parts[3].strip() if len(parts) > 3 else ""
                if team1 and team1 not in team_names and len(team1) > 2:
                    team_names.append(team1)
                if team2 and team2 not in team_names and len(team2) > 2:
                    team_names.append(team2)
    
    # Estrategia 4: Buscar en imágenes (última opción)
    if len(team_names) < 2:
        for img in soup.find_all('img', alt=True):
            alt = img.get('alt', '')
            if alt and 'Opta' not in alt and len(alt) > 2 and alt not in team_names:
                # Lista de palabras clave que suelen estar en nombres de equipos
                team_keywords = ['cf', 'fc', 'club', 'united', 'city', 'athletic', 'real', 'sporting', 
                                'deportivo', 'sociedad', 'madrid', 'barcelona', 'roma', 'lille', 
                                'milan', 'inter', 'juventus', 'ajax', 'bayern', 'dortmund', 'arsenal',
                                'chelsea', 'liverpool', 'manchester', 'tottenham', 'everton']
                if any(word in alt.lower() for word in team_keywords):
                    team_names.append(alt)


    equipo_local = team_names[0] if len(team_names) >= 1 else ""
    equipo_visitante = team_names[1] if len(team_names) >= 2 else ""
    
    # Limpiar nombres de equipos de texto extra (competiciones, fechas, etc.)
    def clean_team_name(name):
        if not name:
            return ""
        # Eliminar nombres de competiciones y palabras extra
        unwanted_patterns = [
            'UEFA Champions League',
            'UEFA Europa League',
            'UEFA Conference League',
            'Primera División',
            'Segunda División',
            'Premier League',
            'Bundesliga',
            'Serie A',
            'Ligue 1',
            'La Liga'
        ]
        for pattern in unwanted_patterns:
            name = name.replace(pattern, '')
        
        # Eliminar fechas y números de jornada
        name = re.sub(r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}', '', name, flags=re.IGNORECASE)
        name = re.sub(r'Matchweek\s+\d+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'Jornada\s+\d+', '', name, flags=re.IGNORECASE)
        
        # Limpiar espacios extra
        name = ' '.join(name.split())
        return name.strip()
    
    equipo_local = clean_team_name(equipo_local)
    equipo_visitante = clean_team_name(equipo_visitante)
    
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
                ensure_parent_dir(ERROR_LOG_FILE)
                with open(ERROR_LOG_FILE, 'a') as f:
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
    print(f"EXTRAYENDO DATOS DE TODOS LOS PARTIDOS (PARALELO) - {league_config['name']} {league_config['season']}")
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
    if total_urls == 0:
        print(f"\n⚠️ No hay partidos que procesar para {league_config['name']} {league_config['season']}.\n")
        return
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
            while progress_counter.value < total_urls and not all(f.done() for f in future_to_batch):
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
        print(f"\n⚠️ {len(all_failed)} partidos fallidos. Ver logs/scraper_errors.log para detalles.")

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

    ensure_parent_dir(filename)
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def show_seasons(league_keys):
    """Lista las temporadas disponibles de cada competición"""
    print("\n" + "="*80)
    print("TEMPORADAS DISPONIBLES")
    print("="*80)
    for league_key in league_keys:
        seasons = available_seasons(league_key)
        etiquetas = ', '.join(sorted(seasons, reverse=True)) or 'ninguna'
        print(f"\n{LEAGUES[league_key]['name']} ({league_key})")
        print(f"  {etiquetas}")
    print()

def main():
    parser = argparse.ArgumentParser(description='Scraper de datos de partidos')
    parser.add_argument('command', choices=['urls', 'data', 'all', 'seasons'],
                       help='Comando a ejecutar (seasons lista las temporadas disponibles)')
    parser.add_argument('--league', type=str, default='spain', 
                       choices=ALL_LEAGUES + ['both', 'all'],
                       help='Liga/Competición: spain, england, germany, italy, france, ucl, uel, spain2, both (spain+england), o all (todas)')
    parser.add_argument('--season', type=normalize_season, default=None,
                       help=f'Temporada, p.ej. 2026-2027 (por defecto la temporada en curso: {current_season()})')
    parser.add_argument('--limit', type=int, help='Limitar número de partidos (para pruebas)')
    parser.add_argument('--workers', type=int, help='Número de workers en paralelo')
    
    args = parser.parse_args()

    start_time = time.time()
    season = args.season or current_season()
    
    # Determinar qué ligas procesar
    if args.league == 'both':
        leagues_to_process = ['spain', 'england']
    elif args.league == 'all':
        leagues_to_process = list(ALL_LEAGUES)
    else:
        leagues_to_process = [args.league]

    if args.command == 'seasons':
        show_seasons(leagues_to_process)
        return

    print(f"\n🗓️  Temporada: {season}")
    
    # Procesar cada liga
    for league_key in leagues_to_process:
        league_config = build_league_config(league_key, season)
        
        print("\n" + "#"*80)
        print(f"# PROCESANDO: {league_config['name'].upper()} {season}")
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
