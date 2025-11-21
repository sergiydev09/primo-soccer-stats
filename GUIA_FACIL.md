# 📖 GUÍA SÚPER FÁCIL - Extracción de Datos de Partidos

## 🎯 ¿Qué hace este script?

Extrae TODOS los datos de jugadores y árbitros de los 120 partidos de Primera División 2025-2026 y los guarda en un Excel (CSV).

---

## 📋 REQUISITOS (Instalar primero)

### 1️⃣ Instalar Python

**Mac:**
```bash
# Abre Terminal (búscalo en Spotlight con Cmd+Espacio)
# Verifica si ya tienes Python:
python3 --version

# Si no lo tienes, instala Homebrew primero:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Luego instala Python:
brew install python3
```

**Windows:**
1. Ve a: https://www.python.org/downloads/
2. Descarga Python (versión 3.10 o superior)
3. **IMPORTANTE**: Al instalar, marca la casilla "Add Python to PATH"
4. Haz clic en "Install Now"

---

### 2️⃣ Instalar Chrome (si no lo tienes)

Descarga e instala Google Chrome desde: https://www.google.com/chrome/

---

### 3️⃣ Instalar ChromeDriver

**Mac:**
```bash
# En Terminal:
brew install chromedriver
```

**Windows:**
1. Ve a: https://chromedriver.chromium.org/downloads
2. Descarga la versión que coincida con tu Chrome
3. Descomprime el archivo
4. Mueve `chromedriver.exe` a `C:\Windows\System32\`

---

## 🚀 PASOS PARA USAR EL SCRIPT

### PASO 1: Abrir la terminal/consola

**Mac:**
- Presiona `Cmd + Espacio`
- Escribe "Terminal"
- Presiona Enter

**Windows:**
- Presiona `Windows + R`
- Escribe "cmd"
- Presiona Enter

---

### PASO 2: Ir a la carpeta del proyecto

En la terminal, escribe:

**Mac:**
```bash
cd /Users/sergiy/StudioProjects/Primo
```

**Windows:**
```bash
cd C:\Users\TU_USUARIO\StudioProjects\Primo
```

💡 **Tip**: Si no sabes la ruta, arrastra la carpeta a la terminal y automáticamente se escribe la ruta.

---

### PASO 3: Instalar las librerías necesarias

Copia y pega este comando en la terminal:

```bash
pip install selenium beautifulsoup4
```

Presiona Enter y espera a que termine (puede tardar 1-2 minutos).

---

### PASO 4: Ejecutar el script completo

Hay 2 opciones:

#### 🔹 OPCIÓN A: Extraer URLs de partidos (si no las tienes)

```bash
python3 extract_match_urls.py
```

Esto creará el archivo `match_urls.txt` con las 120 URLs de partidos.

**Tiempo**: ~2 minutos

---

#### 🔹 OPCIÓN B: Extraer todos los datos de los partidos

```bash
python3 extract_match_data_v2.py
```

Esto:
1. Lee las 120 URLs del archivo `match_urls.txt`
2. Visita cada partido
3. Extrae datos de árbitros y jugadores
4. Guarda todo en `BBDD_partidos_completo.csv`

**Tiempo**: ~15-20 minutos

💡 **Verás algo así en pantalla:**
```
[1] Cargando: https://optaplayerstats...
  Árbitro: Isidro Díaz de Mera Escuderos
  Athletic Club vs Getafe CF
  ✓ Extraídos 58 registros de jugadores

[2] Cargando: https://optaplayerstats...
  Árbitro: Francisco José Hernández Maeso
  ...
```

---

### PASO 5: Esperar a que termine

El script te mostrará:
- Cada partido que está procesando
- Cuántos jugadores extrajo de cada uno
- Guardará progreso cada 10 partidos

Cuando termine verás:
```
================================================================================
💾 Guardando datos finales...
✓ Total de registros: 7576
✓ Archivo: BBDD_partidos_completo.csv
================================================================================

✓ Proceso completado
```

---

### PASO 6: Abrir el archivo CSV

El archivo `BBDD_partidos_completo.csv` estará en la misma carpeta.

**Para abrirlo en Excel:**
1. Abre Excel
2. Archivo → Abrir
3. Busca `BBDD_partidos_completo.csv`
4. Haz clic en "Abrir"

**O simplemente:**
- Haz doble clic en el archivo `BBDD_partidos_completo.csv`

---

## ❓ SOLUCIÓN DE PROBLEMAS

### "Command not found: python3"

**Solución:**
- En Windows usa `python` en lugar de `python3`
- O instala Python (ver Paso 1)

---

### "ModuleNotFoundError: No module named 'selenium'"

**Solución:**
```bash
pip install selenium beautifulsoup4
```

---

### "ChromeDriver not found" o errores con Chrome

**Solución Mac:**
```bash
brew install chromedriver
```

**Solución Windows:**
- Descarga ChromeDriver de https://chromedriver.chromium.org/
- Ponlo en la carpeta del proyecto

---

### El script se queda atascado

**Solución:**
- Presiona `Ctrl + C` para cancelar
- Ejecuta de nuevo el comando
- El script continuará desde donde guardó progreso

---

## 📊 ¿QUÉ DATOS OBTIENES?

El CSV final contiene:

### Por cada jugador de cada partido:
- ✅ Número de partido (1-120)
- ✅ ID del partido
- ✅ Árbitro
- ✅ Equipo local y visitante
- ✅ Nombre del jugador
- ✅ Equipo del jugador
- ✅ **15 estadísticas**: Goles, Asistencias, Tarjetas, Tiros, Pases, Entradas, Córners, Centros, Faltas, Fueras de juego, Paradas, etc.

**Total**: ~7,600 filas con datos de jugadores

---

## 🎯 RESUMEN RÁPIDO (Todo en 5 comandos)

```bash
# 1. Ir a la carpeta
cd /Users/sergiy/StudioProjects/Primo

# 2. Instalar librerías
pip install selenium beautifulsoup4

# 3. (Opcional) Si necesitas las URLs primero
python3 extract_match_urls.py

# 4. Extraer todos los datos
python3 extract_match_data_v2.py

# 5. Listo! Abre BBDD_partidos_completo.csv en Excel
```

---

## 📞 ¿NECESITAS AYUDA?

Si algo no funciona:

1. Copia el mensaje de error completo
2. Busca en Google el error
3. O manda captura del error

---

## ✅ CHECKLIST FINAL

Antes de empezar, verifica que tengas:

- [ ] Python instalado (`python3 --version`)
- [ ] Chrome instalado
- [ ] ChromeDriver instalado
- [ ] Terminal/Consola abierta
- [ ] Estás en la carpeta correcta (`cd /Users/sergiy/StudioProjects/Primo`)
- [ ] Librerías instaladas (`pip install selenium beautifulsoup4`)

Si marcaste todo, ¡estás listo! 🚀

Ejecuta:
```bash
python3 extract_match_data_v2.py
```

Y espera ~20 minutos. ¡Eso es todo!
