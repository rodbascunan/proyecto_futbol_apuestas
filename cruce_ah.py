"""
Cruza el proxy de "diferencia de gol esperada" (ataque/defensa reciente,
ventana movil de 5 partidos) contra la linea de handicap asiatico del
mercado. La idea: si nuestro proxy se aleja mucho de lo que la linea del
mercado implica, apostamos al lado que creemos que el mercado subestimo.
"""

import sqlite3
import pandas as pd
from goals_rolling import calcular_rolling_goals
from liquidacion_ah import liquidar_ah

DB_PATH = "futbol_apuestas.db"
TRAIN_SEASONS = ["2021-2022", "2022-2023", "2023-2024", "2024-2025"]
LEAGUES = LEAGUES = ["T1", "G1", "SC0"]
STAKE = 10.0


def cargar_odds_ah(db_path, league_code, bookmaker="Market Avg"):
    conn = sqlite3.connect(db_path)
    odds = pd.read_sql("""
        SELECT m.match_id, o.selection, o.price, o.handicap_line
        FROM odds o JOIN matches m ON m.match_id=o.match_id
        JOIN leagues l ON l.league_id=m.league_id
        WHERE o.bookmaker=? AND o.market_type='ah' AND o.snapshot='open' AND l.code=?
    """, conn, params=(bookmaker, league_code))
    conn.close()
    if odds.empty:
        return pd.DataFrame(columns=["match_id", "odds_home_ah", "odds_away_ah", "linea"])
    home = odds[odds["selection"] == "home_ah"][["match_id", "price", "handicap_line"]].rename(
        columns={"price": "odds_home_ah", "handicap_line": "linea"})
    away = odds[odds["selection"] == "away_ah"][["match_id", "price"]].rename(columns={"price": "odds_away_ah"})
    return home.merge(away, on="match_id", how="inner")


def bucket_desacuerdo(v):
    av = abs(v)
    if av < 0.5: return "<0.5"
    elif av < 1.0: return "0.5-1.0"
    elif av < 1.5: return "1.0-1.5"
    else: return "1.5+"


def analizar_liga_ah(league_code):
    df = calcular_rolling_goals(DB_PATH, league_code, TRAIN_SEASONS)
    if df.empty:
        print(f"  [SALTADO] {league_code}: sin datos de proxy suficientes.")
        return None

    # Recalcular proxy_home / proxy_away por separado (goals_rolling solo guarda el total)
    df["proxy_home"] = (df["home_avg_for"] + df["away_avg_against"]) / 2
    df["proxy_away"] = (df["away_avg_for"] + df["home_avg_against"]) / 2
    df["proxy_diff"] = df["proxy_home"] - df["proxy_away"]

    ah = cargar_odds_ah(DB_PATH, league_code)
    if ah.empty:
        print(f"  [SALTADO] {league_code}: no hay cuotas de handicap asiatico cargadas.")
        return None

    df = df.merge(ah, on="match_id", how="inner")
    if df.empty:
        print(f"  [SALTADO] {league_code}: no hay cruce entre proxy y cuotas AH.")
        return None

    # desacuerdo > 0 => creemos que el local deberia cubrir mas facil de lo que la linea sugiere
    df["desacuerdo"] = df["proxy_diff"] + df["linea"]
    df["margin"] = df["hg"] - df["ag"]
    df["bucket"] = df["desacuerdo"].apply(bucket_desacuerdo)
    df["lado_apostado"] = df["desacuerdo"].apply(lambda d: "home" if d > 0 else "away")

    filas = []
    for bucket, grupo in df.groupby("bucket"):
        for lado in ["home", "away"]:
            sub = grupo[grupo["lado_apostado"] == lado]
            n = len(sub)
            if n == 0:
                continue
            odds_col = "odds_home_ah" if lado == "home" else "odds_away_ah"
            profits = sub.apply(
                lambda r: liquidar_ah(r["linea"], r["margin"], lado, r[odds_col], STAKE), axis=1
            )
            profit_total = profits.sum()
            roi = profit_total / (n * STAKE) * 100
            acierto = (profits > 0).mean() * 100
            filas.append({
                "liga": league_code, "bucket_desacuerdo": bucket, "lado_apostado": lado,
                "n": n, "acierto_pct": round(acierto, 1),
                "profit_total": round(profit_total, 2), "roi_pct": round(roi, 2),
            })

    return pd.DataFrame(filas)


if __name__ == "__main__":
    todas = []
    for liga in LEAGUES:
        print(f"\n=== {liga} ===")
        res = analizar_liga_ah(liga)
        if res is not None and not res.empty:
            orden = pd.Categorical(res["bucket_desacuerdo"], categories=["<0.5", "0.5-1.0", "1.0-1.5", "1.5+"], ordered=True)
            res = res.assign(_o=orden).sort_values(["_o", "lado_apostado"]).drop(columns="_o")
            print(res.to_string(index=False))
            todas.append(res)

    if todas:
        pd.concat(todas, ignore_index=True).to_csv("cruce_ah_resultado.csv", index=False)
        print("\nGuardado en cruce_ah_resultado.csv")
