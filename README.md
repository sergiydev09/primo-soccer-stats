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

## Estructura de archivos

Todos los outputs se guardan organizados bajo `data/`, `cache/` y `logs/`:

```
Primo/
├── scraper.py               # estadísticas de jugadores (Opta)
├── bet365_scraper.py        # cuotas de apuestas (bet365)
├── verify_dates.py
├── data/
│   ├── opta/                # BBDD_partidos_<liga>_<temporada>.csv
│   │   └── urls/            # match_urls_<liga>_<temporada>.txt (intermedios)
│   └── cuotas/
│       └── bet365/          # cuotas_bet365_<liga>_<fecha>.csv
├── cache/                   # seasons_cache.json, bet365_markets_es.json
└── logs/                    # scraper_errors.log, bet365_errors.log
```

Cada competición y temporada de Opta genera `data/opta/BBDD_partidos_<liga>_<temporada>.csv`
(y sus URLs intermedias en `data/opta/urls/`), con las claves: `spain`, `spain2`,
`england`, `germany`, `italy`, `france`, `ucl`, `uel`.

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

---

# Scraper de cuotas de bet365 (`bet365_scraper.py`)

Extrae, para cada partido listado de una competición en bet365.es, todos los
mercados de apuestas y sus cuotas, y lo vuelca a un CSV por jornadas.

## Cómo funciona

Playwright lanza un **Chrome real** (con un perfil persistente propio en
`~/.bet365_scraper_profile`) y navega por bet365 **como un usuario** (clics).
No replica llamadas a la API (llevan tokens de un solo uso): captura las
respuestas que la propia web hace a sus APIs internas y parsea su feed
propietario. Verás abrirse una ventana de Chrome durante el scraping: es normal.

## Uso

```bash
pip3 install playwright   # una vez

# La Liga: todos los partidos listados (jornada próxima + adelantos), todas las pestañas
python3 bet365_scraper.py cuotas --league spain

# Solo la próxima jornada
python3 bet365_scraper.py cuotas --league spain --jornada 1

# Solo algunas pestañas de mercados
python3 bet365_scraper.py cuotas --league spain --tabs "Resultado,Goles,Córners"

# Modo rápido: sin expandir grupos colapsados ni 'Ver más' (pierde mercados
# como Método del gol, Multicórner o los hándicaps de córners)
python3 bet365_scraper.py cuotas --league spain --rapido

# Pruebas rápidas
python3 bet365_scraper.py cuotas --league spain --partidos 2 --rapido

# Otra competición cualquiera: navega a ella en bet365.es y copia el número
# que va tras la "E" en la URL (#/AC/B1/C1/D1002/E135650998/G40/)
python3 bet365_scraper.py cuotas --comp-id 135650998 --league-name "La Liga"
```

## CSV generado

`data/cuotas/bet365/cuotas_bet365_<liga>_<fecha>.csv` con una fila por cuota:

| columna | contenido |
|---|---|
| `scrape_ts` | momento de la captura (las cuotas cambian con el tiempo) |
| `jornada_rel` | jornada relativa estimada (1 = la más próxima) |
| `fecha`, `hora` | del partido, en hora peninsular |
| `local`, `visitante`, `fixture_id` | partido (el id es estable en bet365) |
| `pestana` | pestaña de la ficha (Resultado, Goles, Córners, Crear apuesta...) |
| `mercado_id`, `mercado` | grupo de mercado (id estable entre partidos e idiomas) |
| `columna` | columna dentro del mercado (Más de / Menos de / Anotará...) |
| `seleccion` | selección o jugador o línea |
| `linea` | línea/hándicap si aplica (2.5, -1.0, 9.5...) |
| `cuota` | decimal; `cuota_frac` fraccional original |
| `idioma` | es/en del nombre del mercado (ver nota) |

## Nota sobre el idioma

El servidor de bet365 sirve los nombres de mercados a veces en español y a veces
en inglés (depende del "pod" que atienda la sesión, cambia con el tiempo). El
scraper lo compensa: aprende los nombres en español (por id de mercado, estable)
en `bet365_markets_es.json` y renombra automáticamente lo que llegue en inglés.
El diccionario viene sembrado con los ~35 mercados principales y mejora solo con
el uso. Las filas que aún no se hayan podido traducir quedan marcadas con
`idioma=en`; el `mercado_id` es siempre estable para cruzar datos.

## Jornadas

bet365 no publica el número de jornada: `jornada_rel` se estima con la regla de
que un equipo solo juega una vez por jornada (al repetirse un equipo, empieza la
siguiente). Para el número absoluto, cruza fecha+equipos con tu BBDD de Opta.

## Consejos

- bet365 lista normalmente la jornada próxima completa y algunos adelantos.
  Ejecuta el scraper cada semana (p. ej. martes/miércoles) para cada jornada.
- Por defecto se captura todo: pestañas, grupos colapsados (Método del gol,
  hándicaps de córners...) y listas 'Ver más'. En mercados de jugadores con
  cantidades (remates 1+/2+/3+...), la cantidad va en la columna `columna`.
- Ritmo: el scraper mete pausas aleatorias entre clics; una jornada completa
  tarda ~30-45 min (`--rapido` la baja a ~15). No lo aceleres: es una web con
  protección anti-bot y conviene parecer humano.
- Si bet365 mostrara un captcha/challenge en la ventana, resuélvelo a mano una
  vez; el perfil persistente lo recuerda.
- Uso personal: respeta los términos del sitio y no redistribuyas los datos.
