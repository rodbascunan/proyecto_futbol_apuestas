import sqlite3
import pandas as pd
import numpy as np

DB_PATH = "data/futbol_master.db"

def cargar_datos_base():
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT 
            p.id_partido,
            p.id_liga,
            p.temporada,
            p.fecha_iso AS fecha,
            p.id_equipo_home,
            p.id_equipo_away,
            p.goles_home,
            p.goles_away,
            p.resultado_1x2 AS resultado,
            p.odd_1,
            p.odd_x,
            p.odd_2,
            x.xg_home,
            x.xg_away
        FROM partidos p
        LEFT JOIN metricas_xg x ON p.id_partido = x.id_partido
        ORDER BY p.fecha_iso ASC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def calcular_features(df, window=5):
    df['fecha'] = pd.to_datetime(df['fecha'])
    df = df.sort_values('fecha').reset_index(drop=True)

    # 1. Convertir cuotas en probabilidades implícitas del mercado (removiendo el overround/margen)
    def normalizar_cuotas(row):
        o1, ox, o2 = row['odd_1'], row['odd_x'], row['odd_2']
        if pd.notnull(o1) and pd.notnull(ox) and pd.notnull(o2) and o1 > 1 and ox > 1 and o2 > 1:
            inv1, invx, inv2 = 1.0/o1, 1.0/ox, 1.0/o2
            margin = inv1 + invx + inv2
            return inv1/margin, invx/margin, inv2/margin
        return np.nan, np.nan, np.nan

    probs_impl = df.apply(normalizar_cuotas, axis=1)
    df['mkt_prob_1'] = [p[0] for p in probs_impl]
    df['mkt_prob_x'] = [p[1] for p in probs_impl]
    df['mkt_prob_2'] = [p[2] for p in probs_impl]

    # 2. Métricas Móviles (Rolling Window)
    home_stats = df[['id_partido', 'fecha', 'id_equipo_home', 'goles_home', 'goles_away', 'xg_home', 'xg_away']].copy()
    home_stats.columns = ['id_partido', 'fecha', 'id_equipo', 'gf', 'gc', 'xg_f', 'xg_c']
    
    away_stats = df[['id_partido', 'fecha', 'id_equipo_away', 'goles_away', 'goles_home', 'xg_away', 'xg_home']].copy()
    away_stats.columns = ['id_partido', 'fecha', 'id_equipo', 'gf', 'gc', 'xg_f', 'xg_c']

    stats = pd.concat([home_stats, away_stats]).sort_values(['id_equipo', 'fecha']).reset_index(drop=True)
    stats[['gf', 'gc', 'xg_f', 'xg_c']] = stats[['gf', 'gc', 'xg_f', 'xg_c']].fillna(0)

    stats['rolling_gf'] = stats.groupby('id_equipo')['gf'].transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
    stats['rolling_gc'] = stats.groupby('id_equipo')['gc'].transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
    stats['rolling_xg_f'] = stats.groupby('id_equipo')['xg_f'].transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
    stats['rolling_xg_c'] = stats.groupby('id_equipo')['xg_c'].transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())

    home_features = stats[['id_partido', 'id_equipo', 'rolling_gf', 'rolling_gc', 'rolling_xg_f', 'rolling_xg_c']].copy()
    home_features.columns = ['id_partido', 'id_equipo_home', 'home_roll_gf', 'home_roll_gc', 'home_roll_xg_f', 'home_roll_xg_c']

    away_features = stats[['id_partido', 'id_equipo', 'rolling_gf', 'rolling_gc', 'rolling_xg_f', 'rolling_xg_c']].copy()
    away_features.columns = ['id_partido', 'id_equipo_away', 'away_roll_gf', 'away_roll_gc', 'away_roll_xg_f', 'away_roll_xg_c']

    df = df.drop(columns=['xg_home', 'xg_away'], errors='ignore')
    df = df.merge(home_features, on=['id_partido', 'id_equipo_home'], how='left')
    df = df.merge(away_features, on=['id_partido', 'id_equipo_away'], how='left')

    df['diff_roll_xg'] = df['home_roll_xg_f'] - df['away_roll_xg_f']
    df['diff_roll_gf'] = df['home_roll_gf'] - df['away_roll_gf']

    return df

def guardar_matriz_features(df):
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("matriz_features", conn, if_exists="replace", index=False)
    conn.close()
    print(f"[OK] Matriz de características guardada en 'matriz_features' ({len(df)} registros).")

if __name__ == "__main__":
    print("=" * 60)
    print("Construyendo Matriz de Características (Con Línea Base del Mercado)")
    print("=" * 60)

    df_base = cargar_datos_base()
    if len(df_base) > 0:
        df_processed = calcular_features(df_base)
        guardar_matriz_features(df_processed)

    print("\n" + "=" * 60)
    print("[ÉXITO] Proceso finalizado.")
    print("=" * 60)
    