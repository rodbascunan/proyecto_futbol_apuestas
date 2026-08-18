import sqlite3
import pandas as pd
import re

DB_PATH = "data/futbol_master.db"

# Fuentes de datos de cuotas históricas (Football-Data)
URLS_CUOTAS = {
    "ENG1_2324": "https://www.football-data.co.uk/mmz4281/2324/E0.csv",
    "ENG1_2425": "https://www.football-data.co.uk/mmz4281/2425/E0.csv",
    "ESP1_2324": "https://www.football-data.co.uk/mmz4281/2324/SP1.csv",
    "ESP1_2425": "https://www.football-data.co.uk/mmz4281/2425/SP1.csv",
}

MAPEO_EQUIPOS_FD = {
    "man city": "manchester city",
    "man utd": "manchester united",
    "wolves": "wolverhampton wanderers",
    "ath bilbao": "athletic club",
    "ath madrid": "atletico madrid",
    "betis": "real betis",
    "vallecano": "rayo vallecano",
    "sociedad": "real sociedad"
}

def agregar_columnas_cuotas(conn):
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(partidos)")
    cols = [row[1] for row in cursor.fetchall()]
    
    for col in ['odd_1', 'odd_x', 'odd_2']:
        if col not in cols:
            cursor.execute(f"ALTER TABLE partidos ADD COLUMN {col} REAL")
    conn.commit()

def normalizar_nombre(nombre):
    if not nombre:
        return ""
    n = str(nombre).lower().strip()
    return MAPEO_EQUIPOS_FD.get(n, n)

def obtener_id_equipo(cursor, nombre_fd, id_liga):
    nombre_norm = normalizar_nombre(nombre_fd)
    
    # Buscar en tabla alias o equipos
    cursor.execute("""
        SELECT id_equipo FROM alias_equipos 
        WHERE LOWER(nombre_fuente) = LOWER(?)
    """, (nombre_fd,))
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute("""
        SELECT id_equipo FROM equipos 
        WHERE id_liga = ? AND (LOWER(nombre_oficial) LIKE ? OR LOWER(nombre_oficial) LIKE ?)
    """, (id_liga, f"%{nombre_norm}%", f"%{nombre_fd}%"))
    row = cursor.fetchone()
    if row:
        return row[0]
        
    return None

def actualizar_cuotas():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Asegurar que existan las columnas en 'partidos'
    agregar_columnas_cuotas(conn)

    total_actualizados = 0

    for key, url in URLS_CUOTAS.items():
        id_liga, temp_code = key.split('_')
        print(f"\nDescargando cuotas para {id_liga} - Temporada {temp_code}...")

        try:
            df = pd.read_csv(url)
        except Exception as e:
            print(f"[ERROR] No se pudo descargar desde {url}: {e}")
            continue

        # Columnas de cuotas promedio/prominentes en Football-Data (B365H, B365D, B365A o AvgH, AvgD, AvgA)
        col_h = 'AvgH' if 'AvgH' in df.columns else 'B365H'
        col_d = 'AvgD' if 'AvgD' in df.columns else 'B365D'
        col_a = 'AvgA' if 'AvgA' in df.columns else 'B365A'

        if col_h not in df.columns:
            print(f"[WARN] No se encontraron columnas de cuotas en {key}.")
            continue

        insertados_key = 0
        for _, row in df.iterrows():
            home_team = row.get('HomeTeam')
            away_team = row.get('AwayTeam')
            
            odd_1 = row.get(col_h)
            odd_x = row.get(col_d)
            odd_2 = row.get(col_a)

            if pd.isna(odd_1) or pd.isna(odd_x) or pd.isna(odd_2):
                continue

            id_home = obtener_id_equipo(cursor, home_team, id_liga)
            id_away = obtener_id_equipo(cursor, away_team, id_liga)

            if not id_home or not id_away:
                continue

            id_partido = f"{id_liga}_{temp_code}_{id_home}_{id_away}"

            cursor.execute("""
                UPDATE partidos 
                SET odd_1 = ?, odd_x = ?, odd_2 = ?
                WHERE id_partido = ?
            """, (float(odd_1), float(odd_x), float(odd_2), id_partido))

            if cursor.rowcount > 0:
                insertados_key += 1

        total_actualizados += insertados_key
        print(f"[INFO] {key}: {insertados_key} cuotas actualizadas.")

    conn.commit()
    conn.close()
    print(f"\n[OK] Se actualizaron cuotas en {total_actualizados} partidos.")

if __name__ == "__main__":
    print("=" * 60)
    print("Descargando e Integrando Cuotas de Apuestas (Odds)")
    print("=" * 60)

    actualizar_cuotas()

    print("\n" + "=" * 60)
    print("[ÉXITO] Proceso finalizado.")
    print("=" * 60)
    