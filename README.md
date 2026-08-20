# Soccer Stats Scraper

Scraper paralelo optimizado para extraer estadísticas de jugadores de las principales ligas y competiciones europeas de fútbol, temporada a temporada.

## Competiciones Soportadas

### Ligas Nacionales
- ✅ **España**: Primera División (La Liga)
- ✅ **España**: Segunda División
- ✅ **Inglaterra**: Premier League
- ✅ **Alemania**: Bundesliga
- ✅ **Italia**: Serie A
- ✅ **Francia**: Ligue 1

### Competiciones Europeas
- ✅ **UEFA Champions League** (UCL)
- ✅ **UEFA Europa League** (UEL)

## Instalación

```bash
pip3 install -r requirements.txt
```

## Uso

Por defecto se usa la **temporada en curso** (el corte es julio: a partir del 1 de julio de 2026 la temporada por defecto es `2026-2027`).

### Una competición específica

```bash
# Ligas nacionales
python3 scraper.py all --league spain      # La Liga
python3 scraper.py all --league spain2     # Segunda División
python3 scraper.py all --league england    # Premier League
python3 scraper.py all --league germany    # Bundesliga
python3 scraper.py all --league italy      # Serie A
python3 scraper.py all --league france     # Ligue 1

# Competiciones europeas
python3 scraper.py all --league ucl        # Champions League
python3 scraper.py all --league uel        # Europa League
```

### Múltiples competiciones

```bash
# España + Inglaterra
python3 scraper.py all --league both

# Todas las competiciones (8 en total)
python3 scraper.py all --league all
```

### Temporadas

```bash
# Temporada en curso (por defecto)
python3 scraper.py all --league all

# Una temporada concreta (acepta 2025-2026, 2025/2026 o 2025)
python3 scraper.py all --league spain --season 2025-2026

# Ver qué temporadas hay disponibles en la web
python3 scraper.py seasons --league all
```

Cada temporada se guarda en sus propios archivos, así que las anteriores nunca se
sobrescriben.

**Cambio de temporada**: no hay que editar nada. Los IDs de temporada de Opta ya
están configurados para 2025-2026 y 2026-2027 en `LEAGUES`, y cualquier temporada
posterior se descubre automáticamente leyendo el selector de temporada de la propia
web. Los IDs descubiertos se cachean en `seasons_cache.json` para no repetir la
búsqueda en cada ejecución.

### Opciones avanzadas

```bash
# Limitar partidos (para pruebas)
python3 scraper.py all --league germany --limit 10

# Especificar workers
python3 scraper.py all --league italy --workers 4

# Solo URLs
python3 scraper.py urls --league france

# Solo datos (requiere URLs previas)
python3 scraper.py data --league spain
```

## Archivos Generados

Cada competición y temporada genera dos archivos, con el patrón
`BBDD_partidos_<liga>_<temporada>.csv` y `match_urls_<liga>_<temporada>.txt`:

| Competición | Clave | URLs | CSV |
|-------------|-------|------|-----|
| La Liga | `spain` | `match_urls_spain_2026-2027.txt` | `BBDD_partidos_spain_2026-2027.csv` |
| Segunda División | `spain2` | `match_urls_spain2_2026-2027.txt` | `BBDD_partidos_spain2_2026-2027.csv` |
| Premier League | `england` | `match_urls_england_2026-2027.txt` | `BBDD_partidos_england_2026-2027.csv` |
| Bundesliga | `germany` | `match_urls_germany_2026-2027.txt` | `BBDD_partidos_germany_2026-2027.csv` |
| Serie A | `italy` | `match_urls_italy_2026-2027.txt` | `BBDD_partidos_italy_2026-2027.csv` |
| Ligue 1 | `france` | `match_urls_france_2026-2027.txt` | `BBDD_partidos_france_2026-2027.csv` |
| Champions League | `ucl` | `match_urls_ucl_2026-2027.txt` | `BBDD_partidos_ucl_2026-2027.csv` |
| Europa League | `uel` | `match_urls_uel_2026-2027.txt` | `BBDD_partidos_uel_2026-2027.csv` |

## Estructura del CSV

Cada CSV contiene:
- **Información del partido**: fecha, jornada, árbitro
- **Equipos**: local, visitante
- **Estadísticas de jugadores**: goles, asistencias, pases, tiros, tarjetas, etc.

> Nota: la columna `Jornada` se queda vacía porque la web de Opta no publica el número
> de jornada en la ficha del partido.

## Verificar los datos

```bash
# Fechas presentes en una BBDD ya generada
python3 verify_dates.py --league spain
python3 verify_dates.py --league ucl --season 2025-2026
```

## Características

- ✅ 8 competiciones soportadas
- ✅ Cualquier temporada, con detección automática de la temporada en curso
- ✅ Archivos separados por temporada (no se pisan datos históricos)
- ✅ Procesamiento paralelo (8 workers por defecto)
- ✅ Barra de progreso en tiempo real
- ✅ Resumen ordenado por fecha
- ✅ Manejo de errores con logging

## Nota sobre Competiciones Europeas

Las competiciones europeas (UCL, UEL) pueden tener tiempos de carga más lentos debido a JavaScript más pesado en las páginas. Se recomienda usarlas con paciencia o aumentar los timeouts si es necesario.

Además, al principio de temporada las competiciones europeas todavía no han disputado
partidos (la fase liga arranca en septiembre): el scraper avisa y no genera CSV cuando
no hay partidos.

## Requisitos

- Python 3.8+
- Chrome/Chromium browser
- Dependencias en `requirements.txt`
