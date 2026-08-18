import sqlite3
import pandas as pd
import requests
import json
import re
from difflib import SequenceMatcher

DB_PATH = "data/futbol_master.db"

# Normalización de texto para matching
def normalizar_texto(texto):
    if not texto:
        return ""
    t = str(texto).lower().strip()
    for kw in ["fc", "cf", "sc", "club", "deportivo", "atletico", "atlético", "real", "united", "utd", "city", "town"]:
        t = re.sub(r'\b' + kw + r'\b', '', t)
    return "".join(t.split())

def similaridad(a, b):
    return SequenceMatcher(None, normalizar_texto(a), normalizar_texto(b)).ratio()

# 1. Obtener equipos desde Understat con User-Agent de navegador
def obtener_equipos_understat(league_name, year=2024):
    url = f"https://understat.com/league/{league_name}/{year}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            match = re.search(r"teamsData\s*=\s*JSON\.parse\('([^']+)'\)", res.text)
            if match:
                json_str = match.group(1).encode('utf-8').decode('unicode_escape')
                teams_dict = json.loads(json_str)
                return [info['title'] for id_team, info in teams_dict.items()]
    except Exception as e:
        print(f"[WARN] No se pudo conectar a Understat ({league_name}): {e}")
    return []

# 2. Obtener equipos desde Football-Data.co.uk (CSV)
def obtener_equipos_football_data(code):
    # Intentar descargar la temporada más reciente disponible
    for season in ["2425", "2324"]:
        url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
        try:
            df = pd.read_csv(url, encoding="latin1")
            equipos = set(df['HomeTeam'].dropna().unique()).union(set(df['AwayTeam'].dropna().unique()))
            if len(equipos) > 0:
                return list(equipos)
        except Exception:
            continue
    return []

# 3. Mapeo y Guardado en SQL
def procesar_liga(id_liga, understat_code, fd_code):
    print("=" * 60)
    print(f"Procesando Liga: {id_liga} ({understat_code})")
    print("=" * 60)

    equipos_us = obtener_equipos_understat(understat_code)
    equipos_fd = obtener_equipos_football_data(fd_code)

    # Si Understat falla por bloqueo, usar Football-Data como fuente principal de equipos
    if not equipos_us:
        print(f"[INFO] Utilizando fuente secundaria Football-Data para registrar clubes de {id_liga}...")
        equipos_us = equipos_fd

    if not equipos_us:
        print(f"[ERROR] No se pudieron obtener equipos para {id_liga} desde ninguna fuente.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for team_us in equipos_us:
        # Registrar o recuperar id_equipo
        cursor.execute("SELECT id_equipo FROM equipos WHERE id_liga = ? AND nombre_oficial = ?", (id_liga, team_us))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute("INSERT INTO equipos (id_liga, nombre_oficial) VALUES (?, ?)", (id_liga, team_us))
            id_equipo = cursor.lastrowid
        else:
            id_equipo = row[0]

        # Registrar Alias Understat
        cursor.execute("""
            INSERT OR IGNORE INTO alias_equipos (id_equipo, fuente, nombre_fuente)
            VALUES (?, 'understat', ?)
        """, (id_equipo, team_us))

        # Mapear y registrar Alias Football-Data
        mejor_match_fd = None
        mejor_score = 0.0

        for team_fd in equipos_fd:
            score = similaridad(team_us, team_fd)
            if score > mejor_score:
                mejor_score = score
                mejor_match_fd = team_fd

        if mejor_match_fd and mejor_score >= 0.5:
            cursor.execute("""
                INSERT OR IGNORE INTO alias_equipos (id_equipo, fuente, nombre_fuente)
                VALUES (?, 'football_data', ?)
            """, (id_equipo, mejor_match_fd))
            print(f"  [MAPEO OK] {team_us:<25} <---> {mejor_match_fd:<25} (Score: {mejor_score:.2f})")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    ligas_config = [
        ("ENG1", "EPL", "E0"),
        ("ESP1", "La_liga", "SP1")
    ]

    for id_liga, us_code, fd_code in ligas_config:
        procesar_liga(id_liga, us_code, fd_code)

    print("\n" + "=" * 60)
    print("[ÉXITO] Mapeo de equipos y alias registrado en 'data/futbol_master.db'.")
    print("=" * 60)
    