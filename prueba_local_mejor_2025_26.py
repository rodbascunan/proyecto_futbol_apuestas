import sqlite3
import pandas as pd
from posiciones import calcular_posiciones

DB_PATH = "futbol_apuestas.db"
TEST_SEASON = ["2025-2026"]
LEAGUES = ["SP1", "E0", "N1", "P1", "E1", "B1", "T1", "G1", "SC0"]
STAKE = 10.0

def cargar_odds_1x2(db_path, league_code, bookmaker="Market Avg"):
    conn = sqlite3.connect(db_path)
    odds = pd.read_sql("""
        SELECT m.match_id, o.selection, o.price
        FROM odds o JOIN matches m ON m.match_id=o.match_id
        JOIN leagues l ON l.league_id=m.league_id
        WHERE o.bookmaker=? AND o.market_type='1x2' AND o.snapshot='open' AND l.code=?
    """, conn, params=(bookmaker, league_code))
    conn.close()
    wide = odds.pivot(index="match_id", columns="selection", values="price")
    wide.columns = [f"odds_{c}" for c in wide.columns]
    return wide

def probar_liga(league_code):
    pos = calcular_posiciones(DB_PATH, league_code, TEST_SEASON, min_jugados=5)
    odds = cargar_odds_1x2(DB_PATH, league_code)
    df = pos.merge(odds, on="match_id", how="left")
    df = df.dropna(subset=["home_pos", "away_pos", "odds_home"])

    df["diff"] = df["home_pos"] - df["away_pos"]
    sub = df[df["diff"] < 0].copy()  # local mejor posicionado (cualquier magnitud)

    n = len(sub)
    if n == 0:
        print(f"  {league_code}: 0 partidos en 2025/26 con datos suficientes.")
        return None

    sub["gano"] = sub["actual"] == "home"
    sub["profit"] = sub.apply(lambda r: STAKE*(r["odds_home"]-1) if r["gano"] else -STAKE, axis=1)

    acierto = sub["gano"].mean()*100
    profit = sub["profit"].sum()
    roi = profit/(n*STAKE)*100
    print(f"  {league_code}: n={n}, acierto={acierto:.1f}%, profit={profit:.2f}, ROI={roi:+.2f}%")
    sub["league"] = league_code
    return sub

if __name__ == "__main__":
    print("=== Regla: local mejor posicionado (cualquier diferencia), apostar home ===")
    print("=== Temporada 2025/26 (out-of-sample real) ===\n")

    resultados = []
    for liga in LEAGUES:
        res = probar_liga(liga)
        if res is not None:
            resultados.append(res)

    if resultados:
        combinado = pd.concat(resultados, ignore_index=True)
        n = len(combinado)
        acierto = combinado["gano"].mean()*100
        profit = combinado["profit"].sum()
        roi = profit/(n*STAKE)*100
        print(f"\n=== CONSOLIDADO: {n} apuestas en {len(resultados)} ligas ===")
        print(f"Acierto: {acierto:.1f}%  |  Profit: {profit:.2f}  |  ROI: {roi:+.2f}%")
        print(f"Umbral n>=500: {'CUMPLIDO' if n >= 500 else 'NO CUMPLIDO'}")
        combinado.to_csv("prueba_local_mejor_2025_26.csv", index=False)
        