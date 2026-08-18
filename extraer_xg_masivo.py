import os
import pandas as pd
import soccerdata as sd


def extraer_datos_xg():
    ligas = ["ENG-Premier League", "ESP-La Liga", "ITA-Serie A", "GER-Bundesliga", "FRA-Ligue 1"]
    temporadas = ["2122", "2223", "2324", "2425"]

    df_acumulado = []

    for liga in ligas:
        for temp in temporadas:
            print(f"Extrayendo {liga} - Temporada {temp}...")
            try:
                ud = sd.Understat(leagues=liga, seasons=temp)
                schedule = ud.read_schedule()

                # Reset de índice si viene indexado por partido
                schedule = schedule.reset_index()

                # Verificar y normalizar columnas requeridas
                cols_deseadas = {
                    "date": "date",
                    "home_team": "home_team",
                    "away_team": "away_team",
                    "home_xg": "home_xg",
                    "away_xg": "away_xg",
                    "home_score": "home_score",
                    "away_score": "away_score",
                }

                # Adaptar nombres si soccerdata usa 'home_goals' / 'away_goals'
                if "home_goals" in schedule.columns:
                    schedule["home_score"] = schedule["home_goals"]
                if "away_goals" in schedule.columns:
                    schedule["away_score"] = schedule["away_goals"]

                # Seleccionar columnas si existen
                cols_presentes = [c for c in cols_deseadas.keys() if c in schedule.columns]
                df_sub = schedule[cols_presentes].copy()
                df_sub["liga_id"] = liga
                df_sub["temporada_id"] = temp

                df_acumulado.append(df_sub)
            except Exception as e:
                print(f"Error extrayendo {liga} {temp}: {e}")

    if df_acumulado:
        df_final = pd.concat(df_acumulado, ignore_index=True)
        # Filtrar partidos no jugados (donde no hay goles ni xG registrado)
        df_final = df_final.dropna(subset=["home_xg", "home_score"])
        
        archivo_salida = "dataset_xg_consolidado.csv"
        df_final.to_csv(archivo_salida, index=False, encoding="utf-8-sig")
        print(f"\n[ÉXITO] Archivo consolidado guardado en: {archivo_salida}")
        print(f"Total partidos extraídos: {len(df_final)}")
        print(f"Columnas guardadas: {list(df_final.columns)}")


if __name__ == "__main__":
    extraer_datos_xg()