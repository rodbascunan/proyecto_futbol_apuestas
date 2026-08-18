import pandas as pd
import numpy as np

def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    t = str(texto).lower().strip()
    # Eliminar palabras recurrentes para facilitar el match
    for palabra in ["fc", "cf", "sc", "club", "real", "deportivo", "atletico", "atlético", "united", "utd", "city"]:
        t = t.replace(palabra, "")
    return "".join(t.split())

def unir_cuotas_definitive():
    print("[1/4] Cargando datasets...")
    try:
        df_xg = pd.read_csv("dataset_xg_features.csv")
    except FileNotFoundError:
        print("[ERROR] No se encontró 'dataset_xg_features.csv'")
        return

    # CSV consolidado descargado de Football-Data
    nombre_csv_cuotas = "cuotas_mercado_real.csv"
    try:
        df_cuotas = pd.read_csv(nombre_csv_cuotas, low_memory=False)
    except FileNotFoundError:
        print(f"[ERROR] No se encontró '{nombre_csv_cuotas}' en la carpeta actual.")
        return

    print("[2/4] Normalizando fechas y horas...")
    # Estandarizar fecha en xG (remover HH:MM:SS)
    col_date_xg = next(c for c in ["fecha", "date"] if c in df_xg.columns)
    df_xg["fecha_clean"] = pd.to_datetime(df_xg[col_date_xg]).dt.strftime("%Y-%m-%d")

    # Estandarizar fecha en Cuotas (Football-Data suele usar DD/MM/YYYY)
    col_date_cuotas = next(c for c in ["Date", "fecha", "date"] if c in df_cuotas.columns)
    df_cuotas["fecha_clean"] = pd.to_datetime(df_cuotas[col_date_cuotas], dayfirst=True, errors='coerce').dt.strftime("%Y-%m-%d")

    print("[3/4] Normalizando nombres de equipos...")
    col_home_xg = next(c for c in ["equipo_home", "home_team", "local"] if c in df_xg.columns)
    col_home_cuotas = next(c for c in ["HomeTeam", "home_team", "Home", "local"] if c in df_cuotas.columns)

    df_xg["home_clean"] = df_xg[col_home_xg].apply(normalizar_texto)
    df_cuotas["home_clean"] = df_cuotas[col_home_cuotas].apply(normalizar_texto)

    # Identificar columnas de cuotas reales (preferencia: Pinnacle > Bet365 > Promedio)
    c_h = next((c for c in ["PSH", "B365H", "AvgH", "MaxH"] if c in df_cuotas.columns), None)
    c_d = next((c for c in ["PSD", "B365D", "AvgD", "MaxD"] if c in df_cuotas.columns), None)
    c_a = next((c for c in ["PSA", "B365A", "AvgA", "MaxA"] if c in df_cuotas.columns), None)

    if not all([c_h, c_d, c_a]):
        print(f"[ERROR] No se encontraron columnas de cuotas 1X2 válidas en {nombre_csv_cuotas}.")
        return

    print(f"Usando columnas de cuota: Home='{c_h}', Draw='{c_d}', Away='{c_a}'")

    # Limpiar duplicados en el dataset de cuotas para evitar multiplicación de filas
    df_cuotas_clean = df_cuotas.drop_duplicates(subset=["fecha_clean", "home_clean"]).copy()

    print("[4/4] Realizando Merge estricto...")
    df_merged = pd.merge(
        df_xg,
        df_cuotas_clean[["fecha_clean", "home_clean", c_h, c_d, c_a]],
        on=["fecha_clean", "home_clean"],
        how="inner"
    )

    # Reemplazar columnas de cuota viejas o crear nuevas estandarizadas
    df_merged["cuota_home"] = pd.to_numeric(df_merged[c_h], errors='coerce')
    df_merged["cuota_draw"] = pd.to_numeric(df_merged[c_d], errors='coerce')
    df_merged["cuota_away"] = pd.to_numeric(df_merged[c_a], errors='coerce')

    # Dropear cualquier fila que tenga cuota nula o <= 1.0
    df_final = df_merged.dropna(subset=["cuota_home", "cuota_draw", "cuota_away"]).copy()
    df_final = df_final[(df_final["cuota_home"] > 1.0) & (df_final["cuota_draw"] > 1.0) & (df_final["cuota_away"] > 1.0)]

    # Eliminar auxiliares
    df_final = df_final.drop(columns=["fecha_clean", "home_clean"])

    archivo_salida = "dataset_xg_con_cuotas.csv"
    df_final.to_csv(archivo_salida, index=False)

    print("\n" + "="*60)
    print(f"[ÉXITO ABSOLUTO] Se cruzaron {len(df_final)} partidos con CUOTAS VARIABLES REALES.")
    print(f"Archivo generado: {archivo_salida}")
    print("="*60)

if __name__ == "__main__":
    unir_cuotas_definitive()

    