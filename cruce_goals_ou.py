import pandas as pd
from goals_rolling import calcular_rolling_goals
from cruce_shots_ou import cargar_odds_ou, STAKE, LEAGUES, TRAIN_SEASONS, DB_PATH

def bucket_proxy_goles(v):
    if v < 2.2: return "<2.2"
    elif v < 2.6: return "2.2-2.6"
    elif v < 3.0: return "2.6-3.0"
    else: return "3.0+"

def analizar_liga_goles(league_code):
    df = calcular_rolling_goals(DB_PATH, league_code, TRAIN_SEASONS)
    if df.empty:
        print(f"  [SALTADO] {league_code}: sin datos suficientes.")
        return None
    odds = cargar_odds_ou(DB_PATH, league_code)
    df = df.merge(odds, on="match_id", how="left")
    df = df.dropna(subset=["odds_over", "odds_under"])
    df["bucket"] = df["proxy_total"].apply(bucket_proxy_goles)

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
        res = analizar_liga_goles(liga)
        if res is not None:
            orden = pd.Categorical(res["bucket"], categories=["<2.2","2.2-2.6","2.6-3.0","3.0+"], ordered=True)
            res = res.assign(_o=orden).sort_values(["_o","seleccion"]).drop(columns="_o")
            print(res.to_string(index=False))
            todas.append(res)
    if todas:
        pd.concat(todas, ignore_index=True).to_csv("cruce_goals_ou.csv", index=False)
        