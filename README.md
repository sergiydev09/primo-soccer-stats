# ⚽ Extractor de Datos de Partidos - Primera División

Herramienta automatizada para extraer estadísticas completas de jugadores y árbitros de todos los partidos de Primera División 2025-2026 desde [Opta Player Stats](https://optaplayerstats.statsperform.com).

## 🎯 ¿Qué hace?

Extrae **todos los datos** de los 120 partidos de la temporada y los convierte en un archivo CSV listo para análisis:

- ✅ **7,576 registros** de jugadores
- ✅ **23 columnas** de datos por jugador
- ✅ **15 estadísticas** detalladas (goles, asistencias, tarjetas, tiros, pases, etc.)
- ✅ Información de árbitros y equipos
- ✅ ~20 minutos de ejecución total

## 📊 Datos Extraídos

Por cada jugador de cada partido obtendrás:

### Información del Partido
- Número de partido (1-120)
- ID único del partido
- Árbitro
- Equipo local y visitante
- Equipo del jugador

### Estadísticas del Jugador (15 métricas)
- Goals (Goles)
- Assists (Asistencias)
- Red cards (Tarjetas rojas)
- Yellow cards (Tarjetas amarillas)
- Shots (Tiros)
- Shots on target (Tiros a puerta)
- Passes (Pases)
- Tackles (Entradas)
- Corners won (Córners ganados)
- Crosses (Centros)
- Blocked shots (Tiros bloqueados)
- Fouls conceded (Faltas cometidas)
- Fouls won (Faltas recibidas)
- Offsides (Fueras de juego)
- Saves (Paradas)

## 🚀 Inicio Rápido

### Requisitos Previos

- Python 3.7+
- Google Chrome
- ChromeDriver

### Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/TU_USUARIO/primo-soccer-stats.git
cd primo-soccer-stats

# 2. Instalar dependencias
pip install selenium beautifulsoup4

# 3. Instalar ChromeDriver
# Mac:
brew install chromedriver

# Windows: Descarga de https://chromedriver.chromium.org/
```

### Uso

#### Opción 1: Script Automático (Mac/Linux)

```bash
./INICIO_FACIL.sh
```

Selecciona la opción 3 para ejecutar todo automáticamente.

#### Opción 2: Paso a Paso

```bash
# Verificar requisitos
python3 verificar_requisitos.py

# Extraer URLs de partidos (~2 min)
python3 extract_match_urls.py

# Extraer datos de todos los partidos (~20 min)
python3 extract_match_data_v2.py

# ¡Listo! Abre BBDD_partidos_completo.csv en Excel
```

## 📁 Estructura del Proyecto

```
.
├── LEEME_PRIMERO.txt              # Guía rápida de inicio
├── GUIA_FACIL.md                  # Documentación completa
├── README.md                      # Este archivo
├── requirements.txt               # Dependencias Python
├── .gitignore                     # Archivos ignorados por Git
│
├── INICIO_FACIL.sh                # Script automático (Mac/Linux)
├── verificar_requisitos.py        # Verificador de requisitos
│
├── extract_match_urls.py          # Paso 1: Extraer URLs
├── extract_match_data_v2.py       # Paso 2: Extraer datos
├── extract_match_urls_simple.py   # Alternativa ligera (requests)
│
└── test_extraction.py             # Script de prueba
```

## 📖 Documentación

- **[LEEME_PRIMERO.txt](LEEME_PRIMERO.txt)** - Empieza aquí para una guía super rápida
- **[GUIA_FACIL.md](GUIA_FACIL.md)** - Guía completa con instrucciones detalladas paso a paso
- **Verificación de requisitos**: `python3 verificar_requisitos.py`

## 🔧 Solución de Problemas

### "Command not found: python3"
**Solución:** En Windows usa `python` en lugar de `python3`

### "ModuleNotFoundError: No module named 'selenium'"
**Solución:**
```bash
pip install selenium beautifulsoup4
```

### "ChromeDriver not found"
**Mac:**
```bash
brew install chromedriver
```

**Windows:** Descarga de https://chromedriver.chromium.org/

### Más ayuda
Consulta [GUIA_FACIL.md](GUIA_FACIL.md) para soluciones detalladas a problemas comunes.

## 📋 Ejemplo de Salida

El script genera `BBDD_partidos_completo.csv`:

```csv
Aux,Jornada,ID_PARTIDO,Arbitro,Equipo_local,Equipo_Visitante,Equipo_Jugador,Jugador,Goals,Assists,...
1,,10d1132abu0fa9xolj05top3o,Isidro Díaz de Mera Escuderos,Athletic Club,Getafe CF,Athletic Club,Íñigo Lekue,0,0,...
1,,10d1132abu0fa9xolj05top3o,Isidro Díaz de Mera Escuderos,Athletic Club,Getafe CF,Athletic Club,Alex Berenguer,0,0,...
...
```

**Estadísticas:**
- ~7,576 filas (jugadores)
- 23 columnas
- 120 partidos procesados
- Tamaño: ~935 KB

## ⚙️ Cómo Funciona

1. **extract_match_urls.py**: Usa Selenium para navegar por la página principal y extraer las URLs de los 120 partidos
2. **extract_match_data_v2.py**: Para cada URL:
   - Carga la página del partido
   - Extrae información del árbitro
   - Extrae nombres de equipos
   - Extrae datos de cada jugador y sus estadísticas
   - Guarda progreso cada 10 partidos
3. Genera un CSV con todos los datos consolidados

## 🛠️ Tecnologías Utilizadas

- **Python 3** - Lenguaje principal
- **Selenium** - Automatización del navegador
- **BeautifulSoup4** - Parsing de HTML
- **ChromeDriver** - Driver para Chrome

## 📝 Notas

- El script ejecuta Chrome en modo headless (sin ventana visible)
- Guarda progreso cada 10 partidos en `match_data_progress.csv`
- Tiempo total de ejecución: ~20 minutos para 120 partidos
- El campo "Jornada" puede estar vacío en algunos casos si no está disponible en la página

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Si encuentras algún bug o tienes sugerencias:

1. Abre un Issue
2. Crea un Pull Request
3. Reporta problemas

## 📄 Licencia

Este proyecto es de código abierto y está disponible para uso libre.

## ⚠️ Disclaimer

Este proyecto es solo para fines educativos y de análisis de datos. Respeta los términos de servicio del sitio web fuente.

---

**Desarrollado por:** [Tu nombre/usuario]
**Fecha:** Noviembre 2025
**Versión:** 1.0.0
