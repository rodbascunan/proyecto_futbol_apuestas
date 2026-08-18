"""
Analisis: % de victoria, cuota promedio y ROI segun la diferencia de
posiciones en la tabla entre local y visita, separado por liga y por
seleccion (local/empate/visita).

Intervalos de diferencia (en valor absoluto): 1-5, 6-10, 11-15, 16-20+
Ademas se indica quien esta mejor posicionado (local o visita), porque
el efecto NO deberia ser simetrico (jugar de local ya de por si ayuda).
"""

import sqlite3
import pandas as pd
from posiciones import calcular_posiciones

DB_PATH = "futbol_apuestas.db"
TRAIN_SEASONS = ["2021-2022", "2022-2023", "2023-2024", "2024-2025"]
LEAGUES = ["T1", "G1", "SC0"]
STAKE = 10.0


def bucket_diferencia(abs_diff):
    if abs_diff <= 5:
        return "1-5"
    elif abs_diff <= 10:
        return "6-10"
    elif abs_diff <= 15:
        return "11-15"
    else:
        return "16+"


def cargar_odds_1x2(db_path, bookmaker="Market Avg"):
    conn = sqlite3.connect(db_path)
    odds = pd.read_sql(
        """SELECT m.match_id, o.selection, o.price
           FROM odds o JOIN matches m ON m.match_id = o.match_id
           WHERE o.bookmaker = ? AND o.market_type='1x2' AND o.snapshot='open'""",
        conn, params=(bookmaker,),
    )
    conn.close()
    if odds.empty:
        return pd.DataFrame(columns=["odds_home", "odds_draw", "odds_away"])
    wide = odds.pivot(index="match_id", columns="selection", values="price")
    wide.columns = [f"odds_{c}" for c in wide.columns]
    return wide


def analizar_liga(league_code, season_labels=TRAIN_SEASONS, db_path=DB_PATH, min_jugados=5):
    pos = calcular_posiciones(db_path, league_code, season_labels, min_jugados=min_jugados)
    odds = cargar_odds_1x2(db_path)

    df = pos.merge(odds, on="match_id", how="left")
    df = df.dropna(subset=["home_pos", "away_pos", "odds_home", "odds_draw", "odds_away"])

    if df.empty:
        print(f"  [SALTADO] {league_code}: sin suficientes datos (posiciones + cuotas cruzadas).")
        return None

    df["diff"] = df["home_pos"] - df["away_pos"]  # negativo = local mejor posicionado
    df["abs_diff"] = df["diff"].abs()
    df["mejor_posicionado"] = df["diff"].apply(lambda d: "local" if d < 0 else ("visita" if d > 0 else "igual"))
    df["bucket"] = df["abs_diff"].apply(bucket_diferencia)

    filas = []
    for (mejor, bucket), grupo in df.groupby(["mejor_posicionado", "bucket"]):
        if mejor == "igual":
            continue
        n = len(grupo)
        for sel in ["home", "draw", "away"]:
            gano = (grupo["actual"] == sel)
            cuota_prom = grupo[f"odds_{sel}"].mean()
            acierto = gano.mean() * 100
            profit = (grupo.loc[gano, f"odds_{sel}"] - 1).sum() * STAKE - (~gano).sum() * STAKE
            roi = profit / (n * STAKE) * 100
            filas.append({
                "liga": league_code, "mejor_posicionado": mejor, "diferencia_posiciones": bucket,
                "n_partidos": n, "seleccion": sel, "cuota_promedio": round(cuota_prom, 2),
                "acierto_pct": round(acierto, 1), "roi_pct": round(roi, 2),
            })

    return pd.DataFrame(filas)


if __name__ == "__main__":
    todas = []
    for liga in LEAGUES:
        print(f"\n=== {liga} ===")
        res = analizar_liga(liga)
        if res is not None and not res.empty:
            todas.append(res)
            orden_bucket = pd.Categorical(res["diferencia_posiciones"], categories=["1-5", "6-10", "11-15", "16+"], ordered=True)
            res = res.assign(_orden=orden_bucket).sort_values(["mejor_posicionado", "_orden", "seleccion"]).drop(columns="_orden")
            print(res.to_string(index=False))

    if todas:
        consolidado = pd.concat(todas, ignore_index=True)
        consolidado.to_csv("analisis_posiciones_roi.csv", index=False)
        print("\nGuardado en analisis_posiciones_roi.csv")
