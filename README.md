# ⚽ Primera División Soccer Stats Scraper

Extrae estadísticas completas de 120 partidos de Primera División 2025-2026.

## 🚀 Instalación

```bash
git clone https://github.com/sergiydev09/primo-soccer-stats.git
cd primo-soccer-stats
pip install -r requirements.txt
brew install chromedriver  # Mac
```

## 💻 Uso

```bash
# Extraer URLs de partidos (~2 min)
python3 scraper.py urls

# Extraer datos de todos los partidos (~20 min)
python3 scraper.py data

# O hacer todo de una vez (~22 min)
python3 scraper.py all
```

## 📊 Resultado

Genera `BBDD_partidos_completo.csv` con:
- **7,576 filas** (jugadores)
- **23 columnas** (datos del partido + 15 estadísticas)
- **120 partidos** completos

### Estadísticas por jugador:
Goals, Assists, Red/Yellow cards, Shots, Passes, Tackles, Corners, Crosses, Blocked shots, Fouls, Offsides, Saves

## 📋 Requisitos

- Python 3.7+
- Chrome + ChromeDriver
- selenium, beautifulsoup4

## 📄 Licencia

Open source - Uso libre
