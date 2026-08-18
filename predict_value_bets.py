import sqlite3
import pandas as pd
import numpy as np
import pickle

DB_PATH = "data/futbol_master.db"
MODEL_PATH = "modelo_xgboost.pkl"

def cargar_modelo():
    try:
        with open(MODEL_PATH, "rb") as f:
            data = pickle.load(f)
        return data['model'], data['features']
    except Exception as e:
        print(f"[ERROR] No se pudo cargar el modelo desde '{MODEL_PATH}': {e}")
        return None, None

def cargar_partidos_evaluar():
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT 
            mf.*,
            p.odd_1, p.odd_x, p.odd_2,
            eh.nombre_oficial AS local_nombre,
            ea.nombre_oficial AS visita_nombre
        FROM matriz_features mf
        LEFT JOIN partidos p ON mf.id_partido = p.id_partido
        LEFT JOIN equipos eh ON mf.id_equipo_home = eh.id_equipo
        LEFT JOIN equipos ea ON mf.id_equipo_away = ea.id_equipo
        ORDER BY mf.fecha DESC
    """
    
    try:
        df = pd.read_sql_query(query, conn)
    except Exception:
        df = pd.read_sql_query("SELECT * FROM matriz_features ORDER BY fecha DESC", conn)

    conn.close()
    return df

def calcular_valor(df, model, feature_cols, min_ev=0.01, max_ev=0.25):
    if len(df) == 0:
        return pd.DataFrame(), pd.DataFrame()

    X = df.reindex(columns=feature_cols, fill_value=0)
    probs = model.predict_proba(X)
    
    df['prob_1'] = probs[:, 0]
    df['prob_x'] = probs[:, 1]
    df['prob_2'] = probs[:, 2]

    todas_las_predicciones = []
    apuestas_de_valor = []

    for idx, row in df.iterrows():
        local = str(row.get('local_nombre') or row.get('id_equipo_home', 'Local'))
        visita = str(row.get('visita_nombre') or row.get('id_equipo_away', 'Visita'))
        fecha = str(row.get('fecha', ''))[:10]

        todas_las_predicciones.append({
            'Fecha': fecha,
            'Local': local[:14],
            'Visita': visita[:14],
            'Prob_1_%': round(row['prob_1'] * 100, 1),
            'Prob_X_%': round(row['prob_x'] * 100, 1),
            'Prob_2_%': round(row['prob_2'] * 100, 1)
        })

        odds = {'1': row.get('odd_1'), 'X': row.get('odd_x'), '2': row.get('odd_2')}
        model_probs = {'1': row['prob_1'], 'X': row['prob_x'], '2': row['prob_2']}

        for pick, p_model in model_probs.items():
            odd = odds.get(pick)
            if pd.notnull(odd) and odd > 1.0:
                ev = (p_model * odd) - 1.0
                if min_ev <= ev <= max_ev:
                    b = odd - 1.0
                    kelly = (b * p_model - (1.0 - p_model)) / b if b > 0 else 0
                    kelly_sugerido = max(0, min(kelly * 0.10, 0.03))

                    apuestas_de_valor.append({
                        'Fecha': fecha,
                        'Local': local[:14],
                        'Visita': visita[:14],
                        'Pick': pick,
                        'Prob_%': round(p_model * 100, 1),
                        'Cuota': float(odd),
                        'EV_%': round(ev * 100, 1),
                        'Kelly_%': round(kelly_sugerido * 100, 2)
                    })

    return pd.DataFrame(apuestas_de_valor), pd.DataFrame(todas_las_predicciones)

def imprimir_tabla_valor(df):
    if len(df) == 0:
        return
    print("\n[ÉXITO] APUESTAS DE VALOR DETECTADAS")
    print("=" * 85)
    header = f"{'Fecha':<10} | {'Local':<14} | {'Visita':<14} | {'Pick':<4} | {'Prob_%':<6} | {'Cuota':<5} | {'EV_%':<5} | {'Kelly_%':<7}"
    print(header)
    print("-" * 85)
    
    for _, r in df.iterrows():
        linea = f"{r['Fecha']:<10} | {r['Local']:<14} | {r['Visita']:<14} | {r['Pick']:^4} | {r['Prob_%']:>6.1f} | {r['Cuota']:>5.2f} | {r['EV_%']:>5.1f} | {r['Kelly_%']:>7.2f}"
        print(linea)

def imprimir_tabla_predicciones(df):
    if len(df) == 0:
        return
    print("\nÚLTIMAS PREDICCIONES GENERADAS POR EL MODELO")
    print("=" * 85)
    header = f"{'Fecha':<10} | {'Local':<14} | {'Visita':<14} | {'Prob_1_%':<8} | {'Prob_X_%':<8} | {'Prob_2_%':<8}"
    print(header)
    print("-" * 85)
    
    for _, r in df.iterrows():
        linea = f"{r['Fecha']:<10} | {r['Local']:<14} | {r['Visita']:<14} | {r['Prob_1_%']:>8.1f} | {r['Prob_X_%']:>8.1f} | {r['Prob_2_%']:>8.1f}"
        print(linea)

if __name__ == "__main__":
    print("=" * 85)
    print("DETECCIÓN DE APUESTAS DE VALOR Y PREDICCIONES")
    print("=" * 85)

    model, feature_cols = cargar_modelo()

    if model:
        df = cargar_partidos_evaluar()
        df_value, df_pred = calcular_valor(df, model, feature_cols)
        
        if len(df_value) > 0:
            imprimir_tabla_valor(df_value.head(15))
        else:
            print("\n[INFO] No hay apuestas dentro de los parámetros de EV configurados.")

        if len(df_pred) > 0:
            imprimir_tabla_predicciones(df_pred.head(10))

    print("\n" + "=" * 85)
    print("[ÉXITO] Proceso finalizado.")
    print("=" * 85)
    