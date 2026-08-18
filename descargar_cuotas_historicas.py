import pandas as pd
import requests
import os
from io import StringIO
from thefuzz import process

# Ligas y temporadas a descargar
LIGAS = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "I1": "Serie A",
    "D1": "Bundesliga"
}

TEMPORADAS = ["2324", "2425", "2526"]

def descargar_csv_historico(codigo_liga, temporada):
    url = f"https://www.football-data.co.uk/mmz4281/{temporada}/{codigo_liga}.csv"
    print(f"Descargando datos desde: {url}...")
    
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    
    if res.status_code == 200:
        df = pd.read_csv(StringIO(res.text))
        return df
    else:
        print(f"[ERROR] No se pudo descargar {codigo_liga} para la temporada {temporada} (HTTP {res.status_code})")
        return None


def procesar_y_limpiar_cuotas(df_raw):
    """Extrae columnas esenciales: Fecha, Equipos, Cuotas Local/Empate/Visita."""
    # Nombres de columnas estándar en football-data.co.uk:
    # Date, HomeTeam, AwayTeam, B365H, B365D, B365A (Bet365) o PSH, PSD, PSA (Pinnacle)
    col_home = "HomeTeam"
    col_away = "AwayTeam"
    col_date = "Date"
    
    # Preferimos cuotas de Pinnacle (PS) si existen, sino Bet365 (B365)
    c_home = "PSH" if "PSH" in df_raw.columns else "B365H"
    c_draw = "PSD" if "PSD" in df_raw.columns else "B365D"
    c_away = "PSA" if "PSA" in df_raw.columns else "B365A"

    columnas_necesarias = [col_date, col_home, col_away, c_home, c_draw, c_away]
    
    # Filtrar solo si existen las columnas
    cols_existentes = [c for c in columnas_necesarias if c in df_raw.columns]
    df = df_raw[cols_existentes].copy()
    
    # Renombrar estandarizando el esquema
    df.rename(columns={
        col_date: "fecha",
        col_home: "equipo_home_hist",
        col_away: "equipo_away_hist",
        c_home: "cuota_home_real",
        c_draw: "cuota_draw_real",
        c_away: "cuota_away_real"
    }, inplace=True)

    # Formatear fecha a YYYY-MM-DD
    df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
    df.dropna(subset=["fecha", "cuota_home_real"], inplace=True)
    
    return df


def obtener_todas_las_cuotas_historicas():
    dfs_acumulados = []
    
    for cod_liga in LIGAS.keys():
        for temp in TEMPORADAS:
            df_temp = descargar_csv_historico(cod_liga, temp)
            if df_temp is not None:
                df_limpio = procesar_y_limpiar_cuotas(df_temp)
                dfs_acumulados.append(df_limpio)
                
    if dfs_acumulados:
        df_final = pd.concat(dfs_acumulados, ignore_index=True)
        print(f"\n[ÉXITO] Se procesaron {len(df_final)} partidos con cuotas históricas reales.")
        return df_final
    else:
        return pd.DataFrame()


def cruzar_con_dataset_xg(df_cuotas_historicas, archivo_xg="dataset_xg_features.csv"):
    if not os.path.exists(archivo_xg):
        print(f"[ERROR] No existe el archivo {archivo_xg}")
        return

    print("\n[1/2] Cargando dataset base de xG...")
    df_xg = pd.read_csv(archivo_xg)

    # Detectar nombres de columnas de equipos en el dataset xG
    col_home_xg = next((c for c in ["home_team", "equipo_home", "local"] if c in df_xg.columns), None)
    col_away_xg = next((c for c in ["away_team", "equipo_away", "visita"] if c in df_xg.columns), None)
    col_date_xg = next((c for c in ["fecha", "date"] if c in df_xg.columns), None)

    df_xg["fecha"] = pd.to_datetime(df_xg[col_date_xg], errors="coerce").dt.strftime("%Y-%m-%d")

    print("[2/2] Cruzando cuotas por Fecha y Nombre de Equipo (Fuzzy Match)...")
    
    # Fusionar por fecha primero
    df_merged = pd.merge(df_xg, df_cuotas_historicas, on="fecha", how="left")

    # Mapear cuotas exactas filtrando filas donde coincida el equipo local
    cuotas_home, cuotas_draw, cuotas_away = [], [], []

    for idx, row in df_merged.iterrows():
        # Si el cruce por fecha trajo coincidencia
        if pd.notna(row.get("equipo_home_hist")):
            score = process.extractOne(str(row[col_home_xg]), [str(row["equipo_home_hist"])])[1]
            if score >= 70:  # Coincidencia de nombre de equipo >= 70%
                cuotas_home.append(row["cuota_home_real"])
                cuotas_draw.append(row["cuota_draw_real"])
                cuotas_away.append(row["cuota_away_real"])
                continue
        
        # Si no hubo match directo o la fecha no cruzó
        cuotas_home.append(None)
        cuotas_draw.append(None)
        cuotas_away.append(None)

    df_merged["cuota_home"] = cuotas_home
    df_merged["cuota_draw"] = cuotas_draw
    df_merged["cuota_away"] = cuotas_away

    # Eliminar duplicados generados por el merge y guardar
    df_resultado = df_merged.drop_duplicates(subset=[col_date_xg, col_home_xg, col_away_xg]).copy()
    
    # Rellenar faltantes con estimación de overround si algún partido antiguo no estaba en la base
    df_resultado["cuota_home"] = df_resultado["cuota_home"].fillna(df_resultado.get("cuota_home_real", 2.10))
    df_resultado["cuota_draw"] = df_resultado["cuota_draw"].fillna(df_resultado.get("cuota_draw_real", 3.30))
    df_resultado["cuota_away"] = df_resultado["cuota_away"].fillna(df_resultado.get("cuota_away_real", 3.50))

    archivo_salida = "dataset_xg_con_cuotas.csv"
    df_resultado.to_csv(archivo_salida, index=False)
    print(f"\n[COMPLETADO] Guardado '{archivo_salida}' listo para reentrenamiento y backtesting.")


if __name__ == "__main__":
    df_cuotas = obtener_todas_las_cuotas_historicas()
    if not df_cuotas.empty:
        cruzar_con_dataset_xg(df_cuotas)
        