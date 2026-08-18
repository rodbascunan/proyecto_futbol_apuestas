import sqlite3
import pandas as pd
import numpy as np
import pickle

DB_PATH = "data/futbol_master.db"
MODEL_PATH = "models/modelo_xgboost.pkl"

def cargar_modelo():
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
            print(f"[ERROR] No se pudo cargar el modelo desde '{MODEL_PATH}': {e}")
            return None, None

def cargar_datos_backtest():
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT 
            mf.*,
            p.odd_1, 
            p.odd_x, 
            p.odd_2,
            COALESCE(p.resultado_1x2, mf.resultado) AS resultado_real,
            eh.nombre_oficial AS local_nombre,
            ea.nombre_oficial AS visita_nombre
        FROM matriz_features mf
        INNER JOIN partidos p ON mf.id_partido = p.id_partido
        LEFT JOIN equipos eh ON mf.id_equipo_home = eh.id_equipo
        LEFT JOIN equipos ea ON mf.id_equipo_away = ea.id_equipo
        ORDER BY mf.fecha ASC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    mapeo_res = {'H': '1', 'D': 'X', 'A': '2', '1': '1', 'X': 'X', '2': '2'}
    df['resultado_real'] = df['resultado_real'].astype(str).map(mapeo_res)
    
    df = df[
        df['resultado_real'].notnull() & 
        df['odd_1'].notnull() & 
        df['odd_x'].notnull() & 
        df['odd_2'].notnull()
    ].copy()
    
    return df

def ejecutar_backtest(initial_bankroll=1000.0, min_ev=0.02, max_ev=0.30, kelly_fraction=0.10, max_stake_pct=0.03, allowed_picks=['X', '2']):
    model, feature_cols = cargar_modelo()
    if not model:
        return

    df = cargar_datos_backtest()
    if len(df) == 0:
        print("[ERROR] No se encontraron partidos con cuotas y resultados completos para evaluar.")
        return

    X = df.reindex(columns=feature_cols, fill_value=0)
    probs = model.predict_proba(X)
    
    df['prob_1'] = probs[:, 0]
    df['prob_x'] = probs[:, 1]
    df['prob_2'] = probs[:, 2]

    bankroll = initial_bankroll
    peak_bankroll = initial_bankroll
    max_drawdown = 0.0

    historial_apuestas = []

    for idx, row in df.iterrows():
        odds = {'1': float(row['odd_1']), 'X': float(row['odd_x']), '2': float(row['odd_2'])}
        model_probs = {'1': row['prob_1'], 'X': row['prob_x'], '2': row['prob_2']}
        resultado_real = row['resultado_real']

        for pick, p_model in model_probs.items():
            # Filtro opcional para ignorar picks con rendimiento negativo (ej: Pick 1)
            if pick not in allowed_picks:
                continue

            odd = odds.get(pick)
            if odd > 1.0:
                ev = (p_model * odd) - 1.0

                if min_ev <= ev <= max_ev:
                    b = odd - 1.0
                    kelly = (b * p_model - (1.0 - p_model)) / b if b > 0 else 0
                    stake_pct = max(0, min(kelly * kelly_fraction, max_stake_pct))
                    
                    if stake_pct <= 0:
                        continue

                    monto_apostado = bankroll * stake_pct
                    acierto = (pick == resultado_real)

                    if acierto:
                        ganancia_neta = monto_apostado * (odd - 1.0)
                    else:
                        ganancia_neta = -monto_apostado

                    bankroll += ganancia_neta

                    if bankroll > peak_bankroll:
                        peak_bankroll = bankroll
                    drawdown = (peak_bankroll - bankroll) / peak_bankroll if peak_bankroll > 0 else 0
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown

                    historial_apuestas.append({
                        'Fecha': str(row.get('fecha', ''))[:10],
                        'Local': str(row.get('local_nombre', 'Local'))[:14],
                        'Visita': str(row.get('visita_nombre', 'Visita'))[:14],
                        'Pick': pick,
                        'Resultado_Real': resultado_real,
                        'Cuota': float(odd),
                        'EV_%': round(ev * 100, 1),
                        'Monto_Apostado': round(monto_apostado, 2),
                        'Acierto': 1 if acierto else 0,
                        'Resultado_Financiero': round(ganancia_neta, 2),
                        'Bankroll_Actual': round(bankroll, 2)
                    })

    df_res = pd.DataFrame(historial_apuestas)
    imprimir_resumen_backtest(df_res, initial_bankroll, bankroll, max_drawdown)

def imprimir_resumen_backtest(df, initial_bankroll, final_bankroll, max_drawdown):
    if len(df) == 0:
        print("\n[INFO] No se realizaron apuestas en la simulación con los filtros actuales.")
        return

    total_apuestas = len(df)
    total_ganadas = df['Acierto'].sum()
    win_rate = (total_ganadas / total_apuestas) * 100
    total_invertido = df['Monto_Apostado'].sum()
    beneficio_neto = final_bankroll - initial_bankroll
    roi = (beneficio_neto / total_invertido) * 100 if total_invertido > 0 else 0

    print("=" * 85)
    print("RESUMEN GENERAL OPTIMIZADO DEL BACKTESTING (PICKS X Y 2)")
    print("=" * 85)
    print(f"Bankroll Inicial    : ${initial_bankroll:,.2f}")
    print(f"Bankroll Final      : ${final_bankroll:,.2f}")
    print(f"Beneficio Neto      : ${beneficio_neto:,.2f}")
    print(f"ROI / Yield Total   : {roi:.2f}%")
    print(f"Total de Apuestas   : {total_apuestas}")
    print(f"Apuestas Ganadas    : {total_ganadas} ({win_rate:.1f}%)")
    print(f"Volumen Invertido   : ${total_invertido:,.2f}")
    print(f"Máximo Drawdown     : {max_drawdown * 100:.2f}%")
    print("=" * 85)

    print("\nRENDIMIENTO DESGLOSADO POR TIPO DE APUESTA (PICK):")
    print("-" * 85)
    for pick, group in df.groupby('Pick'):
        wins = group['Acierto'].sum()
        total = len(group)
        wr = (wins / total) * 100
        inv = group['Monto_Apostado'].sum()
        net = group['Resultado_Financiero'].sum()
        yield_pick = (net / inv) * 100 if inv > 0 else 0
        print(f"Pick {pick:<3} -> Apuestas: {total:<4} | WinRate: {wr:>5.1f}% | Invertido: ${inv:>8.2f} | Neto: ${net:>8.2f} | Yield: {yield_pick:>6.2f}%")
    print("=" * 85)

if __name__ == "__main__":
    # Simulación enfocada solo en Empates ('X') y Visitantes ('2')
    ejecutar_backtest(
        initial_bankroll=1000.0, 
        min_ev=0.02, 
        max_ev=0.30, 
        kelly_fraction=0.10, 
        max_stake_pct=0.03,
        allowed_picks=['X', '2']
    )
    