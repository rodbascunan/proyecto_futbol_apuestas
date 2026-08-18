import pandas as pd
import numpy as np

def auditar_simulacion():
    # Cargar predicciones guardadas
    df = pd.read_csv("predicciones_cuotas_reales.csv")
    
    print("=== AUDITORÍA DE VALOR ESPERADO (EV) Y CUOTAS ===")
    print(f"Total registros en test set: {len(df)}")
    
    # Detectar columnas de cuotas
    col_odd_h = next((c for c in ["cuota_home", "odd_h", "home_odd", "1"] if c in df.columns), None)
    col_odd_d = next((c for c in ["cuota_draw", "odd_d", "draw_odd", "X"] if c in df.columns), None)
    col_odd_a = next((c for c in ["cuota_away", "odd_a", "away_odd", "2"] if c in df.columns), None)
    
    print(f"Columnas de cuotas detectadas: Home='{col_odd_h}', Draw='{col_odd_d}', Away='{col_odd_a}'")
    
    if not all([col_odd_h, col_odd_d, col_odd_a]):
        print("[ERROR CRÍTICO] No se encontraron las columnas de cuotas en el CSV.")
        return

    # Calcular EV para cada mercado
    df["ev_home"] = (df["prob_local"] * df[col_odd_h]) - 1
    df["ev_draw"] = (df["prob_empate"] * df[col_odd_d]) - 1
    df["ev_away"] = (df["prob_visita"] * df[col_odd_a]) - 1
    
    df["max_ev"] = df[["ev_home", "ev_draw", "ev_away"]].max(axis=1)
    
    apuestas_ev5 = df[df["max_ev"] >= 0.05]
    
    print(f"\nPartidos con EV >= 5%: {len(apuestas_ev5)} de {len(df)} ({len(apuestas_ev5)/len(df)*100:.1f}%)")
    
    print("\n--- MUESTRA DE LAS PRIMERAS 5 APUESTAS DETECTADAS ---")
    cols_mostrar = ["fecha", "equipo_home", "equipo_away", "prob_local", "prob_empate", "prob_visita", col_odd_h, col_odd_d, col_odd_a, "max_ev"]
    cols_existentes = [c for c in cols_mostrar if c in df.columns]
    print(apuestas_ev5[cols_existentes].head())

if __name__ == "__main__":
    auditar_simulacion()
    