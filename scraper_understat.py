"""
Scraper de Understat -- extrae xG por partido (Premier League y La Liga).

Understat no expone el xG en una tabla HTML visible: lo trae incrustado
como JSON dentro de un <script>, en una variable llamada 'datesData',
codificado como texto JS con escapes tipo \\x22 (comillas escapadas).
Este script encuentra ese bloque, lo decodifica, y lo convierte en un
DataFrame usable.

Cobertura: Understat solo tiene estas 6 ligas: EPL, La_liga, Bundesliga,
Serie_A, Ligue_1, RFPL. De nuestras 9, solo sirve para Premier League y
La Liga.
"""

import re
import json
import time
import requests
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

LIGAS_UNDERSTAT = {
    "EPL": "E0",       # nombre en Understat -> codigo en nuestra base
    "La_liga": "SP1",
}

# Understat identifica temporadas por el anio de inicio (2021 = temporada 2021/2022)
TEMPORADAS = [2021, 2022, 2023, 2024, 2025]


def extraer_json_de_script(html, nombre_variable="datesData"):
    """Busca el bloque JSON.parse('...') asociado a una variable de JS
    y lo decodifica a un objeto Python."""
    patron = re.compile(
        rf"var\s+{nombre_variable}\s*=\s*JSON\.parse\('(.*?)'\)", re.DOTALL
    )
    match = patron.search(html)
    if not match:
        return None

    crudo = match.group(1)
    # El texto viene con escapes tipo \x22 (comilla), hay que decodificarlo
    decodificado = crudo.encode("utf-8").decode("unicode_escape")
    # unicode_escape puede corromper caracteres no-ASCII (nombres con tildes);
    # se re-codifica correctamente a utf-8 despues del escape
    decodificado = decodificado.encode("latin1").decode("utf-8")
    return json.loads(decodificado)


def descargar_temporada(liga_understat, anio):
    url = f"https://understat.com/league/{liga_understat}/{anio}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    datos = extraer_json_de_script(resp.text, "datesData")
    if datos is None:
        print(f"  [AVISO] No se encontro 'datesData' en {url} -- revisar manualmente")
        return []
    return datos


def parsear_partidos(datos_crudos, liga_code, anio):
    filas = []
    for partido in datos_crudos:
        if not partido.get("isResult"):
            continue  # partido todavia no jugado
        filas.append({
            "liga_understat": liga_code,
            "temporada_understat": anio,
            "fecha": partido.get("datetime"),
            "home_team": partido["h"]["title"],
            "away_team": partido["a"]["title"],
            "fthg": int(partido["goals"]["h"]),
            "ftag": int(partido["goals"]["a"]),
            "xg_home": float(partido["xG"]["h"]),
            "xg_away": float(partido["xG"]["a"]),
        })
    return filas


if __name__ == "__main__":
    todas_las_filas = []

    for liga_understat, nuestro_codigo in LIGAS_UNDERSTAT.items():
        for anio in TEMPORADAS:
            print(f"Descargando {liga_understat} temporada {anio}...")
            try:
                datos = descargar_temporada(liga_understat, anio)
                filas = parsear_partidos(datos, nuestro_codigo, anio)
                print(f"  {len(filas)} partidos con xG obtenidos")
                todas_las_filas.extend(filas)
            except requests.exceptions.RequestException as e:
                print(f"  [ERROR] {e}")
            time.sleep(4)  # pausa prudente entre requests

    df = pd.DataFrame(todas_las_filas)
    print(f"\nTotal de partidos descargados: {len(df)}")
    if not df.empty:
        print(df.head(10).to_string(index=False))
        df.to_csv("understat_xg.csv", index=False)
        print("\nGuardado en understat_xg.csv")
