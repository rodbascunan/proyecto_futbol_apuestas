import sqlite3
import pandas as pd
from posiciones import calcular_posiciones

DB_PATH = "futbol_apuestas.db"
TEST_SEASON = ["2025-2026"]
LEAGUES = ["SP1", "N1", "P1"]  # Premier League (E0) ya la probamos

def cargar_odds_1x2(db_path, bookmaker="Market Avg"):
    conn = sqlite3.connect(db_path)
    odds = pd.read_sql(
        """SELECT m.match_id, o.selection, o.price
           FROM odds o JOIN matches m ON m.match_id = o.match_id
           WHERE o.bookmaker = ? AND o.market_type='1x2' AND o.snapshot='open'""",
        conn, params=(bookmaker,),
    )
    conn.close()
    wide = odds.pivot(index="match_id", columns="selection", values="price")
    wide.columns = [f"odds_{c}" for c in wide.columns]
    return wide

def probar_regla(league_code):
    pos = calcular_posiciones(DB_PATH, league_code, TEST_SEASON, min_jugados=5)
    odds = cargar_odds_1x2(DB_PATH)
    df = pos.merge(odds, on="match_id", how="left")
    df = df.dropna(subset=["home_pos", "away_pos", "odds_away"])

    df["diff"] = df["home_pos"] - df["away_pos"]
    sub = df[(df["diff"] < 0) & (df["diff"].abs() >= 6) & (df["diff"].abs() <= 10)].copy()

    sub["gano"] = sub["actual"] == "away"
    sub["profit"] = sub.apply(lambda r: 10*(r["odds_away"]-1) if r["gano"] else -10, axis=1)

    n = len(sub)
    print(f"=== {league_code}: local mejor por 6-10 puestos, apostar away (2025/26) ===")
    print(f"Partidos disponibles en 2025/26: {len(df)}")
    print(f"Apuestas que cumplen la regla: {n}")
    if n == 0:
        print("Sin apuestas suficientes todavia.\n")
        return None
    acierto = sub['gano'].mean()*100
    cuota_prom = sub['odds_away'].mean()
    profit = sub['profit'].sum()
    roi = profit/(n*10)*100
    print(f"Acierto real: {acierto:.1f}%")
    print(f"Cuota promedio: {cuota_prom:.2f}")
    print(f"Profit total: {profit:.2f}")
    print(f"ROI: {roi:+.2f}%\n")
    sub["league"] = league_code
    return sub

if __name__ == "__main__":
    resultados = []
    for liga in LEAGUES:
        res = probar_regla(liga)
        if res is not None:
            resultados.append(res)

    if resultados:
        combinado = pd.concat(resultados, ignore_index=True)
        n = len(combinado)
        acierto = combinado['gano'].mean()*100
        profit = combinado['profit'].sum()
        roi = profit/(n*10)*100
        print("=== CONSOLIDADO: SP1 + N1 + P1 (2025/26) ===")
        print(f"Apuestas: {n}")
        print(f"Acierto real: {acierto:.1f}%")
        print(f"Profit total: {profit:.2f}")
        print(f"ROI: {roi:+.2f}%")
        combinado.to_csv("prueba_2025_26_otras_ligas.csv", index=False)
        