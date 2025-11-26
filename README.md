# Soccer Stats Scraper

Scraper paralelo optimizado para extraer estadísticas de jugadores de las principales ligas y competiciones europeas de fútbol.

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

Cada competición genera dos archivos:

| Competición | URLs | CSV |
|-------------|------|-----|
| La Liga | `match_urls_spain.txt` | `BBDD_partidos_spain.csv` |
| Segunda División | `match_urls_spain2.txt` | `BBDD_partidos_spain2.csv` |
| Premier League | `match_urls_england.txt` | `BBDD_partidos_england.csv` |
| Bundesliga | `match_urls_germany.txt` | `BBDD_partidos_germany.csv` |
| Serie A | `match_urls_italy.txt` | `BBDD_partidos_italy.csv` |
| Ligue 1 | `match_urls_france.txt` | `BBDD_partidos_france.csv` |
| Champions League | `match_urls_ucl.txt` | `BBDD_partidos_ucl.csv` |
| Europa League | `match_urls_uel.txt` | `BBDD_partidos_uel.csv` |

## Estructura del CSV

Cada CSV contiene:
- **Información del partido**: fecha, jornada, árbitro
- **Equipos**: local, visitante
- **Estadísticas de jugadores**: goles, asistencias, pases, tiros, tarjetas, etc.

## Características

- ✅ 8 competiciones soportadas
- ✅ Procesamiento paralelo (8 workers por defecto)
- ✅ Barra de progreso en tiempo real
- ✅ Resumen ordenado por fecha
- ✅ Manejo de errores con logging
- ✅ ~65-77 segundos por 130 partidos

## Nota sobre Competiciones Europeas

Las competiciones europeas (UCL, UEL) pueden tener tiempos de carga más lentos debido a JavaScript más pesado en las páginas. Se recomienda usarlas con paciencia o aumentar los timeouts si es necesario.

## Requisitos

- Python 3.8+
- Chrome/Chromium browser
- Dependencias en `requirements.txt`
