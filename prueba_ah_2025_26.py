import pandas as pd
from goals_rolling import calcular_rolling_goals
from cruce_ah import cargar_odds_ah, liquidar_ah, DB_PATH, LEAGUES, STAKE

TEST_SEASON = ["2025-2026"]

def probar_regla_ah(league_code):
    df = calcular_rolling_goals(DB_PATH, league_code, TEST_SEASON)
    if df.empty:
        print(f"  [SALTADO] {league_code}: sin datos de proxy en 2025/26 todavia.")
        return None

    df["proxy_home"] = (df["home_avg_for"] + df["away_avg_against"]) / 2
    df["proxy_away"] = (df["away_avg_for"] + df["home_avg_against"]) / 2
    df["proxy_diff"] = df["proxy_home"] - df["proxy_away"]

    ah = cargar_odds_ah(DB_PATH, league_code)
    if ah.empty:
        print(f"  [SALTADO] {league_code}: no hay cuotas AH en 2025/26.")
        return None

    df = df.merge(ah, on="match_id", how="inner")
    if df.empty:
        print(f"  [SALTADO] {league_code}: sin cruce proxy+cuotas en 2025/26.")
        return None

    df["desacuerdo"] = df["proxy_diff"] + df["linea"]
    df["margin"] = df["hg"] - df["ag"]

    # LA REGLA EXACTA que encontramos: desacuerdo >= 1.5, apostar away
    sub = df[df["desacuerdo"] <= -1.5].copy()  # desacuerdo favorece al away cuando es muy negativo
    n = len(sub)
    if n == 0:
        print(f"  {league_code}: 0 apuestas que cumplen la regla en 2025/26.")
        return None

    sub["profit"] = sub.apply(lambda r: liquidar_ah(r["linea"], r["margin"], "away", r["odds_away_ah"], STAKE), axis=1)
    acierto = (sub["profit"] > 0).mean() * 100
    profit_total = sub["profit"].sum()
    roi = profit_total / (n * STAKE) * 100

    print(f"=== {league_code}: desacuerdo>=1.5 a favor del visitante (2025/26) ===")
    print(f"  Apuestas: {n}  |  Acierto: {acierto:.1f}%  |  Profit: {profit_total:.2f}  |  ROI: {roi:+.2f}%\n")
    sub["league"] = league_code
    return sub

if __name__ == "__main__":
    resultados = []
    for liga in LEAGUES:
        res = probar_regla_ah(liga)
        if res is not None:
            resultados.append(res)

    if resultados:
        combinado = pd.concat(resultados, ignore_index=True)
        n = len(combinado)
        acierto = (combinado["profit"] > 0).mean() * 100
        profit = combinado["profit"].sum()
        roi = profit / (n * STAKE) * 100
        print("=== CONSOLIDADO 2025/26 (todas las ligas con datos) ===")
        print(f"Apuestas: {n}  |  Acierto: {acierto:.1f}%  |  Profit: {profit:.2f}  |  ROI: {roi:+.2f}%")
        combinado.to_csv("prueba_ah_2025_26.csv", index=False)
    else:
        print("\nNo hubo apuestas que cumplieran la regla en ninguna liga.")
        