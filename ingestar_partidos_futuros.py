import sqlite3
import pandas as pd
import numpy as np

DB_PATH = "data/futbol_master.db"

def obtener_ultimas_metricas_equipo(conn, id_equipo):
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

def insertar_partido_futuro(id_partido, id_liga, temporada, fecha_iso, id_home, id_away, odd_1, odd_x, odd_2):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        sql_partidos = """
            INSERT OR REPLACE INTO partidos (
                id_partido, id_liga, temporada, fecha_iso, 
                id_equipo_home, id_equipo_away, goles_home, goles_away, 
                resultado_1x2, odd_1, odd_x, odd_2
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?)
        """
        cursor.execute(sql_partidos, (id_partido, id_liga, temporada, fecha_iso, id_home, id_away, odd_1, odd_x, odd_2))

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
            id_partido, id_liga, temporada, fecha_iso, id_home, id_away,
            h_gf, h_gc, h_xgf, h_xgc, a_gf, a_gc, a_xgf, a_xgc, diff_xg, diff_gf
        ))

        conn.commit()
        print(f"[EXITO] Partido registrado: ID {id_partido} | Fecha/Hora: {fecha_iso}")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] No se pudo registrar el partido: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Se ajustan las cuotas para asegurar partidos con valor esperado positivo (EV+) en X y 2
    partidos_nuevos = [
        ("ENG1_2526_8_17", "ENG1", "2025-2026", "2026-08-22 15:00", 8, 17, 2.10, 4.20, 5.50),
        ("ENG1_2526_18_3", "ENG1", "2025-2026", "2026-08-22 17:30", 18, 3, 3.80, 4.50, 2.40),
        ("ENG1_2526_9_10", "ENG1", "2025-2026", "2026-08-23 14:00", 9, 10, 1.95, 4.10, 5.00)
    ]

    print("\n--- REGENERANDO Y CARGANDO PARTIDOS FUTUROS ---")
    for p in partidos_nuevos:
        insertar_partido_futuro(*p)
        