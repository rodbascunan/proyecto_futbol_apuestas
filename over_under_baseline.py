import sqlite3
import pandas as pd

DB_PATH = "futbol_apuestas.db"
TRAIN_SEASONS = ["2021-2022", "2022-2023", "2023-2024", "2024-2025"]
LEAGUES = ["SP1", "E0", "N1", "P1"]
STAKE = 10.0

def cargar_partidos_ou(db_path, league_code, season_labels, bookmaker="Market Avg"):
    conn = sqlite3.connect(db_path)
    placeholders = ",".join(["?"] * len(season_labels))
    matches = pd.read_sql(f"""
        SELECT m.match_id, m.match_date, m.ft_home_goals AS hg, m.ft_away_goals AS ag,
               m.home_shots_target, m.away_shots_target
        FROM matches m
        JOIN leagues l ON l.league_id = m.league_id
        JOIN seasons s ON s.season_id = m.season_id
        WHERE l.code=? AND s.label IN ({placeholders})
    """, conn, params=(league_code, *season_labels))

    odds = pd.read_sql("""
        SELECT m.match_id, o.selection, o.price
        FROM odds o JOIN matches m ON m.match_id=o.match_id
        JOIN leagues l ON l.league_id=m.league_id
        WHERE o.bookmaker=? AND o.market_type='ou_2_5' AND o.snapshot='open' AND l.code=?
    """, conn, params=(bookmaker, league_code))
    conn.close()

    odds_wide = odds.pivot(index="match_id", columns="selection", values="price")
    odds_wide.columns = [f"odds_{c}" for c in odds_wide.columns]

    df = matches.merge(odds_wide, on="match_id", how="left")
    df["total_goles"] = df["hg"] + df["ag"]
    df["resultado_ou"] = df["total_goles"].apply(lambda g: "over" if g > 2.5 else "under")
    return df


def backtest_siempre(df, seleccion):
    sub = df.dropna(subset=[f"odds_{seleccion}"]).copy()
    n = len(sub)
    if n == 0:
        return None
    sub["gano"] = sub["resultado_ou"] == seleccion
    sub["profit"] = sub.apply(lambda r: STAKE*(r[f"odds_{seleccion}"]-1) if r["gano"] else -STAKE, axis=1)
    acierto = sub["gano"].mean()*100
    cuota_prom = sub[f"odds_{seleccion}"].mean()
    profit = sub["profit"].sum()
    roi = profit/(n*STAKE)*100
    return n, cuota_prom, acierto, profit, roi


if __name__ == "__main__":
    for liga in LEAGUES:
        df = cargar_partidos_ou(DB_PATH, liga, TRAIN_SEASONS)
        print(f"=== {liga} ===")
        print(f"Partidos: {len(df)}  |  % Over 2.5 real: {(df['resultado_ou']=='over').mean()*100:.1f}%")
        for sel in ["over", "under"]:
            res = backtest_siempre(df, sel)
            if res:
                n, cuota, acierto, profit, roi = res
                print(f"  Apostar SIEMPRE {sel}: n={n}, cuota={cuota:.2f}, acierto={acierto:.1f}%, profit=${profit:.2f}, ROI={roi:+.2f}%")
        print()
        