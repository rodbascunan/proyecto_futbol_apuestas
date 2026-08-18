import pandas as pd
import numpy as np

def simular_apuestas(cuota_local=2.10, cuota_empate=3.30, cuota_visita=3.50, min_ev=0.05, bankroll_inicial=1000, stake=20):
    df = pd.read_csv("predicciones_con_probabilidades.csv")
    
    bank = bankroll_inicial
    historial_bank = []
    apuestas_realizadas = 0
    apuestas_ganadas = 0

    for _, row in df.iterrows():
        # Calcular EV para cada opción
        ev_local = (row['prob_local'] * cuota_local) - 1
        ev_empate = (row['prob_empate'] * cuota_empate) - 1
        ev_visita = (row['prob_visita'] * cuota_visita) - 1

        apuesta_seleccionada = None
        cuota_aplicada = 0
        resultado_real = row['target_1x2']

        # Criterio de Selección: Apostar solo si el EV supera el umbral (min_ev)
        if ev_local >= min_ev and ev_local > ev_empate and ev_local > ev_visita:
            apuesta_seleccionada = 1
            cuota_aplicada = cuota_local
        elif ev_visita >= min_ev and ev_visita > ev_local and ev_visita > ev_empate:
            apuesta_seleccionada = 2
            cuota_aplicada = cuota_visita
        elif ev_empate >= min_ev and ev_empate > ev_local and ev_empate > ev_visita:
            apuesta_seleccionada = 0
            cuota_aplicada = cuota_empate

        if apuesta_seleccionada is not None:
            apuestas_realizadas += 1
            if apuesta_seleccionada == resultado_real:
                ganancia = (stake * cuota_aplicada) - stake
                bank += ganancia
                apuestas_ganadas += 1
            else:
                bank -= stake
        
        historial_bank.append(bank)

    roi = ((bank - bankroll_inicial) / (apuestas_realizadas * stake)) * 100 if apuestas_realizadas > 0 else 0
    win_rate = (apuestas_ganadas / apuestas_realizadas) * 100 if apuestas_realizadas > 0 else 0

    print("="*60)
    print("RESULTADOS DEL BACKTESTING (SIMULACIÓN DE APUESTAS DE VALOR)")
    print("="*60)
    print(f"Bankroll Inicial:     ${bankroll_inicial:.2f}")
    print(f"Bankroll Final:       ${bank:.2f}")
    print(f"Beneficio Neto:       ${bank - bankroll_inicial:.2f}")
    print(f"Total Apuestas:       {apuestas_realizadas}")
    print(f"Tasa de Acierto:      {win_rate:.2f}%")
    print(f"ROI (Retorno s/Inversión): {roi:.2f}%")
    print("="*60)

if __name__ == "__main__":
    simular_apuestas()
    