#!/bin/bash
#
# 🚀 SCRIPT DE INICIO RÁPIDO
# Este script hace TODO automáticamente
#
# Cómo usar (en Mac/Linux):
#   chmod +x INICIO_FACIL.sh
#   ./INICIO_FACIL.sh
#

echo ""
echo "==============================================="
echo "  🚀 EXTRACTOR DE DATOS DE PARTIDOS"
echo "  Primera División 2025-2026"
echo "==============================================="
echo ""

# Función para mostrar pasos
paso=1
function mostrar_paso() {
    echo ""
    echo "[$paso] $1"
    echo "-------------------------------------------"
    ((paso++))
}

# 1. Verificar Python
mostrar_paso "Verificando Python..."
if command -v python3 &> /dev/null; then
    echo "✅ Python está instalado: $(python3 --version)"
else
    echo "❌ Python NO está instalado"
    echo "   Instálalo desde: https://www.python.org/downloads/"
    exit 1
fi

# 2. Instalar librerías
mostrar_paso "Instalando librerías necesarias..."
pip install selenium beautifulsoup4 --quiet --upgrade
if [ $? -eq 0 ]; then
    echo "✅ Librerías instaladas correctamente"
else
    echo "⚠️  Hubo un problema instalando librerías"
fi

# 3. Verificar ChromeDriver
mostrar_paso "Verificando ChromeDriver..."
python3 verificar_requisitos.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ ChromeDriver está instalado"
else
    echo "⚠️  ChromeDriver no encontrado"
    echo "   Mac: brew install chromedriver"
    echo "   Continuando de todas formas..."
fi

# 4. Preguntar qué hacer
echo ""
echo "==============================================="
echo "  ¿Qué quieres hacer?"
echo "==============================================="
echo ""
echo "1) Extraer URLs de partidos (si no las tienes)"
echo "2) Extraer TODOS los datos de partidos (RECOMENDADO)"
echo "3) Ejecutar TODO (URLs + Datos)"
echo "4) Solo verificar requisitos"
echo ""
read -p "Elige una opción (1-4): " opcion

case $opcion in
    1)
        mostrar_paso "Extrayendo URLs de partidos..."
        python3 extract_match_urls.py
        echo ""
        echo "✅ URLs guardadas en: match_urls.txt"
        echo "   Total de partidos: $(wc -l < match_urls.txt)"
        ;;

    2)
        # Verificar si existen las URLs
        if [ ! -f "match_urls.txt" ]; then
            echo "❌ No existe match_urls.txt"
            echo "   Primero necesitas extraer las URLs (opción 1 o 3)"
            exit 1
        fi

        mostrar_paso "Extrayendo datos de TODOS los partidos..."
        echo "⏱️  Esto tardará unos 15-20 minutos"
        echo "   Verás el progreso en pantalla..."
        echo ""

        python3 extract_match_data_v2.py

        if [ -f "BBDD_partidos_completo.csv" ]; then
            echo ""
            echo "==============================================="
            echo "  ✅ ¡PROCESO COMPLETADO!"
            echo "==============================================="
            echo ""
            echo "📊 Resultados:"
            echo "   - Archivo: BBDD_partidos_completo.csv"
            echo "   - Tamaño: $(ls -lh BBDD_partidos_completo.csv | awk '{print $5}')"
            echo "   - Registros: $(($(wc -l < BBDD_partidos_completo.csv) - 1)) jugadores"
            echo ""
            echo "📂 Abre el archivo en Excel para ver los datos"
        else
            echo "❌ Hubo un error al generar el archivo"
        fi
        ;;

    3)
        mostrar_paso "Extrayendo URLs de partidos..."
        python3 extract_match_urls.py
        echo "✅ URLs extraídas: $(wc -l < match_urls.txt) partidos"

        echo ""
        mostrar_paso "Extrayendo datos de TODOS los partidos..."
        echo "⏱️  Esto tardará unos 15-20 minutos"
        echo ""

        python3 extract_match_data_v2.py

        if [ -f "BBDD_partidos_completo.csv" ]; then
            echo ""
            echo "==============================================="
            echo "  ✅ ¡TODO COMPLETADO!"
            echo "==============================================="
            echo ""
            echo "📊 Archivos generados:"
            echo "   - match_urls.txt ($(wc -l < match_urls.txt) URLs)"
            echo "   - BBDD_partidos_completo.csv ($(($(wc -l < BBDD_partidos_completo.csv) - 1)) jugadores)"
            echo ""
        fi
        ;;

    4)
        mostrar_paso "Verificando requisitos..."
        python3 verificar_requisitos.py
        ;;

    *)
        echo "❌ Opción inválida"
        exit 1
        ;;
esac

echo ""
echo "==============================================="
echo "  ¡Gracias por usar el extractor!"
echo "==============================================="
echo ""
