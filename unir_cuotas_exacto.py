import pandas as pd

def unir_cuotas_exacto():
    print("=" * 70)
    print("[1/3] Cargando archivos con encoding y columnas correctas...")
    print("=" * 70)

    try:
        df_xg = pd.read_csv("dataset_xg_features.csv", encoding="utf-8-sig")
        df_cuotas = pd.read_csv("cuotas_mercado_real.csv", encoding="utf-8-sig", low_memory=False)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return

    # Normalizar nombres de columnas (eliminar espacios extra)
    df_cuotas.columns = df_cuotas.columns.str.strip()

    # Identificar columna de equipo local
    col_home_xg = next(c for c in ["equipo_home", "home_team", "local"] if c in df_xg.columns)
    col_home_cuotas = next(c for c in ["HomeTeam", "home_team", "Home", "local"] if c in df_cuotas.columns)

    # Mapear las columnas específicas detectadas en tu imagen
    col_h = next((c for c in ["Bet365 home odds", "B365H", "PSH", "AvgH"] if c in df_cuotas.columns), None)
    col_d = next((c for c in ["Bet365 draw odds", "B365D", "PSD", "AvgD"] if c in df_cuotas.columns), None)
    col_a = next((c for c in ["Bet365 away odds", "B365A", "PSA", "AvgA"] if c in df_cuotas.columns), None)

    if not all([col_h, col_d, col_a]):
        print(f"[ERROR] No se encontraron las columnas de cuotas. Columnas detectadas: {list(df_cuotas.columns[:10])}")
        return

    print(f"Columnas asignadas -> Local: '{col_h}', Empate: '{col_d}', Visita: '{col_a}'")

    # Limpiar y normalizar nombres de equipos
    def clean_team(t):
        if pd.isna(t):
            return ""
        txt = str(t).lower().strip()
        for kw in ["fc", "cf", "sc", "club", "real", "deportivo", "atletico", "atlético", "united", "utd", "city"]:
            txt = txt.replace(kw, "")
        return "".join(txt.split())

    df_xg["clean_home"] = df_xg[col_home_xg].apply(clean_team)
    df_cuotas["clean_home"] = df_cuotas[col_home_cuotas].apply(clean_team)

    # Convertir cuotas a formato numérico
    for c in [col_h, col_d, col_a]:
        df_cuotas[c] = pd.to_numeric(df_cuotas[c], errors="coerce")

    print("\n[2/3] Calculando cuotas promedio por equipo...")
    mapa_h = df_cuotas.groupby("clean_home")[col_h].mean().to_dict()
    mapa_d = df_cuotas.groupby("clean_home")[col_d].mean().to_dict()
    mapa_a = df_cuotas.groupby("clean_home")[col_a].mean().to_dict()

    df_xg["cuota_home"] = df_xg["clean_home"].map(mapa_h)
    df_xg["cuota_draw"] = df_xg["clean_home"].map(mapa_d)
    df_xg["cuota_away"] = df_xg["clean_home"].map(mapa_a)

    # Eliminar columna auxiliar y limpiar nulos
    df_xg = df_xg.drop(columns=["clean_home"])
    df_final = df_xg.dropna(subset=["cuota_home", "cuota_draw", "cuota_away"]).copy()

    archivo_salida = "dataset_xg_con_cuotas.csv"
    df_final.to_csv(archivo_salida, index=False, encoding="utf-8")

    print("\n[3/3] Muestra de datos cruzados con éxito:")
    print(df_final[[col_home_xg, "cuota_home", "cuota_draw", "cuota_away"]].head(10).to_string(index=False))

    print("\n" + "=" * 70)
    print(f"[ÉXITO] Archivo '{archivo_salida}' generado correctamente con {len(df_final)} registros.")
    print("=" * 70)

if __name__ == "__main__":
    unir_cuotas_exacto()

    