import pandas as pd

def auditar_predicciones():
    archivo = "predicciones_cuotas_reales.csv"
    try:
        df = pd.read_csv(archivo)
    except FileNotFoundError:
        print(f"[ERROR] No se encuentra {archivo}")
        return

    print("="*70)
    print("AUDITORÍA DE PREVISIONES Y CUOTAS (MUESTRA DE EVALUACIÓN)")
    print("="*70)
    
    cols_interes = [
        c for c in [
            "fecha", "equipo_home", "equipo_away", 
            "prob_local", "prob_empate", "prob_visita",
            "cuota_home", "cuota_draw", "cuota_away", "target_1x2"
        ] if c in df.columns
    ]
    
    print(f"\nTotal registros en muestra: {len(df)}")
    print("\nMuestra de los primeros 10 partidos con sus cuotas y probabilidades:")
    print(df[cols_interes].head(10).to_string(index=False))

    # Calcular EV de cada opción para ver el sesgo
    if all(k in df.columns for k in ["prob_local", "cuota_home", "prob_empate", "cuota_draw", "prob_visita", "cuota_away"]):
        df["ev_home"] = (df["prob_local"] * df["cuota_home"]) - 1
        df["ev_draw"] = (df["prob_empate"] * df["cuota_draw"]) - 1
        df["ev_away"] = (df["prob_visita"] * df["cuota_away"]) - 1
        
        print("\n" + "-"*70)
        print("DISTRIBUCIÓN DE VALOR ESPERADO (EV):")
        print(f"Partidos con EV Local > 5%: {(df['ev_home'] > 0.05).sum()}")
        print(f"Partidos con EV Empate > 5%: {(df['ev_draw'] > 0.05).sum()}")
        print(f"Partidos con EV Visita > 5%: {(df['ev_away'] > 0.05).sum()}")
        print("-"*70)

if __name__ == "__main__":
    auditar_predicciones()
    