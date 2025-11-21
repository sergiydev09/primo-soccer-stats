#!/usr/bin/env python3
"""
Script alternativo para extraer URLs de partidos usando requests y BeautifulSoup
Nota: Este método puede no funcionar si el sitio requiere JavaScript
"""

import requests
from bs4 import BeautifulSoup
import re

def extract_match_urls():
    """Extrae todas las URLs de partidos usando requests y BeautifulSoup"""

    # URL base
    url = "https://optaplayerstats.statsperform.com/en_GB/soccer/primera-divisi%C3%B3n-2025-2026/80zg2v1cuqcfhphn56u4qpyqc/opta-player-stats"

    # Headers para simular un navegador
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    print(f"Realizando petición a: {url}")

    try:
        # Hacer la petición
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        print(f"Respuesta recibida: {response.status_code}")

        # Parsear el HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Buscar todos los enlaces
        all_links = soup.find_all('a', href=True)

        # Filtrar URLs que contienen '/match/view/'
        match_urls = set()
        base_domain = "https://optaplayerstats.statsperform.com"

        for link in all_links:
            href = link['href']
            if '/match/view/' in href and 'match-summary' in href:
                # Si es una URL relativa, agregar el dominio
                if href.startswith('/'):
                    full_url = base_domain + href
                else:
                    full_url = href
                match_urls.add(full_url)

        # Ordenar URLs
        match_urls = sorted(list(match_urls))

        # Imprimir resultados
        print(f"\n{'='*80}")
        print(f"Se encontraron {len(match_urls)} URLs de partidos:")
        print(f"{'='*80}\n")

        for i, url in enumerate(match_urls, 1):
            print(f"{i}. {url}")

        # Guardar en archivo
        output_file = "match_urls.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            for url in match_urls:
                f.write(url + '\n')

        print(f"\n{'='*80}")
        print(f"URLs guardadas en: {output_file}")
        print(f"{'='*80}")

        return match_urls

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print("\n⚠️  Error 403: El servidor está bloqueando peticiones automatizadas.")
            print("Por favor, usa el script con Selenium (extract_match_urls.py)")
        else:
            print(f"Error HTTP: {e}")
        return []

    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    extract_match_urls()
