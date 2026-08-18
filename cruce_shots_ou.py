import sqlite3
import pandas as pd
from shots_rolling import calcular_rolling_shots

DB_PATH = "futbol_apuestas.db"
TRAIN_SEASONS = ["2021-2022", "2022-2023", "2023-2024", "2024-2025"]
LEAGUES = ["SP1", "E0", "N1", "P1"]
STAKE = 10.0

def cargar_odds_ou(db_path, league_code, bookmaker="Market Avg"):
    conn = sqlite3.connect(db_path)
    odds = pd.read_sql("""
        SELECT m.match_id, o.selection, o.price
        FROM odds o JOIN matches m ON m.match_id=o.match_id
        JOIN leagues l ON l.league_id=m.league_id
        WHERE o.bookmaker=? AND o.market_type='ou_2_5' AND o.snapshot='open' AND l.code=?
    """, conn, params=(bookmaker, league_code))
    conn.close()
    wide = odds.pivot(index="match_id", columns="selection", values="price")
    wide.columns = [f"odds_{c}" for c in wide.columns]
    return wide

def bucket_proxy(v):
    if v < 6: return "<6"
    elif v < 8: return "6-8"
    elif v < 10: return "8-10"
    else: return "10+"

def analizar_liga(league_code):
    df = calcular_rolling_shots(DB_PATH, league_code, TRAIN_SEASONS)
    if df.empty:
        print(f"  [SALTADO] {league_code}: sin datos suficientes.")
        return None
    odds = cargar_odds_ou(DB_PATH, league_code)
    df = df.merge(odds, on="match_id", how="left")
    df = df.dropna(subset=["odds_over", "odds_under"])
    df["bucket"] = df["proxy_total"].apply(bucket_proxy)

    filas = []
    for bucket, grupo in df.groupby("bucket"):
        n = len(grupo)
        for sel in ["over", "under"]:
            gano = grupo["resultado_ou"] == sel
            cuota_prom = grupo[f"odds_{sel}"].mean()
            acierto = gano.mean()*100
            profit = (grupo.loc[gano, f"odds_{sel}"]-1).sum()*STAKE - (~gano).sum()*STAKE
            roi = profit/(n*STAKE)*100
            filas.append({"liga": league_code, "bucket": bucket, "n": n, "seleccion": sel,
                          "cuota_prom": round(cuota_prom,2), "acierto_pct": round(acierto,1), "roi_pct": round(roi,2)})
    return pd.DataFrame(filas)

if __name__ == "__main__":
    todas = []
    for liga in LEAGUES:
        print(f"\n=== {liga} ===")
        res = analizar_liga(liga)
        if res is not None:
            orden = pd.Categorical(res["bucket"], categories=["<6","6-8","8-10","10+"], ordered=True)
            res = res.assign(_o=orden).sort_values(["_o","seleccion"]).drop(columns="_o")
            print(res.to_string(index=False))
            todas.append(res)
    if todas:
        pd.concat(todas, ignore_index=True).to_csv("cruce_shots_ou.csv", index=False)
        