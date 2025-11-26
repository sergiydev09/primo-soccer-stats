# Soccer Stats Scraper

Scraper paralelo optimizado para extraer estadísticas de jugadores de las principales ligas europeas de fútbol.

## Ligas Soportadas

- ✅ **España**: Primera División (La Liga)
- ✅ **Inglaterra**: Premier League
- ✅ **Alemania**: Bundesliga
- ✅ **Italia**: Serie A
- ✅ **Francia**: Ligue 1

## Instalación

```bash
pip3 install -r requirements.txt
```

## Uso

### Una liga específica

```bash
# España
python3 scraper.py all --league spain

# Inglaterra
python3 scraper.py all --league england

# Alemania
python3 scraper.py all --league germany

# Italia
python3 scraper.py all --league italy

# Francia
python3 scraper.py all --league france
```

### Múltiples ligas

```bash
# España + Inglaterra
python3 scraper.py all --league both

# Todas las ligas
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

Cada liga genera dos archivos:

| Liga | URLs | CSV |
|------|------|-----|
| España | `match_urls_spain.txt` | `BBDD_partidos_spain.csv` |
| Inglaterra | `match_urls_england.txt` | `BBDD_partidos_england.csv` |
| Alemania | `match_urls_germany.txt` | `BBDD_partidos_germany.csv` |
| Italia | `match_urls_italy.txt` | `BBDD_partidos_italy.csv` |
| Francia | `match_urls_france.txt` | `BBDD_partidos_france.csv` |

## Estructura del CSV

Cada CSV contiene:
- **Información del partido**: fecha, jornada, árbitro
- **Equipos**: local, visitante
- **Estadísticas de jugadores**: goles, asistencias, pases, tiros, tarjetas, etc.

## Características

- ✅ Procesamiento paralelo (8 workers por defecto)
- ✅ Barra de progreso en tiempo real
- ✅ Resumen ordenado por fecha
- ✅ Manejo de errores con logging
- ✅ ~65-77 segundos por 130 partidos

## Requisitos

- Python 3.8+
- Chrome/Chromium browser
- Dependencias en `requirements.txt`
