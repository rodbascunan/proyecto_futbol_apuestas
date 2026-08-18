import numpy as np
import pandas as pd


def buscar_columna(df, posibles_nombres):
    for nombre in posibles_nombres:
        if nombre in df.columns:
            return nombre
    raise KeyError(
        f"No se encontró ninguna de las columnas esperadas: {posibles_nombres}. Columnas disponibles: {list(df.columns)}"
    )


def calcular_features_xg(archivo_csv="dataset_xg_consolidado.csv"):
    print("[1/3] Cargando dataset maestro de xG...")
    df = pd.read_csv(archivo_csv)

    col_home_team = buscar_columna(df, ["home_team", "home", "team_h"])
    col_away_team = buscar_columna(df, ["away_team", "away", "team_a"])

    col_home_score = buscar_columna(
        df,
        [
            "home_score",
            "home_goals",
            "goals_home",
            "score_h",
            "h_goals",
            "goals_h",
        ],
    )
    col_away_score = buscar_columna(
        df,
        [
            "away_score",
            "away_goals",
            "goals_away",
            "score_a",
            "a_goals",
            "goals_a",
        ],
    )

    col_home_xg = buscar_columna(df, ["home_xg", "xg_home", "xg_h", "h_xg"])
    col_away_xg = buscar_columna(df, ["away_xg", "xg_away", "xg_a", "a_xg"])

    col_date = buscar_columna(df, ["date", "fecha", "datetime"])
    df["date"] = pd.to_datetime(df[col_date])
    
    # 1. ORDENAR POR FECHA Y CREAR UN ID ÚNICO REAL
    df = df.sort_values("date").reset_index(drop=True)
    df["id_partido_unico"] = (
        df["date"].dt.strftime("%Y%m%d")
        + "_"
        + df[col_home_team].astype(str)
        + "_"
        + df[col_away_team].astype(str)
    )

    print("[2/3] Transformando dataset a estructura por equipo/partido...")

    registros_equipos = []

    for idx, row in df.iterrows():
        liga_val = row.get("liga_id", row.get("league", "Liga"))
        temp_val = row.get("temporada_id", row.get("season", "Temp"))

        # Local
        registros_equipos.append(
            {
                "id_partido": row["id_partido_unico"],
                "fecha": row["date"],
                "liga": liga_val,
                "temporada": temp_val,
                "equipo": row[col_home_team],
                "rival": row[col_away_team],
                "es_local": 1,
                "goles_favor": row[col_home_score],
                "goles_contra": row[col_away_score],
                "xg_favor": row[col_home_xg],
                "xg_contra": row[col_away_xg],
            }
        )
        # Visitante
        registros_equipos.append(
            {
                "id_partido": row["id_partido_unico"],
                "fecha": row["date"],
                "liga": liga_val,
                "temporada": temp_val,
                "equipo": row[col_away_team],
                "rival": row[col_home_team],
                "es_local": 0,
                "goles_favor": row[col_away_score],
                "goles_contra": row[col_home_score],
                "xg_favor": row[col_away_xg],
                "xg_contra": row[col_home_xg],
            }
        )

    df_teams = pd.DataFrame(registros_equipos)

    print(
        "[3/3] Calculando promedios móviles y ratio de conversión (5 y 10 partidos previos con SHIFT)..."
    )

    # Ordenar estrictamente por Equipo y Fecha para los rolling features
    df_teams = df_teams.sort_values(["equipo", "fecha"]).reset_index(drop=True)

    for window in [5, 10]:
        df_teams[f"xg_favor_roll_{window}"] = df_teams.groupby("equipo")[
            "xg_favor"
        ].transform(lambda x: x.shift(1).rolling(window, min_periods=3).mean())

        df_teams[f"xg_contra_roll_{window}"] = df_teams.groupby("equipo")[
            "xg_contra"
        ].transform(lambda x: x.shift(1).rolling(window, min_periods=3).mean())

        df_teams[f"xg_diff_roll_{window}"] = (
            df_teams[f"xg_favor_roll_{window}"]
            - df_teams[f"xg_contra_roll_{window}"]
        )

    # Eficiencia de conversión (Goles Reales / xG en últimos 10 partidos PREVIOS)
    goles_roll_10 = df_teams.groupby("equipo")["goles_favor"].transform(
        lambda x: x.shift(1).rolling(10, min_periods=3).sum()
    )
    xg_roll_10 = df_teams.groupby("equipo")["xg_favor"].transform(
        lambda x: x.shift(1).rolling(10, min_periods=3).sum()
    )
    df_teams["conversion_ratio_10"] = goles_roll_10 / (xg_roll_10 + 1e-5)

    # Reconstruir la vista de partido cruzando por id_partido único
    df_home = df_teams[df_teams["es_local"] == 1].copy()
    df_away = df_teams[df_teams["es_local"] == 0].copy()

    df_features = pd.merge(
        df_home,
        df_away,
        on=["id_partido", "fecha", "liga", "temporada"],
        suffixes=("_home", "_away"),
    )

    # Reordenar por fecha final
    df_features = df_features.sort_values("fecha").reset_index(drop=True)

    archivo_salida = "dataset_xg_features.csv"
    df_features.to_csv(archivo_salida, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 50)
    print(
        f"[ÉXITO] Dataset procesado correctamente guardado en: {archivo_salida}"
    )
    print(f"Total partidos procesados con variables: {len(df_features)}")
    print("=" * 50)


if __name__ == "__main__":
    calcular_features_xg()
    