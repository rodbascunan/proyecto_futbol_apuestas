import numpy as np
import pandas as pd
from xgboost import XGBClassifier


def identificar_columnas(df):
    """Detecta dinámicamente los nombres de las columnas en el dataset."""
    col_home = next(
        (c for c in ["home_team", "equipo_home", "local", "equipo_local"] if c in df.columns),
        None,
    )
    col_away = next(
        (c for c in ["away_team", "equipo_away", "visita", "visitante", "equipo_visitante"] if c in df.columns),
        None,
    )
    col_ghome = next(
        (c for c in ["goles_favor_home", "home_score", "goles_home", "goles_local"] if c in df.columns),
        None,
    )
    col_gaway = next(
        (c for c in ["goles_favor_away", "away_score", "goles_away", "goles_visita"] if c in df.columns),
        None,
    )
    col_fecha = next((c for c in ["fecha", "date"] if c in df.columns), None)

    return col_home, col_away, col_ghome, col_gaway, col_fecha


def cargar_modelo_y_ultimas_features():
    df = pd.read_csv("dataset_xg_con_cuotas.csv")

    col_home, col_away, col_ghome, col_gaway, col_fecha = identificar_columnas(df)

    if not col_home or not col_away:
        raise KeyError(
            f"No se encontraron las columnas de equipos. Columnas en el CSV: {list(df.columns)}"
        )

    df[col_fecha] = pd.to_datetime(df[col_fecha])
    df = df.sort_values(col_fecha).reset_index(drop=True)

    # Recrear target 1X2
    df["target_1x2"] = np.where(
        df[col_ghome] > df[col_gaway], 1, np.where(df[col_ghome] < df[col_gaway], 2, 0)
    )

    df["tendencia_xg_home"] = df["xg_diff_roll_5_home"] - df["xg_diff_roll_10_home"]
    df["tendencia_xg_away"] = df["xg_diff_roll_5_away"] - df["xg_diff_roll_10_away"]
    df["diff_xg_10_h_vs_a"] = df["xg_favor_roll_10_home"] - df["xg_favor_roll_10_away"]

    features = [
        "xg_favor_roll_5_home",
        "xg_contra_roll_5_home",
        "xg_diff_roll_5_home",
        "xg_favor_roll_10_home",
        "xg_contra_roll_10_home",
        "xg_diff_roll_10_home",
        "conversion_ratio_10_home",
        "tendencia_xg_home",
        "xg_favor_roll_5_away",
        "xg_contra_roll_5_away",
        "xg_diff_roll_5_away",
        "xg_favor_roll_10_away",
        "xg_contra_roll_10_away",
        "xg_diff_roll_10_away",
        "conversion_ratio_10_away",
        "tendencia_xg_away",
        "diff_xg_10_h_vs_a",
    ]

    df_model = df.dropna(subset=features).copy()

    # Entrenar modelo
    model = XGBClassifier(
        n_estimators=120,
        learning_rate=0.03,
        max_depth=3,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=1.0,
        reg_lambda=1.0,
        random_state=42,
    )
    model.fit(df_model[features], df_model["target_1x2"])

    # Extraer la última foto de cada equipo
    ultimos_datos_equipos = {}
    todos_los_equipos = pd.concat([df_model[col_home], df_model[col_away]]).unique()

    for equipo in todos_los_equipos:
        partidos_local = df_model[df_model[col_home] == equipo]
        partidos_visita = df_model[df_model[col_away] == equipo]

        if not partidos_local.empty or not partidos_visita.empty:
            if partidos_local.empty:
                ultimo = partidos_visita.iloc[-1]
                prefix = "away"
            elif partidos_visita.empty:
                ultimo = partidos_local.iloc[-1]
                prefix = "home"
            else:
                if ultimo_l := partidos_local.iloc[-1][col_fecha] >= partidos_visita.iloc[-1][col_fecha]:
                    ultimo = partidos_local.iloc[-1]
                    prefix = "home"
                else:
                    ultimo = partidos_visita.iloc[-1]
                    prefix = "away"

            ultimos_datos_equipos[equipo] = {
                "xg_favor_roll_5": ultimo[f"xg_favor_roll_5_{prefix}"],
                "xg_contra_roll_5": ultimo[f"xg_contra_roll_5_{prefix}"],
                "xg_diff_roll_5": ultimo[f"xg_diff_roll_5_{prefix}"],
                "xg_favor_roll_10": ultimo[f"xg_favor_roll_10_{prefix}"],
                "xg_contra_roll_10": ultimo[f"xg_contra_roll_10_{prefix}"],
                "xg_diff_roll_10": ultimo[f"xg_diff_roll_10_{prefix}"],
                "conversion_ratio_10": ultimo[f"conversion_ratio_10_{prefix}"],
                "tendencia_xg": ultimo[f"tendencia_xg_{prefix}"],
            }

    return model, features, ultimos_datos_equipos


def predecir_jornada(proximos_partidos, bankroll=1000, min_ev=0.05):
    model, features, ultimos_datos = cargar_modelo_y_ultimas_features()

    filas_features = []
    partidos_validos = []

    for partido in proximos_partidos:
        local, visita = partido["local"], partido["visita"]

        if local in ultimos_datos and visita in ultimos_datos:
            d_local = ultimos_datos[local]
            d_visita = ultimos_datos[visita]

            feat_vector = [
                d_local["xg_favor_roll_5"],
                d_local["xg_contra_roll_5"],
                d_local["xg_diff_roll_5"],
                d_local["xg_favor_roll_10"],
                d_local["xg_contra_roll_10"],
                d_local["xg_diff_roll_10"],
                d_local["conversion_ratio_10"],
                d_local["tendencia_xg"],
                d_visita["xg_favor_roll_5"],
                d_visita["xg_contra_roll_5"],
                d_visita["xg_diff_roll_5"],
                d_visita["xg_favor_roll_10"],
                d_visita["xg_contra_roll_10"],
                d_visita["xg_diff_roll_10"],
                d_visita["conversion_ratio_10"],
                d_visita["tendencia_xg"],
                d_local["xg_favor_roll_10"] - d_visita["xg_favor_roll_10"],
            ]

            filas_features.append(feat_vector)
            partidos_validos.append(partido)
        else:
            print(f"[AVISO] No se encontraron datos acumulados para: {local} o {visita}")

    if not filas_features:
        print("\nNo hay partidos válidos para predecir. Revisa la escritura de los nombres de los equipos.")
        return

    X_proximos = pd.DataFrame(filas_features, columns=features)
    probs = model.predict_proba(X_proximos)

    print("\n" + "=" * 80)
    print(f"ANÁLISIS DE VALOR Y RECOMENDACIÓN DE APUESTAS (Bankroll: ${bankroll})")
    print("=" * 80)

    for idx, p in enumerate(partidos_validos):
        p_empate, p_local, p_visita = probs[idx][0], probs[idx][1], probs[idx][2]
        c_local, c_empate, c_visita = p["cuota_local"], p["cuota_empate"], p["cuota_visita"]

        ev_local = (p_local * c_local) - 1
        ev_empate = (p_empate * c_empate) - 1
        ev_visita = (p_visita * c_visita) - 1

        print(f"\n⚽ Partido: {p['local']} vs {p['visita']}")
        print(f"   Probabilidades Modelo -> Local: {p_local:.1%} | Empate: {p_empate:.1%} | Visita: {p_visita:.1%}")
        print(f"   Cuotas Mercado        -> Local: {c_local:.2f}  | Empate: {c_empate:.2f}  | Visita: {c_visita:.2f}")

        opciones = [
            ("LOCAL", ev_local, p_local, c_local),
            ("EMPATE", ev_empate, p_empate, c_empate),
            ("VISITA", ev_visita, p_visita, c_visita),
        ]
        opciones.sort(key=lambda x: x[1], reverse=True)
        best_op, best_ev, best_p, best_c = opciones[0]

        if best_ev >= min_ev:
            b = best_c - 1
            f_kelly = ((best_p * b) - (1 - best_p)) / b
            stake = max(0, min(f_kelly * 0.25, 0.05)) * bankroll

            print(f"   🔥 APUESTA CON VALOR DETECTADA: Apostar a {best_op}")
            print(f"      EV: +{best_ev*100:.1f}% | Stake Sugerido: ${stake:.2f} ({(stake/bankroll)*100:.1f}% del bank)")
        else:
            print("   ⛔ SIN APUESTA: Ningún mercado supera el umbral de EV mínimo (+5.0%).")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    from obtener_cuotas_api import obtener_proximos_partidos_con_cuotas

    # 1. Obtiene las cuotas en vivo/demostración y homologa los nombres automáticamente
    partidos_api = obtener_proximos_partidos_con_cuotas(usar_modo_prueba=True)

    # 2. Corre el análisis de Expected Value y Criterio de Kelly
    if partidos_api:
        predecir_jornada(partidos_api, bankroll=1000, min_ev=0.05)