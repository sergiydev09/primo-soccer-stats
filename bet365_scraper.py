#!/usr/bin/env python3
"""
Scraper de cuotas de bet365.es - partidos y mercados de apuestas por jornada.

Estrategia: Playwright lanza un Chrome real (perfil persistente propio) y navega
por bet365 como un usuario. No replica llamadas a la API (llevan tokens de un solo
uso): captura pasivamente las respuestas que la propia web hace a sus APIs internas
(matchmarketscontentapi / matchbettingcontentapi) y parsea su feed propietario
(registros separados por '|', campos 'CLAVE=valor' separados por ';').

Jerarquía del feed de un partido:
  MG (grupo de mercado, ej. "Goles - Más/Menos de")
    MA (columna, ej. "Más de" / "Menos de"; la primera MA sin nombre lleva las
        etiquetas de fila: jugadores o líneas)
      CO (sub-columna de cantidad en mercados de jugadores: "1+", "2+", "3+"...;
          cada CO reinicia el recorrido de filas)
        PA (celda: selección con cuota OD= fraccional, o etiqueta de fila sin OD)

Particularidades del servidor que condicionan el diseño:
  - Responde a veces en inglés cuando la petición no nace de una interacción real
    (cambio de hash). Por eso se navega con CLICS y se reintenta si llega inglés.
  - La SPA cachea: re-visitar la vista activa no genera petición. Para forzar una
    petición fresca hay que "rebotar" a otra pestaña y volver.

Uso:
  python3 bet365_scraper.py cuotas --league spain                  # La Liga, todo lo listado
  python3 bet365_scraper.py cuotas --league spain --jornada 1      # solo la próxima jornada
  python3 bet365_scraper.py cuotas --league spain --tabs "Resultado,Goles,Córners"
  python3 bet365_scraper.py cuotas --league spain --rapido         # sin expandir colapsados ni 'Ver más'
  python3 bet365_scraper.py cuotas --comp-id 135650998 --league-name "La Liga"
  python3 bet365_scraper.py ligas                                  # ver ligas configuradas
"""

import os
import re
import csv
import json
import sys
import time
import random
import argparse
import unicodedata
from datetime import datetime
from urllib.parse import unquote

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

from tqdm import tqdm
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE_URL = 'https://www.bet365.es'
DEFAULT_PROFILE = os.path.expanduser('~/.bet365_scraper_profile')

# Estructura de salida organizada (rutas ancladas al directorio del proyecto)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'cuotas', 'bet365')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
ERROR_LOG = os.path.join(LOGS_DIR, 'bet365_errors.log')


def ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

# IDs de competición de bet365 (el E<id> de la URL #/AC/B1/C1/D1002/E<id>/G40/).
# Pueden cambiar entre temporadas. Para añadir una liga: navega a ella en bet365.es,
# copia el número tras la "E" en la URL y añádelo aquí (o usa --comp-id).
LEAGUES = {
    'spain': {'name': 'La Liga', 'comp_id': '135650998'},
    'uel':   {'name': 'UEFA Europa League', 'comp_id': '135566042'},
    # Descubre el resto navegando en bet365.es y usa --comp-id, o añádelos aquí:
    # 'spain2':  {'name': 'LaLiga 2', 'comp_id': None},
    # 'england': {'name': 'Premier League', 'comp_id': None},
}

# Pestañas que no aportan cuotas tabulares (ninguna por ahora; 'Crear apuesta' sí
# trae las cuotas individuales de cada selección del builder)
EXCLUDED_TABS = set()

# Equivalencias inglés -> español de los nombres de pestañas (para el CSV y --tabs)
TAB_ES = {
    'Popular': 'Populares', 'Corners': 'Córners', 'Goals': 'Goles',
    'Result': 'Resultado', 'Shots': 'Remates', 'Cards/Fouls': 'Tarjetas/faltas',
    'Player Stats': 'Estadísticas de jugador', 'Scorers': 'Anotadores',
    'Half': '1ª/2ª mitad', 'Other': 'Otro', 'Asian Lines': 'Asiáticos',
    'Specials': 'Especiales', 'Bet Builder': 'Crear apuesta',
    'Quick Players': 'Rápidas a Jugadores', 'Player Quick Bets': 'Rápidas a Jugadores',
}

# Pestañas cuyo clic abre la vista nueva con filtros (sin datos capturables por
# HTTP); se navega directamente por hash a la vista clásica equivalente
HASH_FIRST_TABS = {'anotadores', 'scorers'}

# El servidor puede responder en inglés o español; se detecta por votación de
# palabras en los nombres de los grupos de mercados.
ENGLISH_HINTS = ('Over/Under', 'Both Teams', 'Corners', 'Handicap', 'Goalscorer',
                 'Shots', 'Cards', 'Full Time', 'Half', 'Asian', 'Correct Score',
                 'Score or Assist', 'To Be Booked', 'Player -', 'Draw No Bet',
                 'Clean Sheet', 'Winning Margin', 'Time of', 'Range', 'Total Goals',
                 'First ', 'Last ', 'Exact ', 'Team ', 'Match ', 'Number of',
                 'Saves', 'Goalkeeper', 'Booking', 'Penalty', 'Offside', 'Player',
                 'Tackles', 'Passes', 'Assists', 'Sending Off', 'Goal ', 'Win ')
SPANISH_HINTS = ('Más', 'Menos', 'Anotará', 'Córners', 'Tarjetas', 'Goles', 'mitad',
                 'Resultado', 'Marcador', 'Hándicap', 'Ambos', 'Empate', 'Descanso',
                 'Intervalo', 'Jugador', 'Primer', 'Último', 'Total de', 'Exacto',
                 'Doble oportunidad', 'Goleadores', 'Remates', 'apuesta', 'Sí',
                 'Minuto', 'Expulsión', 'Penalti', 'recibirá', 'equipo', 'asistirá')

# Normalización inglés->español de columnas y selecciones frecuentes
COL_ES = {'Over': 'Más de', 'Under': 'Menos de', 'Exactly': 'Exactamente',
          'Yes': 'Sí', 'No': 'No', 'Draw': 'Empate', 'Score': 'Anotará',
          'Assist': 'Asistirá', 'Score or Assist': 'Anotará o asistirá',
          'Home': 'Local', 'Away': 'Visitante', 'Odd': 'Impar', 'Even': 'Par'}
SEL_ES = {'Draw': 'Empate', 'Yes': 'Sí', 'No': 'No', 'None': 'Ninguno',
          'Odd': 'Impar', 'Even': 'Par', 'No Goal': 'Sin goles',
          'Home': 'Local', 'Away': 'Visitante'}

# Diccionario persistente id de mercado -> nombre en español. Se aprende solo:
# cada feed que llega en español lo alimenta y sirve para renombrar los ingleses.
MARKET_NAMES_FILE = os.path.join(CACHE_DIR, 'bet365_markets_es.json')

MADRID_TZ = ZoneInfo('Europe/Madrid') if ZoneInfo else None
LONDON_TZ = ZoneInfo('Europe/London') if ZoneInfo else None


def log_error(msg):
    ensure_parent_dir(ERROR_LOG)
    with open(ERROR_LOG, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")


def norm_txt(s):
    """minúsculas y sin acentos, para comparar nombres de pestañas."""
    s = unicodedata.normalize('NFD', s or '')
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower().strip()


def tab_es(name):
    return TAB_ES.get(name, name)


# ---------------------------------------------------------------------------
# Parser del feed "ZAP" de bet365
# ---------------------------------------------------------------------------

def zap_records(body):
    """Convierte el feed en una lista de dicts con '_t' = tipo de registro."""
    records = []
    for chunk in body.split('|'):
        if not chunk:
            continue
        parts = chunk.split(';')
        rtype = re.sub(r'[^A-Z]', '', parts[0])[:2]
        rec = {'_t': rtype}
        for part in parts[1:]:
            if '=' in part:
                key, val = part.split('=', 1)
                rec[key] = val
        records.append(rec)
    return records


def frac_to_dec(od):
    """'13/10' -> 2.3; '1/500' -> 1.002. Devuelve None si no es parseable."""
    if not od:
        return None
    od = od.strip()
    if '/' in od:
        try:
            num, den = od.split('/')
            return round(1.0 + float(num) / float(den), 3)
        except (ValueError, ZeroDivisionError):
            return None
    try:
        return round(float(od), 3)
    except ValueError:
        return None


def parse_fixture_list(body):
    """Extrae los partidos del feed del listado de una competición.

    Cada partido es un PA con FI= (fixture id), NA= (local), N2= (visitante),
    FD= ("Local v Visitante") y BC= (fecha/hora YYYYMMDDHHMMSS en hora de
    Reino Unido). El mismo FI se repite en los PA de las columnas de cuotas:
    nos quedamos con los registros que llevan FD (la fila de etiqueta).
    """
    fixtures = {}
    for rec in zap_records(body):
        if rec['_t'] != 'PA' or not rec.get('FI') or not rec.get('FD'):
            continue
        fi = rec['FI']
        if fi in fixtures:
            continue
        dt_local = None
        bc = rec.get('BC', '')
        if re.fullmatch(r'\d{14}', bc or ''):
            dt = datetime.strptime(bc, '%Y%m%d%H%M%S')
            if LONDON_TZ and MADRID_TZ:
                dt_local = dt.replace(tzinfo=LONDON_TZ).astimezone(MADRID_TZ)
            else:
                dt_local = dt
        fixtures[fi] = {
            'fi': fi,
            'local': (rec.get('NA') or '').strip(),
            'visitante': (rec.get('N2') or '').strip(),
            'fd': rec.get('FD', ''),
            'dt': dt_local,
        }
    return sorted(fixtures.values(), key=lambda f: (f['dt'] is None, f['dt'] or datetime.max))


def assign_matchdays(fixtures):
    """Asigna un número de jornada relativo (1 = la más próxima).

    bet365 no publica el número de jornada; se estima con la regla de que un
    equipo solo juega una vez por jornada: al reaparecer un equipo, empieza
    la siguiente jornada.
    """
    seen = set()
    matchday = 1
    for fx in fixtures:
        teams = {fx['local'], fx['visitante']}
        if teams & seen:
            matchday += 1
            seen = set()
        seen |= teams
        fx['jornada_rel'] = matchday
    return fixtures


def parse_tabs(records):
    """Pestañas de mercados de un partido: registros MA cuyo PD termina en #I<n>#."""
    tabs = []
    seen = set()
    for rec in records:
        if rec['_t'] != 'MA':
            continue
        m = re.search(r'#I(\d+)#$', rec.get('PD', ''))
        if not m:
            continue
        name = (rec.get('NA') or '').strip()
        if name and name not in seen:
            seen.add(name)
            tabs.append({'name': name, 'i': m.group(1)})
    return tabs


def coupon_rows(records, tab_name):
    """Convierte un coupon (o mini-coupon de expansión) en filas de cuotas.

    Devuelve (rows_por_mg, mgs_vacios):
      rows_por_mg: dict {clave_mg: [fila, ...]}
      mgs_vacios:  [(mg_id, mg_name), ...] grupos colapsados sin datos en el feed
    """
    rows_by_mg = {}
    empty_mgs = []
    mg_name, mg_id, mg_pa_count = None, None, 0
    ma_name = None
    co_name = None
    labels, label_recs = [], []
    odd_idx = 0

    def close_mg():
        if mg_name and mg_pa_count == 0 and mg_id:
            empty_mgs.append((mg_id, mg_name))

    for rec in records:
        t = rec['_t']
        if t == 'MG':
            close_mg()
            name = (rec.get('NA') or '').strip()
            mg_name = name or None
            mg_id = rec.get('ID') or None
            mg_pa_count = 0
            ma_name = None
            co_name = None
            labels, label_recs = [], []
            odd_idx = 0
        elif t == 'MA':
            # Las MA de la barra de pestañas (PD=...#I<n>#) no son mercados
            if re.search(r'#I\d+#$', rec.get('PD', '')):
                ma_name = None
                continue
            ma_name = (rec.get('NA') or '').strip()
            co_name = None
            odd_idx = 0
        elif t == 'CO' and mg_name:
            # sub-columna de cantidad ("1+", "2+"...): recorre las filas desde arriba
            co_name = (rec.get('NA') or '').strip()
            odd_idx = 0
        elif t == 'PA' and mg_name:
            od = rec.get('OD', '')
            if od:
                mg_pa_count += 1
                label = labels[odd_idx] if odd_idx < len(labels) else ''
                lrec = label_recs[odd_idx] if odd_idx < len(label_recs) else {}
                odd_idx += 1
                sel = (rec.get('NA') or '').strip() or label
                linea = (rec.get('HA') or rec.get('HD') or '').strip()
                if not linea:
                    cand = label or (rec.get('NA') or '').strip()
                    if re.fullmatch(r'[+\-]?\d+(?:[.,]\d+)?(?:\s*,\s*[+\-]?\d+(?:[.,]\d+)?)?', cand or ''):
                        linea = cand
                if not linea and lrec:
                    linea = (lrec.get('HA') or lrec.get('HD') or '').strip()
                key = mg_id or mg_name
                rows_by_mg.setdefault(key, []).append({
                    'mercado_id': mg_id or '',
                    'mercado': mg_name,
                    'columna': co_name or ma_name or '',
                    'seleccion': sel,
                    'linea': linea,
                    'cuota_frac': od,
                    'cuota': frac_to_dec(od),
                    'pestana': tab_name,
                })
            else:
                # PA sin cuota = etiqueta de fila (jugador, línea, equipo...)
                lbl = (rec.get('NA') or rec.get('HA') or rec.get('HD') or '').strip()
                labels.append(lbl)
                label_recs.append(rec)
    close_mg()
    return rows_by_mg, empty_mgs


def mg_names_of(records):
    return [(r.get('NA') or '').strip() for r in records if r['_t'] == 'MG']


def feed_lang(records):
    """'es' / 'en' por votación sobre los nombres de grupos; 'es' si no hay señal."""
    names = mg_names_of(records)
    score_en = sum(1 for n in names if any(h in n for h in ENGLISH_HINTS))
    score_es = sum(1 for n in names if any(h in n for h in SPANISH_HINTS))
    return 'en' if score_en > score_es else 'es'


def looks_english(records):
    return feed_lang(records) == 'en'


# ---------------------------------------------------------------------------
# Navegación
# ---------------------------------------------------------------------------

def pred_markets(comp_id):
    def pred(resp):
        url = unquote(resp.url)
        return '/matchmarketscontentapi/markets' in url and f'E{comp_id}' in url
    return pred


def pred_coupon(fi, suffix=None):
    """Respuesta de coupon del partido fi. suffix: '#F3#' (índice) o '#I5#' (pestaña)."""
    def pred(resp):
        url = unquote(resp.url)
        if 'matchbettingcontentapi' not in url or f'E{fi}' not in url:
            return False
        if suffix is None:
            return True
        m = re.search(r'[?&]pd=([^&]*)', url)
        pd = m.group(1) if m else ''
        return pd.endswith(suffix)
    return pred


def pred_expand(fi):
    def pred(resp):
        url = unquote(resp.url)
        return ('matchbettingcontentapi' in url and f'E{fi}' in url and '#S^1#' in url)
    return pred


def tab_from_url(url, tabs):
    """Identifica a qué pestaña corresponde una respuesta por el #I<n># de su pd."""
    m = re.search(r'#I(\d+)#', unquote(url))
    if m:
        for tab in tabs:
            if tab['i'] == m.group(1):
                return tab
    return tabs[0] if tabs else None


class Capture:
    def __init__(self, body, url):
        self.body = body
        self.url = url


class Bet365Session:
    def __init__(self, profile_dir, headless=False, cdp=None):
        self._pw = sync_playwright().start()
        self._attached = bool(cdp)
        if cdp:
            # Se conecta al Chrome habitual del usuario (lanzado con
            # --remote-debugging-port=9222): sesión y fingerprint 100% reales.
            self._browser = self._pw.chromium.connect_over_cdp(cdp)
            ctx = (self._browser.contexts[0] if self._browser.contexts
                   else self._browser.new_context())
            self.ctx = ctx
            self.page = ctx.new_page()
        else:
            self.ctx = self._pw.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                channel='chrome',
                headless=headless,
                viewport={'width': 1480, 'height': 900},
                locale='es-ES',
                timezone_id='Europe/Madrid',
                args=['--disable-blink-features=AutomationControlled'],
            )
            self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        self.page.set_default_timeout(20000)
        self.comp_id = None
        # tras varios reintentos de idioma fallidos se deja de insistir (la sesión
        # está anclada a inglés y el diccionario ya normaliza los nombres)
        self.en_streak = 0
        # registro pasivo de todas las respuestas de coupons (para 'Ver más')
        self._coupon_responses = []
        self.page.on('response', self._on_response)

    def _on_response(self, response):
        if 'matchbettingcontentapi' in response.url:
            self._coupon_responses.append(response)

    def close(self):
        try:
            if self._attached:
                self.page.close()   # solo la pestaña creada; el Chrome del usuario sigue
                self._browser.close()
            else:
                self.ctx.close()
        finally:
            self._pw.stop()

    def pause(self, a=0.7, b=1.6):
        time.sleep(random.uniform(a, b))

    def handle_consent(self):
        """Cierra el aviso de cookies si aparece (elige la opción más restrictiva)."""
        for text in ('Rechazar todas', 'Rechazar', 'Guardar preferencias', 'Aceptar todas', 'Aceptar'):
            try:
                btn = self.page.get_by_text(text, exact=True).first
                if btn.is_visible(timeout=1500):
                    btn.click(timeout=3000)
                    self.pause(0.5, 1.0)
                    return
            except Exception:
                continue

    def goto_listado(self, comp_id):
        self.comp_id = comp_id
        url = f'{BASE_URL}/#/AC/B1/C1/D1002/E{comp_id}/G40/'
        with self.page.expect_response(pred_markets(comp_id), timeout=45000) as ri:
            self.page.goto(url, wait_until='domcontentloaded')
            self.handle_consent()
        return ri.value.text()

    def back_to_listado(self):
        """Vuelve al listado de la competición (sin esperar respuesta de la API)."""
        self.page.evaluate(f"location.hash = '#/AC/B1/C1/D1002/E{self.comp_id}/G40/'")
        self.pause(0.9, 1.5)

    def hash_nav(self, hash_path, pred, timeout=25000):
        with self.page.expect_response(pred, timeout=timeout) as ri:
            self.page.evaluate(f"location.hash = '{hash_path}'")
        return Capture(ri.value.text(), ri.value.url)

    def _click_candidates(self, text, y_min, y_max, x_min=0):
        """Elementos visibles con ese texto exacto dentro de la zona dada."""
        out = []
        loc = self.page.get_by_text(text, exact=True)
        for i in range(min(loc.count(), 12)):
            el = loc.nth(i)
            try:
                box = el.bounding_box()
            except Exception:
                box = None
            if box and y_min <= box['y'] <= y_max and box['x'] >= x_min:
                out.append((box['y'], el))
        out.sort(key=lambda t: t[0])
        return [el for _, el in out]

    def click_capture(self, text, pred, y_min=60, y_max=420, x_min=0,
                      timeout=12000, nth=0):
        """Clic en un texto esperando la respuesta de la API. None si no hay elemento."""
        candidates = self._click_candidates(text, y_min, y_max, x_min)
        if len(candidates) <= nth:
            return None
        with self.page.expect_response(pred, timeout=timeout) as ri:
            candidates[nth].click()
        return Capture(ri.value.text(), ri.value.url)

    def click_tab(self, fi, tab, timeout=12000):
        """Clic en una pestaña del partido. None si no encuentra el elemento."""
        try:
            return self.click_capture(tab['name'], pred_coupon(fi, f"#I{tab['i']}#"),
                                      y_min=60, y_max=340, timeout=timeout)
        except PWTimeout:
            return None

    def bounce_tab(self, fi, tab, tabs):
        """Fuerza una petición fresca de `tab`: activa otra pestaña y vuelve.

        Necesario porque la SPA no re-pide la pestaña ya activa (caché) y porque
        una respuesta en inglés solo se corrige con una petición nueva.
        """
        other = next((t for t in tabs if t['i'] != tab['i'] and
                      norm_txt(t['name']) not in EXCLUDED_TABS and
                      norm_txt(t['name']) not in HASH_FIRST_TABS), None)
        if other:
            try:
                self.click_tab(fi, other, timeout=6000)
            except Exception:
                pass
            self.pause(0.4, 0.8)
        return self.click_tab(fi, tab, timeout=9000)

    def recover_match(self, fi):
        """La SPA se degrada tras muchas navegaciones y sirve cuerpos vacíos:
        recarga la página completa sobre el partido para reiniciar el estado."""
        try:
            self.page.evaluate(f"location.hash = '#/AC/B1/C1/D8/E{fi}/F3/'")
            with self.page.expect_response(pred_coupon(fi), timeout=35000) as ri:
                self.page.reload(wait_until='domcontentloaded')
                self.handle_consent()
            self.pause(1.5, 2.5)
            return Capture(ri.value.text(), ri.value.url)
        except PWTimeout:
            return None

    def expand_capture(self, text, pred, timeout=6000):
        """Clic en la cabecera de un grupo colapsado; devuelve el mini-coupon o None."""
        candidates = self._click_candidates(text, 230, 20000)
        if not candidates:
            return None
        try:
            with self.page.expect_response(pred, timeout=timeout) as ri:
                candidates[0].click()
            return Capture(ri.value.text(), ri.value.url)
        except PWTimeout:
            return None

    def ver_mas_capture(self, pred, max_clicks=40, settle_ms=800):
        """Pulsa los botones 'Ver más' visibles; devuelve los cuerpos capturados.

        Muchos 'Ver más' solo despliegan filas que ya venían en el feed (sin
        petición). En vez de esperar un timeout por cada uno, se pulsan y se
        recogen las respuestas nuevas del registro pasivo de la sesión.
        """
        mark = len(self._coupon_responses)
        clicked = 0
        for _ in range(max_clicks):
            candidates = self._click_candidates('Ver más', 230, 20000)
            if not candidates:
                break
            try:
                candidates[0].click(timeout=4000)
                clicked += 1
            except Exception as e:
                log_error(f"ver_mas: {e}")
                break
            self.page.wait_for_timeout(random.uniform(250, 450))
        if not clicked:
            return []
        self.page.wait_for_timeout(settle_ms)
        bodies = []
        for resp in self._coupon_responses[mark:]:
            try:
                if pred(resp):
                    bodies.append(resp.text())
            except Exception:
                pass
        return bodies


def open_match(session, fx, fixtures, idx):
    """Abre un partido clicando su fila en el listado (fallback: cambio de hash)."""
    fi = fx['fi']
    # nº de veces que el nombre del local aparece antes en el listado (filas duplicadas)
    occ = sum(1 for f in fixtures[:idx] if fx['local'] in (f['local'], f['visitante']))
    session.back_to_listado()
    try:
        cap = session.click_capture(fx['local'], pred_coupon(fi), y_min=140,
                                    y_max=20000, x_min=300, timeout=15000, nth=occ)
        if cap:
            return cap
    except PWTimeout:
        pass
    try:
        return session.hash_nav(f'#/AC/B1/C1/D8/E{fi}/F3/', pred_coupon(fi), timeout=25000)
    except PWTimeout:
        return None


# ---------------------------------------------------------------------------
# Flujo principal
# ---------------------------------------------------------------------------

def scrape_match(session, fx, fixtures, idx, tabs_filter, full, rapido,
                 market_dict=None, bar=None):
    """Scrapea todas las pestañas de mercados de un partido. Devuelve filas CSV."""
    fi = fx['fi']
    all_rows = {}   # (pestana, clave_mg) -> [rows]
    market_dict = market_dict if market_dict is not None else {}

    def note(msg):
        if bar:
            bar.set_postfix_str(f"{fx['local'][:16]} · {msg}"[:46])

    def merge(tab_name, body):
        records = zap_records(body)
        rows_by_mg, empty = coupon_rows(records, tab_es(tab_name))
        lang = feed_lang(records)
        for key, rows in rows_by_mg.items():
            for row in rows:
                row['idioma'] = lang
                if lang == 'es':
                    # aprender el nombre español de este mercado para el futuro
                    # (verificando el nombre individual: hay feeds con mezcla)
                    if row['mercado_id'] and not any(h in row['mercado'] for h in ENGLISH_HINTS):
                        market_dict[row['mercado_id']] = row['mercado']
                else:
                    # normalizar con lo aprendido en feeds anteriores en español
                    known = market_dict.get(row['mercado_id'])
                    if known:
                        row['mercado'] = known
                        row['idioma'] = 'es'
                    row['columna'] = COL_ES.get(row['columna'], row['columna'])
                    row['seleccion'] = SEL_ES.get(row['seleccion'], row['seleccion'])
            all_rows[(tab_es(tab_name), key)] = rows
        return records, empty

    note('abriendo')
    session._coupon_responses.clear()
    cap = open_match(session, fx, fixtures, idx)
    records = zap_records(cap.body) if cap else []
    tabs = parse_tabs(records)
    if not tabs:
        # feed vacío o degradado: recargar la página completa y reintentar
        note('recargando')
        cap = session.recover_match(fx['fi'])
        records = zap_records(cap.body) if cap else []
        tabs = parse_tabs(records)
    if not tabs:
        log_error(f"{fx['fd']}: coupon inicial sin pestañas (feed vacío)")
        return []

    # El coupon inicial corresponde a la pestaña que bet365 restaura (no siempre
    # "Populares"); identificarla por la URL de la respuesta.
    index_tab = tab_from_url(cap.url, tabs)
    index_english = looks_english(records)
    empty0 = []
    if not index_english:
        _, empty0 = merge(index_tab['name'], cap.body)

    wanted = []
    for tab in tabs:
        if tab['i'] == index_tab['i']:
            continue
        if norm_txt(tab['name']) in EXCLUDED_TABS:
            continue
        if tabs_filter:
            targets = [norm_txt(tab_es(w)) if w in TAB_ES else norm_txt(w) for w in tabs_filter]
            name_es = norm_txt(tab_es(tab['name']))
            if not any(t in name_es or name_es in t for t in targets):
                continue
        wanted.append(tab)

    pending = []
    if full and empty0:
        pending.append((index_tab, empty0))

    for tab in wanted:
        session.pause()
        note(tab_es(tab['name']))
        try:
            if norm_txt(tab['name']) in HASH_FIRST_TABS:
                tcap = session.hash_nav(f"#/AC/B1/C1/D8/E{fi}/F3/I{tab['i']}/",
                                        pred_coupon(fi, f"#I{tab['i']}#"))
            else:
                tcap = session.click_tab(fi, tab)
                if tcap is None:
                    tcap = session.bounce_tab(fi, tab, tabs)
                if tcap is None:
                    tcap = session.hash_nav(f"#/AC/B1/C1/D8/E{fi}/F3/I{tab['i']}/",
                                            pred_coupon(fi, f"#I{tab['i']}#"))
            if tcap is not None and not tcap.body:
                # feed vacío a mitad de partido: reiniciar el estado y repetir
                note('recargando')
                session.recover_match(fi)
                tcap = session.click_tab(fi, tab) or session.bounce_tab(fi, tab, tabs)
                if tcap is None or not tcap.body:
                    log_error(f"{fx['fd']}: pestaña {tab['name']} vacía tras recarga")
                    continue
            if looks_english(zap_records(tcap.body)) and session.en_streak < 3:
                session.pause(0.6, 1.2)
                retry = session.bounce_tab(fi, tab, tabs)
                if retry and not looks_english(zap_records(retry.body)):
                    tcap = retry
                    session.en_streak = 0
                else:
                    session.en_streak += 1
                    log_error(f"{fx['fd']}: pestaña {tab['name']} en inglés")
            _, empty = merge(tab['name'], tcap.body)
            if full and empty:
                pending.append((tab, empty))
            if not rapido:
                for extra in session.ver_mas_capture(pred_coupon(fi)):
                    merge(tab['name'], extra)
        except PWTimeout:
            log_error(f"{fx['fd']}: timeout en pestaña {tab['name']}")
        except Exception as e:
            log_error(f"{fx['fd']}: pestaña {tab['name']}: {e}")

    # Si el coupon inicial llegó en inglés, re-pedirlo ahora con un clic fresco
    if index_english and session.en_streak >= 3:
        # sesión anclada a inglés: usar el coupon tal cual (el diccionario normaliza)
        _, empty0 = merge(index_tab['name'], cap.body)
        if full and empty0:
            pending.append((index_tab, empty0))
        index_english = False
    if index_english:
        note(f"reintento {tab_es(index_tab['name'])}")
        try:
            retry = session.bounce_tab(fi, index_tab, tabs)
            if retry:
                if looks_english(zap_records(retry.body)):
                    log_error(f"{fx['fd']}: pestaña {index_tab['name']} en inglés")
                _, empty0 = merge(index_tab['name'], retry.body)
                if full and empty0:
                    pending.append((index_tab, empty0))
                if not rapido:
                    for extra in session.ver_mas_capture(pred_coupon(fi)):
                        merge(index_tab['name'], extra)
        except Exception as e:
            log_error(f"{fx['fd']}: reintento índice: {e}")

    # Grupos colapsados: volver a cada pestaña y expandirlos. El servidor devuelve
    # vacío para grupos sin datos (props capados cerca del inicio del partido):
    # eso no se reintenta; solo si se encadenan muchos vacíos (sesión degradada)
    # se recarga la página una vez.
    if full:
        empty_streak = 0
        for tab, empties in pending:
            try:
                session.click_tab(fi, tab, timeout=6000)
            except Exception:
                pass
            for mg_id, mg_name in empties:
                note(f'expandir {mg_name[:20]}')
                try:
                    session.pause(0.4, 0.9)
                    ecap = session.expand_capture(mg_name, pred_expand(fi))
                    if ecap is not None and not ecap.body and empty_streak >= 4:
                        note('recargando')
                        session.recover_match(fi)
                        session.click_tab(fi, tab, timeout=6000)
                        session.pause(0.4, 0.9)
                        empty_streak = 0
                        ecap = session.expand_capture(mg_name, pred_expand(fi))
                    if ecap and ecap.body:
                        empty_streak = 0
                        merge(tab['name'], ecap.body)
                    else:
                        empty_streak += 1
                        log_error(f"{fx['fd']}: expandir '{mg_name}': sin datos")
                except Exception as e:
                    log_error(f"{fx['fd']}: expandir '{mg_name}': {e}")
            if not rapido:
                try:
                    for extra in session.ver_mas_capture(pred_coupon(fi)):
                        merge(tab['name'], extra)
                except Exception:
                    pass

    # Aplanar + deduplicar (mismo mercado repetido en varias pestañas)
    seen = set()
    flat = []
    for (tab_name, _key), rows in all_rows.items():
        for row in rows:
            k = (row['mercado'], row['columna'], row['seleccion'], row['linea'], row['cuota_frac'])
            if k in seen:
                continue
            seen.add(k)
            flat.append(row)
    return flat


def scrape_league(args):
    if args.comp_id:
        comp_id = args.comp_id
        league_key = re.sub(r'\W+', '', (args.league_name or f'comp{args.comp_id}')).lower()
        league_name = args.league_name or f'Competición {args.comp_id}'
    else:
        cfg = LEAGUES.get(args.league)
        if not cfg or not cfg.get('comp_id'):
            print(f"❌ Liga '{args.league}' sin comp_id configurado. Usa --comp-id "
                  f"(navega a la liga en bet365.es y copia el número tras E en la URL).")
            sys.exit(1)
        comp_id, league_key, league_name = cfg['comp_id'], args.league, cfg['name']

    market_dict = {}
    if os.path.exists(MARKET_NAMES_FILE):
        try:
            with open(MARKET_NAMES_FILE, encoding='utf-8') as f:
                market_dict = json.load(f)
        except Exception:
            market_dict = {}

    session = Bet365Session(args.perfil, headless=args.headless, cdp=args.attach)
    scrape_ts = datetime.now().isoformat(timespec='seconds')
    try:
        print(f"🌐 Abriendo bet365.es - {league_name} ...")
        body = session.goto_listado(comp_id)
        fixtures = assign_matchdays(parse_fixture_list(body))
        if not fixtures:
            print("❌ No se han encontrado partidos en el listado.")
            sys.exit(1)

        if args.jornada:
            fixtures = [f for f in fixtures if f['jornada_rel'] == args.jornada]
        if args.partidos:
            fixtures = fixtures[:args.partidos]

        print(f"📋 {len(fixtures)} partidos:")
        for fx in fixtures:
            when = fx['dt'].strftime('%d %b %H:%M') if fx['dt'] else '¿?'
            print(f"   J{fx['jornada_rel']}  {when}  {fx['local']} v {fx['visitante']}")

        all_rows = []
        with tqdm(total=len(fixtures), desc='Partidos', unit='partido') as bar:
            for idx, fx in enumerate(fixtures):
                session.pause(1.2, 2.4)
                try:
                    rows = scrape_match(session, fx, fixtures, idx,
                                        args.tabs, not args.rapido, args.rapido,
                                        market_dict, bar)
                except PWTimeout:
                    log_error(f"{fx['fd']}: timeout abriendo el partido")
                    rows = []
                except Exception as e:
                    log_error(f"{fx['fd']}: {e}")
                    rows = []
                when = fx['dt'] if fx['dt'] else None
                for row in rows:
                    row.update({
                        'scrape_ts': scrape_ts,
                        'casa': 'bet365',
                        'liga': league_name,
                        'jornada_rel': fx['jornada_rel'],
                        'fecha': when.strftime('%Y-%m-%d') if when else '',
                        'hora': when.strftime('%H:%M') if when else '',
                        'local': fx['local'],
                        'visitante': fx['visitante'],
                        'fixture_id': fx['fi'],
                    })
                all_rows.extend(rows)
                try:
                    ensure_parent_dir(MARKET_NAMES_FILE)
                    with open(MARKET_NAMES_FILE, 'w', encoding='utf-8') as f:
                        json.dump(market_dict, f, ensure_ascii=False, indent=1)
                except Exception:
                    pass
                bar.update(1)
                bar.set_postfix_str(f"{fx['local'][:16]} ✓ {len(rows)} cuotas")

        if not all_rows:
            print("❌ No se ha extraído ninguna cuota. Revisa logs/bet365_errors.log")
            sys.exit(1)

        # normalización retroactiva: lo aprendido al final renombra lo del principio
        for row in all_rows:
            if row.get('idioma') == 'en':
                known = market_dict.get(row.get('mercado_id', ''))
                if known:
                    row['mercado'] = known
                    row['idioma'] = 'es'
                    row['columna'] = COL_ES.get(row['columna'], row['columna'])
                    row['seleccion'] = SEL_ES.get(row['seleccion'], row['seleccion'])

        out = args.out or os.path.join(
            DATA_DIR, f"cuotas_bet365_{league_key}_{datetime.now():%Y-%m-%d_%H%M}.csv")
        ensure_parent_dir(out)
        fieldnames = ['scrape_ts', 'casa', 'liga', 'jornada_rel', 'fecha', 'hora',
                      'local', 'visitante', 'fixture_id', 'pestana', 'mercado_id', 'mercado',
                      'columna', 'seleccion', 'linea', 'cuota', 'cuota_frac', 'idioma']
        with open(out, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)

        n_matches = len({r['fixture_id'] for r in all_rows})
        n_markets = len({(r['fixture_id'], r['mercado']) for r in all_rows})
        n_en = sum(1 for r in all_rows if r.get('idioma') == 'en')
        print(f"\n✅ {out}")
        print(f"   {n_matches} partidos · {n_markets} mercados · {len(all_rows)} cuotas")
        if n_en:
            print(f"   ⚠️ {n_en} cuotas con nombres en inglés (columna 'idioma'). Para forzar")
            print(f"      español: cierra Chrome, relánzalo con --remote-debugging-port=9222")
            print(f"      y usa: python3 bet365_scraper.py cuotas --attach ... (ver README)")
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description='Scraper de cuotas de bet365.es')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('cuotas', help='Extraer cuotas de una competición')
    p.add_argument('--league', choices=sorted(LEAGUES.keys()), default='spain')
    p.add_argument('--comp-id', help='ID de competición de bet365 (número tras E en la URL)')
    p.add_argument('--league-name', help='Nombre de la liga (con --comp-id)')
    p.add_argument('--jornada', type=int, help='Solo la jornada relativa N (1 = próxima)')
    p.add_argument('--partidos', type=int, help='Límite de partidos (para pruebas)')
    p.add_argument('--tabs', type=lambda s: [x.strip() for x in s.split(',') if x.strip()],
                   help='Pestañas a extraer, ej: "Resultado,Goles,Córners" (por defecto todas)')
    p.add_argument('--rapido', action='store_true',
                   help="No expandir grupos colapsados ni pulsar 'Ver más' (más rápido, "
                        "pero pierde mercados como Método del gol o los hándicaps)")
    p.add_argument('--attach', nargs='?', const='http://127.0.0.1:9222', default=None,
                   help='Usar tu Chrome habitual vía CDP (lánzalo antes con '
                        '--remote-debugging-port=9222). Sesión 100%% real, feed en español')
    p.add_argument('--headless', action='store_true',
                   help='Sin ventana (mayor riesgo de bloqueo, no recomendado)')
    p.add_argument('--perfil', default=DEFAULT_PROFILE,
                   help=f'Directorio del perfil de Chrome (def: {DEFAULT_PROFILE})')
    p.add_argument('--out', help='Fichero CSV de salida')

    sub.add_parser('ligas', help='Ver ligas configuradas')

    args = parser.parse_args()
    if args.cmd == 'ligas':
        for key, cfg in LEAGUES.items():
            status = f"E{cfg['comp_id']}" if cfg.get('comp_id') else '— (usa --comp-id)'
            print(f"  {key:10s} {cfg['name']:28s} {status}")
        return
    scrape_league(args)


if __name__ == '__main__':
    main()
