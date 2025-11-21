# Extractor de URLs de Partidos - Opta Player Stats

Scripts para extraer todas las URLs de partidos de la Primera División 2025-2026 desde Opta Player Stats.

## 📋 Archivos

- **extract_match_urls.py**: Versión con Selenium (recomendada) - simula un navegador real
- **extract_match_urls_simple.py**: Versión con requests/BeautifulSoup (más ligera)
- **requirements.txt**: Dependencias necesarias
- **match_urls.txt**: Archivo de salida con las URLs extraídas

## 🚀 Instalación

### Opción 1: Instalar todas las dependencias (incluye Selenium)

```bash
pip install -r requirements.txt
```

Si usas Selenium, también necesitas instalar ChromeDriver:

**macOS:**
```bash
brew install chromedriver
```

**Linux:**
```bash
sudo apt-get install chromium-chromedriver
```

**Windows:**
Descarga ChromeDriver desde: https://chromedriver.chromium.org/

### Opción 2: Solo requests y BeautifulSoup (método simple)

```bash
pip install requests beautifulsoup4
```

## 💻 Uso

### Método 1: Con Selenium (Recomendado)

```bash
python extract_match_urls.py
```

Este método:
- ✅ Funciona aunque el sitio bloquee peticiones automatizadas
- ✅ Ejecuta JavaScript si es necesario
- ✅ Más robusto y confiable
- ⚠️  Requiere ChromeDriver instalado

### Método 2: Con requests (Más rápido pero puede fallar)

```bash
python extract_match_urls_simple.py
```

Este método:
- ✅ Más rápido y ligero
- ✅ No requiere navegador ni ChromeDriver
- ⚠️  Puede recibir error 403 si el sitio bloquea peticiones
- ⚠️  No funciona si el contenido se carga con JavaScript

## 📄 Salida

Ambos scripts generan:

1. **Salida en consola**: Lista numerada de todas las URLs encontradas
2. **Archivo match_urls.txt**: Archivo de texto con una URL por línea

### Ejemplo de salida:

```
================================================================================
Se encontraron 380 URLs de partidos:
================================================================================

1. https://optaplayerstats.statsperform.com/en_GB/soccer/primera-división-2025-2026/80zg2v1cuqcfhphn56u4qpyqc/match/view/16t0fdut4ky4b4es7i0trovtg/match-summary
2. https://optaplayerstats.statsperform.com/en_GB/soccer/primera-división-2025-2026/80zg2v1cuqcfhphn56u4qpyqc/match/view/176p8ms7mmtnsyiwqb87aavx0/match-summary
3. https://optaplayerstats.statsperform.com/en_GB/soccer/primera-división-2025-2026/80zg2v1cuqcfhphn56u4qpyqc/match/view/17kbnro1phdt3xdaadluy52j8/match-summary
...

================================================================================
URLs guardadas en: match_urls.txt
================================================================================
```

## 🔧 Personalización

Si quieres extraer URLs de otra liga o temporada, modifica la variable `base_url` o `url` en el script:

```python
# En extract_match_urls.py o extract_match_urls_simple.py
base_url = "TU_URL_AQUI"
```

## ❓ Solución de Problemas

### Error 403 Forbidden
- Usa el script con Selenium (`extract_match_urls.py`)
- Verifica que ChromeDriver esté instalado correctamente

### Selenium no encuentra ChromeDriver
- Asegúrate de que ChromeDriver esté en tu PATH
- O especifica la ruta manualmente en el script

### No se encuentran URLs
- El sitio puede haber cambiado su estructura HTML
- Verifica manualmente que las URLs de partidos sigan el patrón `/match/view/`

## 📝 Notas

- Los scripts eliminan URLs duplicadas automáticamente
- Las URLs se ordenan alfabéticamente
- El script con Selenium ejecuta en modo headless (sin ventana visible)
- Ambos scripts usan un User-Agent de navegador real para evitar bloqueos
