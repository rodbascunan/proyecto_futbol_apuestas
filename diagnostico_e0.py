import sqlite3
import pandas as pd
from posiciones import calcular_posiciones

DB_PATH = "futbol_apuestas.db"
TRAIN_SEASONS = ["2021-2022", "2022-2023", "2023-2024", "2024-2025"]

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

pos = calcular_posiciones(DB_PATH, "E0", TRAIN_SEASONS, min_jugados=5)
odds = cargar_odds_1x2(DB_PATH)
df = pos.merge(odds, on="match_id", how="left")
df = df.dropna(subset=["home_pos", "away_pos", "odds_away"])

df["diff"] = df["home_pos"] - df["away_pos"]
sub = df[(df["diff"] < 0) & (df["diff"].abs() >= 6) & (df["diff"].abs() <= 10)].copy()

sub["gano"] = sub["actual"] == "away"
sub["profit"] = sub.apply(lambda r: 10*(r["odds_away"]-1) if r["gano"] else -10, axis=1)

print(f"Total de apuestas en el grupo: {len(sub)}")
print(f"Profit total: {sub['profit'].sum():.2f}")
print()

print("=== 1. Distribucion por temporada (se sostiene en todas o es 1 sola?) ===")
print(sub.groupby("season").agg(n=("gano","count"), acierto=("gano","mean"), profit=("profit","sum")))
print()

print("=== 2. Distribucion exacta de la diferencia de posiciones (6,7,8,9,10) ===")
sub["diff_exacta"] = sub["diff"].abs().astype(int)
print(sub.groupby("diff_exacta").agg(n=("gano","count"), acierto=("gano","mean"), profit=("profit","sum")))
print()

print("=== 3. Las 15 apuestas que mas aportaron al profit (ver si son pocas apuestas gigantes) ===")
top = sub.nlargest(15, "profit")[["season","match_date","home_team","away_team","home_pos","away_pos","odds_away","actual","profit"]]
print(top.to_string(index=False))
print()

print("=== 4. Equipos visitantes que mas aparecen ganando en este grupo ===")
ganados = sub[sub["gano"]]
print(ganados["away_team"].value_counts().head(15))
print()

print("=== 5. Cuota promedio y mediana (revisar si el promedio esta inflado por outliers) ===")
print(f"Cuota promedio: {sub['odds_away'].mean():.2f}")
print(f"Cuota mediana: {sub['odds_away'].median():.2f}")
print(f"Cuota maxima: {sub['odds_away'].max():.2f}")
