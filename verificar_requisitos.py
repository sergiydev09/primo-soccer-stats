#!/usr/bin/env python3
"""
Script de verificación de requisitos
Ejecuta este script primero para ver si tienes todo instalado
"""

import sys
import subprocess
import os

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def check_requirement(name, check_func):
    """Verifica un requisito y muestra el resultado"""
    print(f"🔍 Verificando {name}...", end=" ")
    try:
        result = check_func()
        if result:
            print("✅ OK")
            return True
        else:
            print("❌ NO ENCONTRADO")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def check_python():
    """Verifica versión de Python"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 7:
        print(f"✅ OK (Python {version.major}.{version.minor}.{version.micro})")
        return True
    else:
        print(f"❌ Versión muy antigua: {version.major}.{version.minor}")
        return False

def check_pip():
    """Verifica pip"""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"],
                      capture_output=True, check=True)
        return True
    except:
        return False

def check_selenium():
    """Verifica selenium"""
    try:
        import selenium
        return True
    except ImportError:
        return False

def check_beautifulsoup():
    """Verifica beautifulsoup4"""
    try:
        import bs4
        return True
    except ImportError:
        return False

def check_chromedriver():
    """Verifica ChromeDriver"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=chrome_options)
        driver.quit()
        return True
    except Exception as e:
        return False

def check_files():
    """Verifica archivos necesarios"""
    files = {
        "extract_match_urls.py": "Script para extraer URLs",
        "extract_match_data_v2.py": "Script principal de extracción",
        "GUIA_FACIL.md": "Guía de uso"
    }

    all_ok = True
    for file, desc in files.items():
        exists = os.path.exists(file)
        status = "✅" if exists else "❌"
        print(f"  {status} {file:<30} - {desc}")
        if not exists:
            all_ok = False

    return all_ok

def main():
    print_header("🔧 VERIFICADOR DE REQUISITOS")

    print("Este script verificará que tengas todo lo necesario instalado.\n")

    results = {}

    # Verificar Python
    print(f"🔍 Verificando Python...", end=" ")
    results['python'] = check_python()

    # Verificar pip
    results['pip'] = check_requirement("pip", check_pip)

    # Verificar librerías
    results['selenium'] = check_requirement("selenium", check_selenium)
    results['beautifulsoup'] = check_requirement("beautifulsoup4", check_beautifulsoup)

    # Verificar ChromeDriver
    results['chromedriver'] = check_requirement("ChromeDriver", check_chromedriver)

    # Verificar archivos
    print(f"\n🔍 Verificando archivos del proyecto:")
    results['files'] = check_files()

    # Resumen
    print_header("📊 RESUMEN")

    all_ok = all(results.values())

    if all_ok:
        print("✅ ¡TODO ESTÁ LISTO!")
        print("\nPuedes ejecutar el script:")
        print(f"  python3 extract_match_data_v2.py")
        return 0
    else:
        print("❌ FALTAN ALGUNOS REQUISITOS\n")

        # Instrucciones para instalar lo que falta
        if not results['selenium'] or not results['beautifulsoup']:
            print("📦 Para instalar las librerías faltantes, ejecuta:")
            print(f"  pip install selenium beautifulsoup4\n")

        if not results['chromedriver']:
            print("🔧 Para instalar ChromeDriver:")
            print("  Mac: brew install chromedriver")
            print("  Windows: Descarga de https://chromedriver.chromium.org/\n")

        if not results['files']:
            print("📁 Asegúrate de estar en la carpeta correcta del proyecto.\n")

        print("📖 Consulta GUIA_FACIL.md para más detalles.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
