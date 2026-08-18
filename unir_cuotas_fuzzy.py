import pandas as pd
from difflib import get_close_matches

def unir_fuzzy():
    print("[1/3] Cargando datasets...")
    df_xg = pd.read_csv("dataset_xg_features.csv")
    df_cuotas = pd.read_csv("cuotas_mercado_real.csv", low_memory=False)

    col_date_xg = next(c for c in ["fecha", "date"] if c in df_xg.columns)
    col_home_xg = next(c for c in ["equipo_home", "home_team", "local"] if c in df_xg.columns)

    col_date_cuotas = next(c for c in ["Date", "fecha", "date"] if c in df_cuotas.columns)
    col_home_cuotas = next(c for c in ["HomeTeam", "home_team", "Home", "local"] if c in df_cuotas.columns)

    # Identificar columnas de cuotas reales
    c_h = next((c for c in ["PSH", "B365H", "AvgH", "MaxH"] if c in df_cuotas.columns), None)
    c_d = next((c for c in ["PSD", "B365D", "AvgD", "MaxD"] if c in df_cuotas.columns), None)
    c_a = next((c for c in ["PSA", "B365A", "AvgA", "MaxA"] if c in df_cuotas.columns), None)

    # Convertir fechas
    df_xg["f_clean"] = pd.to_datetime(df_xg[col_date_xg]).dt.strftime("%Y-%m-%d")
    df_cuotas["f_clean"] = pd.to_datetime(df_cuotas[col_date_cuotas], dayfirst=True, errors='coerce').dt.strftime("%Y-%m-%d")

    # Mapeo de equipos en cuotas por fecha
    cuotas_dict = {}
    for _, row in df_cuotas.iterrows():
        key = (row["f_clean"], str(row[col_home_cuotas]).lower().strip())
        cuotas_dict[key] = (row[c_h], row[c_d], row[c_a])

    print("[2/3] Buscando coincidencias flexibles...")
    cuotas_h, cuotas_d, cuotas_a = [], [], []
    matches_encontrados = 0

    for _, row in df_xg.iterrows():
        fecha = row["f_clean"]
        equipo = str(row[col_home_xg]).lower().strip()
        
        # Equipos disponibles en esa misma fecha en el CSV de cuotas
        equipos_fecha = [k[1] for k in cuotas_dict.keys() if k[0] == fecha]
        match = get_close_matches(equipo, equipos_fecha, n=1, cutoff=0.5)

        if match:
            h, d, a = cuotas_dict[(fecha, match[0])]
            cuotas_h.append(h)
            cuotas_d.append(d)
            cuotas_a.append(a)
            matches_encontrados += 1
        else:
            cuotas_h.append(None)
            cuotas_d.append(None)
            cuotas_a.append(None)

    df_xg["cuota_home"] = pd.to_numeric(cuotas_h, errors='coerce')
    df_xg["cuota_draw"] = pd.to_numeric(cuotas_d, errors='coerce')
    df_xg["cuota_away"] = pd.to_numeric(cuotas_a, errors='coerce')

    # Descartar los que no cruzaron
    df_final = df_xg.dropna(subset=["cuota_home", "cuota_draw", "cuota_away"]).copy()
    df_final = df_final.drop(columns=["f_clean"])

    df_final.to_csv("dataset_xg_con_cuotas.csv", index=False)

    print("\n" + "="*60)
    print(f"[RESULTADO] Se lograron cruzar {matches_encontrados} de {len(df_xg)} partidos.")
    print("Dataset guardado en 'dataset_xg_con_cuotas.csv'")
    print("="*60)

if __name__ == "__main__":
    unir_fuzzy()

    