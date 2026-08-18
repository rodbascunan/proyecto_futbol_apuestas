import pandas as pd
import numpy as np

def detectar_columna(df, opciones):
    """Busca la primera columna presente en el dataframe que coincida con la lista de opciones."""
    for op in opciones:
        if op in df.columns:
            return op
    return None

def ejecutar_backtest_realista(csv_predicciones="predicciones_cuotas_reales.csv", bankroll_inicial=1000.0, min_ev=0.05):
    try:
        df = pd.read_csv(csv_predicciones)
    except Exception as e:
        print(f"[ERROR] No se pudo leer {csv_predicciones}: {e}")
        return

    # 1. Identificar columnas de Cuotas
    col_c_home = detectar_columna(df, ["cuota_home", "cuota_home_real", "cuota_local", "B365H", "PSH"])
    col_c_draw = detectar_columna(df, ["cuota_draw", "cuota_draw_real", "cuota_empate", "B365D", "PSD"])
    col_c_away = detectar_columna(df, ["cuota_away", "cuota_away_real", "cuota_visita", "B365A", "PSA"])

    # 2. Identificar columnas de Probabilidades del Modelo
    col_p_home = detectar_columna(df, ["prob_home", "prob_local", "prob_1", "p_home"])
    col_p_draw = detectar_columna(df, ["prob_draw", "prob_empate", "prob_0", "p_draw"])
    col_p_away = detectar_columna(df, ["prob_away", "prob_visita", "prob_2", "p_away"])

    # 3. Identificar columna Target/Resultado
    col_target = detectar_columna(df, ["target_1x2", "resultado_real", "target", "resultado"])

    # Verificar que existan las columnas mínimas
    if not (col_c_home and col_p_home and col_target):
        print(f"[ERROR] No se encontraron las columnas requeridas en el CSV.")
        print(f"Columnas disponibles en el CSV: {list(df.columns)}")
        return

    # Deduplicar por fecha y equipo local si existen
    col_home = detectar_columna(df, ["home_team", "equipo_home", "local"])
    col_date = detectar_columna(df, ["fecha", "date"])
    if col_home and col_date:
        df = df.drop_duplicates(subset=[col_date, col_home]).copy()

    bankroll = bankroll_inicial
    total_invertido = 0.0
    total_apuestas = 0
    apuestas_ganadas = 0

    print(f"\n==================================================")
    print(f"BACKTESTING CONTROLADO Y REALISTA (EV Min: {min_ev*100:.1f}%)")
    print(f"==================================================")

    for idx, row in df.iterrows():
        try:
            c_home = float(row[col_c_home]) if pd.notna(row[col_c_home]) else 0.0
            c_draw = float(row[col_c_draw]) if pd.notna(row[col_c_draw]) else 0.0
            c_away = float(row[col_c_away]) if pd.notna(row[col_c_away]) else 0.0

            p_home = float(row[col_p_home]) if pd.notna(row[col_p_home]) else 0.0
            p_draw = float(row[col_p_draw]) if pd.notna(row[col_p_draw]) else 0.0
            p_away = float(row[col_p_away]) if pd.notna(row[col_p_away]) else 0.0

            resultado_real = int(row[col_target])
        except (ValueError, TypeError):
            continue

        # Calcular EV para cada selección (1: Local, 0: Empate, 2: Visita)
        evs = {
            1: (p_home * c_home) - 1 if c_home > 1 else -1,
            0: (p_draw * c_draw) - 1 if c_draw > 1 else -1,
            2: (p_away * c_away) - 1 if c_away > 1 else -1
        }

        mejor_opcion = max(evs, key=evs.get)
        ev_max = evs[mejor_opcion]

        if ev_max >= min_ev:
            prob = p_home if mejor_opcion == 1 else (p_draw if mejor_opcion == 0 else p_away)
            cuota = c_home if mejor_opcion == 1 else (c_draw if mejor_opcion == 0 else c_away)

            # Criterio de Kelly Fraccionario (1/4 Kelly)
            f_kelly = ((prob * cuota) - 1) / (cuota - 1) if cuota > 1 else 0
            f_kelly = max(0, f_kelly) * 0.25

            # Stake máximo: 3% del bankroll inicial ($30 máximo por apuesta)
            stake = min(bankroll_inicial * f_kelly, bankroll_inicial * 0.03)

            if stake <= 0 or bankroll < stake:
                continue

            total_apuestas += 1
            total_invertido += stake
            bankroll -= stake

            if resultado_real == mejor_opcion:
                ganancia = stake * cuota
                bankroll += ganancia
                apuestas_ganadas += 1

    roi = ((bankroll - bankroll_inicial) / total_invertido * 100) if total_invertido > 0 else 0
    tasa_acierto = (apuestas_ganadas / total_apuestas * 100) if total_apuestas > 0 else 0

    print(f"Bankroll Inicial:      ${bankroll_inicial:.2f}")
    print(f"Bankroll Final:        ${bankroll:.2f}")
    print(f"Ganancia/Pérdida Neto:  ${bankroll - bankroll_inicial:.2f}")
    print(f"Total Invertido:       ${total_invertido:.2f}")
    print(f"Total Apuestas:        {total_apuestas}")
    print(f"Tasa de Acierto:       {tasa_acierto:.2f}%")
    print(f"ROI sobre lo Apostado: {roi:.2f}%")
    print(f"==================================================\n")

if __name__ == "__main__":
    ejecutar_backtest_realista(min_ev=0.05)
    