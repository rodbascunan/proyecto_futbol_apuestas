import sqlite3
import re
from difflib import SequenceMatcher
from understatapi import UnderstatClient

DB_PATH = "data/futbol_master.db"

MAPEO_EXPLICITO = {
    "manchester city": "man city",
    "manchester united": "man united",
    "wolverhampton wanderers": "wolves",
    "wolverhampton": "wolves",
    "tottenham": "tottenham",
    "newcastle united": "newcastle",
    "west ham united": "west ham",
    "brighton & hove albion": "brighton",
    "sheffield united": "sheffield utd",
    "athletic club": "ath bilbao",
    "atletico madrid": "ath madrid",
    "real betis": "betis",
    "real valladolid": "valladolid",
    "rayo vallecano": "vallecano",
    "real sociedad": "sociedad"
}

def normalizar_texto(texto):
    if not texto:
        return ""
    t = str(texto).lower().strip()
    for kw in ["fc", "cf", "sc", "club", "deportivo", "atletico", "atlético", "real", "united", "utd", "city", "town"]:
        t = re.sub(r'\b' + kw + r'\b', '', t)
    return "".join(t.split())

def obtener_id_equipo(cursor, nombre_us, id_liga):
    nombre_clean = nombre_us.strip().lower()

    cursor.execute("""
        SELECT id_equipo FROM alias_equipos 
        WHERE LOWER(nombre_fuente) = LOWER(?)
    """, (nombre_us,))
    row = cursor.fetchone()
    if row:
        return row[0]

    nombre_us_normalizado = MAPEO_EXPLICITO.get(nombre_clean, nombre_us)

    cursor.execute("""
        SELECT id_equipo FROM equipos 
        WHERE id_liga = ? AND (LOWER(nombre_oficial) = LOWER(?) OR LOWER(nombre_oficial) = LOWER(?))
    """, (id_liga, nombre_us, nombre_us_normalizado))
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute("SELECT id_equipo, nombre_oficial FROM equipos WHERE id_liga = ?", (id_liga,))
    equipos = cursor.fetchall()
    
    mejor_id = None
    mejor_score = 0.0
    for id_eq, nombre_of in equipos:
        score = SequenceMatcher(None, normalizar_texto(nombre_us_normalizado), normalizar_texto(nombre_of)).ratio()
        if score > mejor_score:
            mejor_score = score
            mejor_id = id_eq

    if mejor_id and mejor_score >= 0.35:
        cursor.execute("INSERT OR IGNORE INTO alias_equipos (id_equipo, fuente, nombre_fuente) VALUES (?, 'understat', ?)",
                       (mejor_id, nombre_us))
        return mejor_id

    return None

def descargar_xg_liga(id_liga, league_code, aos=["2023", "2024"]):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    total_xg_insertados = 0

    with UnderstatClient() as client:
        for year in aos:
            print(f"\nDescargando xG para {id_liga} ({league_code}) - Temporada {year}...")
            try:
                # Obtener la lista de partidos directamente desde la API cliente
                league_match_data = client.league(league=league_code).get_match_data(season=year)
                
                insertados_temporada = 0
                omitidos_temporada = 0

                for p in league_match_data:
                    home_name = p.get('h', {}).get('title')
                    away_name = p.get('a', {}).get('title')

                    if not home_name or not away_name:
                        continue

                    id_home = obtener_id_equipo(cursor, home_name, id_liga)
                    id_away = obtener_id_equipo(cursor, away_name, id_liga)

                    if not id_home or not id_away:
                        omitidos_temporada += 1
                        continue

                    code_temp = "2324" if year == "2023" else "2425"
                    id_partido = f"{id_liga}_{code_temp}_{id_home}_{id_away}"

                    xg_h = float(p.get('xG', {}).get('h', 0)) if isinstance(p.get('xG'), dict) else float(p.get('xG', 0))
                    xg_a = float(p.get('xG', {}).get('a', 0)) if isinstance(p.get('xG'), dict) else float(p.get('xGa', 0))

                    cursor.execute("""
                        INSERT OR REPLACE INTO metricas_xg 
                        (id_partido, xg_home, xg_away, xga_home, xga_away)
                        VALUES (?, ?, ?, ?, ?)
                    """, (id_partido, xg_h, xg_a, xg_a, xg_h))

                    insertados_temporada += 1

                total_xg_insertados += insertados_temporada
                print(f"[INFO] Temporada {year}: {insertados_temporada} partidos insertados ({omitidos_temporada} omitidos sin ID).")

            except Exception as e:
                print(f"[ERROR] Excepción al procesar {id_liga} ({year}): {e}")

    conn.commit()
    conn.close()
    print(f"[OK] {id_liga}: {total_xg_insertados} registros de xG insertados en total.")

if __name__ == "__main__":
    ligas_config = [
        ("ENG1", "EPL"),
        ("ESP1", "La_Liga")
    ]

    print("=" * 60)
    print("Iniciando Extracción de Métricas xG con UnderstatAPI")
    print("=" * 60)

    for id_liga, us_code in ligas_config:
        descargar_xg_liga(id_liga, us_code)

    print("\n" + "=" * 60)
    print("[ÉXITO] Proceso finalizado e insertado en 'data/futbol_master.db'.")
    print("=" * 60)
