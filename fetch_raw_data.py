import sqlite3
import pandas as pd
import requests
import re
from difflib import SequenceMatcher

DB_PATH = "data/futbol_master.db"

def normalizar_texto(texto):
    if not texto:
        return ""
    t = str(texto).lower().strip()
    for kw in ["fc", "cf", "sc", "club", "deportivo", "atletico", "atlético", "real", "united", "utd", "city", "town"]:
        t = re.sub(r'\b' + kw + r'\b', '', t)
    return "".join(t.split())

def obtener_id_equipo(cursor, nombre_fuente, id_liga, fuente="football_data"):
    """Busca el id_equipo en la base de datos intentando coincidencia directa o aproximada."""
    # 1. Búsqueda exacta en alias
    cursor.execute("""
        SELECT e.id_equipo 
        FROM alias_equipos a
        JOIN equipos e ON a.id_equipo = e.id_equipo
        WHERE e.id_liga = ? AND LOWER(a.nombre_fuente) = LOWER(?)
    """, (id_liga, nombre_fuente))
    row = cursor.fetchone()
    if row:
        return row[0]

    # 2. Búsqueda por similitud con los equipos oficiales registrados
    cursor.execute("SELECT id_equipo, nombre_oficial FROM equipos WHERE id_liga = ?", (id_liga,))
    equipos = cursor.fetchall()
    
    mejor_id = None
    mejor_score = 0.0
    for id_eq, nombre_of in equipos:
        score = SequenceMatcher(None, normalizar_texto(nombre_fuente), normalizar_texto(nombre_of)).ratio()
        if score > mejor_score:
            mejor_score = score
            mejor_id = id_eq

    if mejor_id and mejor_score >= 0.5:
        # Registrar este nuevo alias automáticamente para futuras consultas
        cursor.execute("INSERT OR IGNORE INTO alias_equipos (id_equipo, fuente, nombre_fuente) VALUES (?, ?, ?)",
                       (mejor_id, fuente, nombre_fuente))
        return mejor_id

    return None

def Mapear_FTR_a_1X2(ftr):
    """Mapea valores H/D/A de Football-Data a 1/X/2."""
    ftr_str = str(ftr).strip().upper()
    mapeo = {'H': '1', 'D': 'X', 'A': '2'}
    return mapeo.get(ftr_str, None)

def procesar_historico_cuotas(id_liga, code_fd, temporadas=["2425", "2324"]):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total_partidos = 0
    total_cuotas = 0

    for temp in temporadas:
        url = f"https://www.football-data.co.uk/mmz4281/{temp}/{code_fd}.csv"
        print(f"\nDescargando data de {id_liga} - Temporada 20{temp[:2]}-20{temp[2:]}...")

        try:
            df = pd.read_csv(url, encoding="latin1")
        except Exception as e:
            print(f"[ERROR] No se pudo descargar {url}: {e}")
            continue

        cols_necesarias = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']
        if not all(col in df.columns for col in cols_necesarias):
            print(f"[WARN] Formato inesperado en el CSV de {id_liga}.")
            continue

        temp_formateada = f"20{temp[:2]}-20{temp[2:]}"

        for _, row in df.iterrows():
            if pd.isna(row['HomeTeam']) or pd.isna(row['AwayTeam']) or pd.isna(row['FTR']):
                continue

            id_home = obtener_id_equipo(cursor, row['HomeTeam'], id_liga)
            id_away = obtener_id_equipo(cursor, row['AwayTeam'], id_liga)

            if not id_home or not id_away:
                print(f"  [OMITIDO] Equipo no mapeado: {row['HomeTeam']} vs {row['AwayTeam']}")
                continue

            resultado_1x2 = Mapear_FTR_a_1X2(row['FTR'])
            if not resultado_1x2:
                continue

            try:
                fecha_iso = pd.to_datetime(row['Date'], dayfirst=True).strftime('%Y-%m-%d')
            except Exception:
                fecha_iso = str(row['Date'])

            id_partido = f"{id_liga}_{temp}_{id_home}_{id_away}"

            cursor.execute("""
                INSERT OR REPLACE INTO partidos 
                (id_partido, id_liga, temporada, fecha_iso, id_equipo_home, id_equipo_away, goles_home, goles_away, resultado_1x2)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                id_partido, id_liga, temp_formateada, fecha_iso, 
                id_home, id_away, int(row['FTHG']), int(row['FTAG']), resultado_1x2
            ))
            total_partidos += 1

            # Asignación de cuotas
            casa = "Bet365" if 'B365H' in df.columns else "Avg"
            c_home = row.get('B365H') if 'B365H' in df.columns else row.get('AvgH')
            c_draw = row.get('B365D') if 'B365D' in df.columns else row.get('AvgD')
            c_away = row.get('B365A') if 'B365A' in df.columns else row.get('AvgA')
            c_over = row.get('B365>2.5') if 'B365>2.5' in df.columns else row.get('Avg>2.5')
            c_under = row.get('B365<2.5') if 'B365<2.5' in df.columns else row.get('Avg<2.5')

            if pd.notna(c_home) and pd.notna(c_draw) and pd.notna(c_away):
                cursor.execute("""
                    INSERT OR REPLACE INTO cuotas 
                    (id_partido, casa_apuestas, cuota_1, cuota_x, cuota_2, cuota_over_25, cuota_under_25)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    id_partido, casa, float(c_home), float(c_draw), float(c_away),
                    float(c_over) if pd.notna(c_over) else None,
                    float(c_under) if pd.notna(c_under) else None
                ))
                total_cuotas += 1

    conn.commit()
    conn.close()
    print(f"[OK] {id_liga}: {total_partidos} partidos y {total_cuotas} registros de cuotas guardados.")

if __name__ == "__main__":
    ligas_config = [
        ("ENG1", "E0"),
        ("ESP1", "SP1")
    ]

    print("=" * 60)
    print("Iniciando Ingesta de Partidos y Cuotas Históricas")
    print("=" * 60)

    for id_liga, code_fd in ligas_config:
        procesar_historico_cuotas(id_liga, code_fd)

    print("\n" + "=" * 60)
    print("[ÉXITO] Ingesta inicial completada en 'data/futbol_master.db'.")
    print("=" * 60)
    