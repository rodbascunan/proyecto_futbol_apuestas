import sqlite3
import pandas as pd
import numpy as np
import pickle

DB_PATH = "data/futbol_master.db"
MODEL_PATH = "models/modelo_xgboost.pkl"

def cargar_modelo():
    """Carga el modelo XGBoost entrenado y la lista de variables requeridas."""
    try:
        with open(MODEL_PATH, "rb") as f:
            data = pickle.load(f)
        return data['model'], data['features']
    except Exception as e:
        try:
            with open("modelo_xgboost.pkl", "rb") as f:
                data = pickle.load(f)
            return data['model'], data['features']
        except Exception:
            print(f"[ERROR] No se pudo cargar el modelo desde ninguna ruta: {e}")
            return None, None

def cargar_partidos_futuros():
    """Consulta la base de datos para obtener únicamente partidos pendientes sin duplicados."""
    conn = sqlite3.connect(DB_PATH)
    
    # DISTINCT evita filas duplicadas producidas por joins múltiples
    query = """
        SELECT DISTINCT
            mf.*,
            p.odd_1, p.odd_x, p.odd_2,
            COALESCE(p.fecha_iso, mf.fecha) AS fecha_partido,
            eh.nombre_oficial AS local_nombre,
            ea.nombre_oficial AS visita_nombre
        FROM matriz_features mf
        INNER JOIN partidos p ON mf.id_partido = p.id_partido
        LEFT JOIN equipos eh ON mf.id_equipo_home = eh.id_equipo
        LEFT JOIN equipos ea ON mf.id_equipo_away = ea.id_equipo
        WHERE p.resultado_1x2 IS NULL 
           OR p.resultado_1x2 = '' 
           OR p.resultado_1x2 = 'None'
           OR mf.resultado IS NULL
           OR mf.resultado = ''
        ORDER BY fecha_partido ASC
    """
    
    try:
        df = pd.read_sql_query(query, conn)
    except Exception as e:
        print(f"[ERROR] Error al ejecutar la consulta en SQLite: {e}")
        df = pd.DataFrame()
        
    conn.close()
    
    if not df.empty:
        # Filtrar solo registros que tengan cuotas válidas
        df = df[
            df['odd_1'].notnull() & 
            df['odd_x'].notnull() & 
            df['odd_2'].notnull()
        ].copy()
    
    return df

def generar_predicciones(bankroll=1000.0, min_ev=0.02, max_ev=0.30, kelly_fraction=0.10, max_stake_pct=0.03, allowed_picks=['X', '2']):
    """Evalúa los partidos pendientes, calcula EV+, aplica Kelly y genera la cartelera final."""
    model, feature_cols = cargar_modelo()
    if not model:
        return

    df = cargar_partidos_futuros()
    if len(df) == 0:
        print("\n[INFO] No hay partidos futuros pendientes válidos en la base de datos.")
        return

    # Ajustar matriz de entrada a las variables esperadas por el modelo
    X = df.reindex(columns=feature_cols, fill_value=0)
    probs = model.predict_proba(X)
    
    df['prob_1'] = probs[:, 0]
    df['prob_x'] = probs[:, 1]
    df['prob_2'] = probs[:, 2]

    recomendaciones = []

    for idx, row in df.iterrows():
        odds = {'1': float(row['odd_1']), 'X': float(row['odd_x']), '2': float(row['odd_2'])}
        model_probs = {'1': row['prob_1'], 'X': row['prob_x'], '2': row['prob_2']}

        for pick in allowed_picks:
            odd = odds.get(pick)
            p_model = model_probs.get(pick)

            if odd and odd > 1.0:
                ev = (p_model * odd) - 1.0

                if min_ev <= ev <= max_ev:
                    b = odd - 1.0
                    kelly = (b * p_model - (1.0 - p_model)) / b if b > 0 else 0
                    stake_pct = max(0, min(kelly * kelly_fraction, max_stake_pct))
                    
                    if stake_pct <= 0:
                        continue

                    monto_sugerido = bankroll * stake_pct
                    fecha_str = str(row.get('fecha_partido', ''))[:16]

                    recomendaciones.append({
                        'Fecha_Hora': fecha_str,
                        'Local': str(row.get('local_nombre', 'Local'))[:14],
                        'Visita': str(row.get('visita_nombre', 'Visita'))[:14],
                        'Pick': pick,
                        'Cuota': float(odd),
                        'Prob_Modelo_%': round(p_model * 100, 1),
                        'EV_%': round(ev * 100, 1),
                        'Stake_%': round(stake_pct * 100, 2),
                        'Monto_Apostar': round(monto_sugerido, 2)
                    })

    df_rec = pd.DataFrame(recomendaciones)
    
    # Eliminación de duplicados exacta a nivel de recomendación
    if not df_rec.empty:
        df_rec = df_rec.drop_duplicates(subset=['Fecha_Hora', 'Local', 'Visita', 'Pick', 'Cuota']).reset_index(drop=True)

    imprimir_cartelera(df_rec, bankroll)

def imprimir_cartelera(df, bankroll):
    """Muestra la tabla formateada en la consola."""
    if len(df) == 0:
        print("\n[INFO] No se encontraron apuestas con EV+ para los partidos futuros analizados.")
        return

    print("\n" + "=" * 95)
    print(f"CARTELERA DE APUESTAS FUTURAS (BANKROLL BASE: ${bankroll:,.2f})")
    print("=" * 95)
    header = f"{'Fecha / Hora':<16} | {'Local':<14} | {'Visita':<14} | {'Pick':<4} | {'Cuota':<5} | {'Prob %':<6} | {'EV %':<5} | {'Stake %':<7} | {'Apostar':<8}"
    print(header)
    print("-" * 95)

    for _, r in df.iterrows():
        linea = f"{r['Fecha_Hora']:<16} | {r['Local']:<14} | {r['Visita']:<14} | {r['Pick']:^4} | {r['Cuota']:>5.2f} | {r['Prob_Modelo_%']:>5.1f}% | {r['EV_%']:>4.1f}% | {r['Stake_%']:>6.2f}% | ${r['Monto_Apostar']:>7.2f}"
        print(linea)
    print("=" * 95)

if __name__ == "__main__":
    generar_predicciones(
        bankroll=1000.0,
        min_ev=0.02,
        max_ev=0.30,
        kelly_fraction=0.10,
        max_stake_pct=0.03,
        allowed_picks=['X', '2']
    )
    