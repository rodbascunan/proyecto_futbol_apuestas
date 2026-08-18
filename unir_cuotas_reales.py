import pandas as pd
import numpy as np

def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    t = str(texto).lower().strip()
    for sufijo in ["fc", "cf", "sc", "club", "1913", "calcio", "deportivo", "atletico", "atlético"]:
        t = t.replace(sufijo, "")
    return "".join(t.split())

def unir_cuotas():
    print("[1/3] Cargando datasets...")
    try:
        df_xg = pd.read_csv("dataset_xg_features.csv")
    except FileNotFoundError:
        print("[ERROR CRÍTICO] No se encontró 'dataset_xg_features.csv'. Ejecuta primero procesar_features_xg.py")
        return

    # Ajusta aquí el nombre exacto de tu CSV con cuotas descargadas
    nombre_csv_cuotas = "predicciones_cuotas_reales.csv" 
    try:
        df_cuotas = pd.read_csv(nombre_csv_cuotas)
    except FileNotFoundError:
        print(f"[ERROR CRÍTICO] No se encontró '{nombre_csv_cuotas}'. Verifica el nombre exacto del archivo.")
        return

    print("\n--------------------------------------------------")
    print(f"Columnas detectadas en {nombre_csv_cuotas}:")
    print(list(df_cuotas.columns))
    print("--------------------------------------------------\n")

    # Búsqueda flexible de columnas con fallback None
    col_date_xg = next((c for c in ["fecha", "date", "Date"] if c in df_xg.columns), None)
    col_date_cuotas = next((c for c in ["fecha", "date", "Date", "Fecha"] if c in df_cuotas.columns), None)

    col_home_xg = next((c for c in ["equipo_home", "home_team", "equipo_home_home", "local"] if c in df_xg.columns), None)
    
    # Lista ampliada de posibles nombres de equipo local en el CSV de cuotas
    posibles_home_cuotas = [
        "home_team", "HomeTeam", "equipo_local", "Home", "home", 
        "Local", "equipo_home", "team_home", "Team1", "Home_Team"
    ]
    col_home_cuotas = next((c for c in posibles_home_cuotas if c in df_cuotas.columns), None)

    # Buscar columnas de cuotas
    c_h = next((c for c in ["cuota_home", "B365H", "PSH", "AvgH", "1", "H", "cuota_local"] if c in df_cuotas.columns), None)
    c_d = next((c for c in ["cuota_draw", "B365D", "PSD", "AvgD", "X", "D", "cuota_empate"] if c in df_cuotas.columns), None)
    c_a = next((c for c in ["cuota_away", "B365A", "PSA", "AvgA", "2", "A", "cuota_visita"] if c in df_cuotas.columns), None)

    if not col_home_cuotas:
        print(f"[ERROR] No se identificó la columna de equipo local en {nombre_csv_cuotas}.")
        print("Revisa la lista impresa arriba y agrega el nombre exacto a la lista 'posibles_home_cuotas' en el script.")
        return

    if not all([c_h, c_d, c_a]):
        print(f"[ERROR] No se encontraron las columnas de cuotas (Home: {c_h}, Draw: {c_d}, Away: {c_a}).")
        return

    # Normalizar Fechas
    df_xg["fecha_norm"] = pd.to_datetime(df_xg[col_date_xg]).dt.strftime("%Y-%m-%d")
    df_cuotas["fecha_norm"] = pd.to_datetime(df_cuotas[col_date_cuotas]).dt.strftime("%Y-%m-%d")

    # Normalizar Nombres
    df_xg["home_clean"] = df_xg[col_home_xg].apply(normalizar_texto)
    df_cuotas["home_clean"] = df_cuotas[col_home_cuotas].apply(normalizar_texto)

    print("[2/3] Cruzando datos por Fecha y Equipo Local...")
    df_merged = pd.merge(
        df_xg,
        df_cuotas[["fecha_norm", "home_clean", c_h, c_d, c_a]],
        on=["fecha_norm", "home_clean"],
        how="inner"
    )

    # Renombrar columnas estandarizadas
    df_merged = df_merged.rename(columns={
        c_h: "cuota_home",
        c_d: "cuota_draw",
        c_a: "cuota_away"
    })

    # Filtrar únicamente registros que hayan emparejado cuotas reales
    df_final = df_merged.dropna(subset=["cuota_home", "cuota_draw", "cuota_away"]).copy()
    df_final = df_final.drop(columns=["fecha_norm", "home_clean"])

    archivo_salida = "dataset_xg_con_cuotas.csv"
    df_final.to_csv(archivo_salida, index=False)
    
    print("\n" + "="*50)
    print(f"[ÉXITO] Se hizo match de {len(df_final)} partidos con CUOTAS REALES.")
    print(f"Archivo guardado en: {archivo_salida}")
    print("="*50)

if __name__ == "__main__":
    unir_cuotas()
