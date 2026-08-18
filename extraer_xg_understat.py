import pandas as pd
import soccerdata as sd


def extraer_xg_soccerdata(liga="ENG-Premier League", temporada="2025"):
    """Extrae datos de xG usando la librería soccerdata.

    Ligas válidas:
    - 'ENG-Premier League'
    - 'ESP-La Liga'
    - 'FRA-Ligue 1'
    - 'GER-Bundesliga'
    - 'ITA-Serie A'
    """
    print(
        f"[1/2] Inicializando scraper para {liga} (Temporada {temporada})..."
    )

    try:
        # Inicializar el scraper de Understat
        ws = sd.Understat(leagues=liga, seasons=temporada)

        print("[2/2] Descargando fixture y métricas xG...")
        # Obtener partidos/resultados con sus valores de xG
        df_partidos = ws.read_schedule()

        if df_partidos.empty:
            print("[AVISO] No se encontraron registros para la temporada.")
            return None

        # Resetear índice para facilitar el guardado en CSV
        df_partidos = df_partidos.reset_index()
        return df_partidos

    except Exception as e:
        print(f"[ERROR] Ocurrió una excepción al extraer datos: {e}")
        return None


if __name__ == "__main__":
    # Configuración de liga y temporada (Ligas válidas: 'ENG-Premier League', 'ESP-La Liga', etc.)
    LIGA = "ENG-Premier League"
    TEMPORADA = "2025"  # Puedes usar '2025', '2024' o formatos como '2526'

    print("=== EXTRACCIÓN AUTOMÁTICA DE xG CON SOCCERDATA ===")
    df_xg = extraer_xg_soccerdata(liga=LIGA, temporada=TEMPORADA)

    if df_xg is None or df_xg.empty:
        print(
            "\n[AVISO] Intentando con la temporada 2024 para obtener datos consolidados..."
        )
        TEMPORADA = "2024"
        df_xg = extraer_xg_soccerdata(liga=LIGA, temporada=TEMPORADA)

    if df_xg is not None and not df_xg.empty:
        archivo_csv = f"xg_{LIGA.replace(' ', '_')}_{TEMPORADA}.csv"
        df_xg.to_csv(archivo_csv, index=False, encoding="utf-8-sig")

        print("\n=== MUESTRA DE DATOS EXTRAÍDOS ===")
        # Selección de columnas principales para visualizar en consola
        columnas_mostrar = [
            col
            for col in [
                "date",
                "home_team",
                "away_team",
                "home_score",
                "away_score",
                "home_xg",
                "away_xg",
            ]
            if col in df_xg.columns
        ]
        print(df_xg[columnas_mostrar].head(10).to_string(index=False))

        print(f"\n[ÉXITO] Archivo guardado correctamente como: {archivo_csv}")
        print(f"Total partidos procesados con xG: {len(df_xg)}")
    else:
        print("\n[ERROR] No se pudieron obtener registros.")            