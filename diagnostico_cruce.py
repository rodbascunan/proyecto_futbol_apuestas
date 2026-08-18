import pandas as pd

def diagnosticar():
    print("=== DIAGNÓSTICO DE FORMATOS Y NOMBRES ===")
    
    # 1. Cargar xG
    df_xg = pd.read_csv("dataset_xg_features.csv")
    col_date_xg = next(c for c in ["fecha", "date"] if c in df_xg.columns)
    col_home_xg = next(c for c in ["equipo_home", "home_team", "local"] if c in df_xg.columns)
    
    # 2. Cargar Cuotas
    df_cuotas = pd.read_csv("cuotas_mercado_real.csv", low_memory=False)
    col_date_cuotas = next(c for c in ["Date", "fecha", "date"] if c in df_cuotas.columns)
    col_home_cuotas = next(c for c in ["HomeTeam", "home_team", "Home", "local"] if c in df_cuotas.columns)

    print("\n--- MUESTRA FECHAS Y NOMBRES EN 'dataset_xg_features.csv' ---")
    print(df_xg[[col_date_xg, col_home_xg]].head(5).to_string(index=False))

    print("\n--- MUESTRA FECHAS Y NOMBRES EN 'cuotas_mercado_real.csv' ---")
    print(df_cuotas[[col_date_cuotas, col_home_cuotas]].head(5).to_string(index=False))

    # Formatear fechas
    f_xg = pd.to_datetime(df_xg[col_date_xg]).dt.strftime("%Y-%m-%d").unique()[:5]
    f_cuotas = pd.to_datetime(df_cuotas[col_date_cuotas], dayfirst=True, errors='coerce').dt.strftime("%Y-%m-%d").dropna().unique()[:5]

    print("\n--- PRIMERAS 5 FECHAS CONVERTIDAS ---")
    print("Fechas xG:    ", list(f_xg))
    print("Fechas Cuotas:", list(f_cuotas))

if __name__ == "__main__":
    diagnosticar()
    