import sqlite3
import pandas as pd
from posiciones import calcular_posiciones

DB_PATH = "futbol_apuestas.db"
TEST_SEASON = ["2025-2026"]
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

def probar_regla(league_code, mejor_posicionado, min_diff, max_diff, seleccion, nombre):
    pos = calcular_posiciones(DB_PATH, league_code, TEST_SEASON, min_jugados=5)
    odds = cargar_odds_1x2(DB_PATH, league_code)
    df = pos.merge(odds, on="match_id", how="left")
    df = df.dropna(subset=["home_pos", "away_pos", f"odds_{seleccion}"])

    df["diff"] = df["home_pos"] - df["away_pos"]
    df["abs_diff"] = df["diff"].abs()

    if mejor_posicionado == "local":
        sub = df[(df["diff"] < 0) & (df["abs_diff"] >= min_diff) & (df["abs_diff"] <= max_diff)].copy()
    else:
        sub = df[(df["diff"] > 0) & (df["abs_diff"] >= min_diff) & (df["abs_diff"] <= max_diff)].copy()

    n = len(sub)
    print(f"=== {nombre} ===")
    if n == 0:
        print("  0 partidos que cumplen la regla en 2025/26.\n")
        return None

    sub["gano"] = sub["actual"] == seleccion
    sub["profit"] = sub.apply(lambda r: STAKE*(r[f"odds_{seleccion}"]-1) if r["gano"] else -STAKE, axis=1)

    acierto = sub["gano"].mean()*100
    profit = sub["profit"].sum()
    roi = profit/(n*STAKE)*100
    print(f"  Apuestas: {n}  |  Acierto: {acierto:.1f}%  |  Profit: {profit:.2f}  |  ROI: {roi:+.2f}%\n")
    return sub

if __name__ == "__main__":
    reglas = [
        ("B1", "visita", 1, 5, "draw", "B1: visita mejor 1-5, apostar draw"),
        ("E1", "local", 1, 5, "away", "E1: local mejor 1-5, apostar away"),
        ("B1", "visita", 11, 15, "away", "B1: visita mejor 11-15, apostar away"),
        ("E1", "visita", 16, 99, "home", "E1: visita mejor 16+, apostar home"),
    ]

    resultados = []
    for liga, mejor, mind, maxd, sel, nombre in reglas:
        res = probar_regla(liga, mejor, mind, maxd, sel, nombre)
        if res is not None:
            resultados.append(res)

    if resultados:
        combinado = pd.concat(resultados, ignore_index=True)
        n = len(combinado)
        acierto = combinado["gano"].mean()*100
        profit = combinado["profit"].sum()
        roi = profit/(n*STAKE)*100
        print(f"=== CONSOLIDADO (los 4 candidatos juntos) ===")
        print(f"Apuestas: {n}  |  Acierto: {acierto:.1f}%  |  Profit: {profit:.2f}  |  ROI: {roi:+.2f}%")
        