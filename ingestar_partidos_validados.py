import sqlite3
import pandas as pd

DB_PATH = "data/futbol_master.db"

def obtener_o_crear_id_equipo(cursor, nombre_equipo, id_liga):
    """Busca el ID del equipo; si no existe, lo inserta incluyendo id_liga obligatorio."""
    query = "SELECT id_equipo FROM equipos WHERE LOWER(nombre_oficial) LIKE LOWER(?) LIMIT 1"
    cursor.execute(query, (f"%{nombre_equipo}%",))
    res = cursor.fetchone()
    
    if res:
        return res[0]
    
    # Obtener el siguiente ID disponible
    cursor.execute("SELECT MAX(id_equipo) FROM equipos")
    max_id = cursor.fetchone()[0]
    nuevo_id = (max_id if max_id is not None else 0) + 1
    
    # Insertar incluyendo id_liga para cumplir el constraint NOT NULL
    cursor.execute(
        "INSERT INTO equipos (id_equipo, id_liga, nombre_oficial) VALUES (?, ?, ?)", 
        (nuevo_id, id_liga, nombre_equipo)
    )
    print(f"[NUEVO EQUIPO] '{nombre_equipo}' registrado en BD con ID {nuevo_id} (Liga: {id_liga})")
    return nuevo_id

def obtener_ultimas_metricas_equipo(conn, id_equipo):
    """Obtiene el último promedio móvil registrado para un equipo dado."""
    query = f"""
        SELECT 
            home_roll_gf, home_roll_gc, home_roll_xg_f, home_roll_xg_c,
            away_roll_gf, away_roll_gc, away_roll_xg_f, away_roll_xg_c
        FROM matriz_features
        WHERE id_equipo_home = {id_equipo} OR id_equipo_away = {id_equipo}
        ORDER BY fecha DESC
        LIMIT 1
    """
    df = pd.read_sql_query(query, conn)
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

def insertar_partido_validado(liga, temporada, fecha_iso, local_nombre, visita_nombre, odd_1, odd_x, odd_2):
    """Sincroniza y registra el partido tanto en la tabla 'partidos' como en 'matriz_features'."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    id_home = obtener_o_crear_id_equipo(cursor, local_nombre, liga)
    id_away = obtener_o_crear_id_equipo(cursor, visita_nombre, liga)

    fecha_clean = fecha_iso.replace("-", "").replace(" ", "").replace(":", "")[:12]
    id_partido = f"{liga}_{fecha_clean}_{id_home}_{id_away}"

    try:
        # 1. Insertar en tabla 'partidos'
        sql_partidos = """
            INSERT OR REPLACE INTO partidos (
                id_partido, id_liga, temporada, fecha_iso, 
                id_equipo_home, id_equipo_away, goles_home, goles_away, 
                resultado_1x2, odd_1, odd_x, odd_2
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?)
        """
        cursor.execute(sql_partidos, (id_partido, liga, temporada, fecha_iso, id_home, id_away, odd_1, odd_x, odd_2))

        # 2. Rescatar o asignar métricas base
        m_home = obtener_ultimas_metricas_equipo(conn, id_home)
        m_away = obtener_ultimas_metricas_equipo(conn, id_away)

        h_gf = m_home.get('home_roll_gf', 1.2) if m_home else 1.2
        h_gc = m_home.get('home_roll_gc', 1.0) if m_home else 1.0
        h_xgf = m_home.get('home_roll_xg_f', 1.3) if m_home else 1.3
        h_xgc = m_home.get('home_roll_xg_c', 1.1) if m_home else 1.1

        a_gf = m_away.get('away_roll_gf', 1.1) if m_away else 1.1
        a_gc = m_away.get('away_roll_gc', 1.2) if m_away else 1.2
        a_xgf = m_away.get('away_roll_xg_f', 1.2) if m_away else 1.2
        a_xgc = m_away.get('away_roll_xg_c', 1.3) if m_away else 1.3

        diff_xg = h_xgf - a_xgf
        diff_gf = h_gf - a_gf

        # 3. Insertar en tabla 'matriz_features'
        sql_features = """
            INSERT OR REPLACE INTO matriz_features (
                id_partido, id_liga, temporada, fecha, 
                id_equipo_home, id_equipo_away, goles_home, goles_away, resultado,
                home_roll_gf, home_roll_gc, home_roll_xg_f, home_roll_xg_c,
                away_roll_gf, away_roll_gc, away_roll_xg_f, away_roll_xg_c,
                diff_roll_xg, diff_roll_gf
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(sql_features, (
            id_partido, liga, temporada, fecha_iso, id_home, id_away,
            h_gf, h_gc, h_xgf, h_xgc, a_gf, a_gc, a_xgf, a_xgc, diff_xg, diff_gf
        ))

        conn.commit()
        print(f"[EXITO] Partido Registrado: {local_nombre} (ID {id_home}) vs {visita_nombre} (ID {id_away}) | Fecha: {fecha_iso}")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] No se pudo registrar el partido: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Limpieza preventiva de pruebas previas
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM partidos WHERE id_partido LIKE 'ENG1_2026%'")
    conn.execute("DELETE FROM matriz_features WHERE id_partido LIKE 'ENG1_2026%'")
    conn.commit()
    conn.close()

    # Programación real con cuotas exactas de la casa de apuestas
    partidos_programados = [
        # liga, temporada, fecha_hora, local, visita, odd_1, odd_x, odd_2
        ("ENG1", "2026-2027", "2026-08-22 10:00", "Ipswich", "Sunderland", 2.78, 3.28, 2.73),
        ("ENG1", "2026-2027", "2026-08-21 15:00", "Arsenal", "Coventry", 1.30, 5.80, 11.00),
        ("ENG1", "2026-2027", "2026-08-31 15:00", "Aston Villa", "Arsenal", 3.10, 4.10, 2.40),
        ("ENG1", "2026-2027", "2026-09-06 12:30", "Arsenal", "Chelsea", 2.05, 4.30, 3.70)
    ]

    print("\n--- CARGANDO PROGRAMACIÓN CON CUOTAS REALES DE LA CASA DE APUESTAS ---")
    for p in partidos_programados:
        insertar_partido_validado(*p)
        