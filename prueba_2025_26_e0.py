import sqlite3
import pandas as pd
from posiciones import calcular_posiciones

DB_PATH = "futbol_apuestas.db"
TEST_SEASON = ["2025-2026"]

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

pos = calcular_posiciones(DB_PATH, "E0", TEST_SEASON, min_jugados=5)
odds = cargar_odds_1x2(DB_PATH)
df = pos.merge(odds, on="match_id", how="left")
df = df.dropna(subset=["home_pos", "away_pos", "odds_away"])

df["diff"] = df["home_pos"] - df["away_pos"]
sub = df[(df["diff"] < 0) & (df["diff"].abs() >= 6) & (df["diff"].abs() <= 10)].copy()

sub["gano"] = sub["actual"] == "away"
sub["profit"] = sub.apply(lambda r: 10*(r["odds_away"]-1) if r["gano"] else -10, axis=1)

n = len(sub)
print(f"=== Prueba OUT-OF-SAMPLE real: Premier League 2025/26 ===")
print(f"Partidos disponibles en 2025/26 hasta ahora: {len(df)}")
print(f"Apuestas que cumplen la regla (local mejor por 6-10 puestos, apostar away): {n}")
print()

if n == 0:
    print("Todavia no hay suficientes partidos jugados en 2025/26 para formar tablas de posicion confiables.")
    print("Esto es esperable si la temporada recien empezo -- hay que esperar a que avancen mas jornadas.")
else:
    print(f"Acierto real: {sub['gano'].mean()*100:.1f}%")
    print(f"Cuota promedio: {sub['odds_away'].mean():.2f}")
    print(f"Profit total (stake $10/apuesta): {sub['profit'].sum():.2f}")
    print(f"ROI: {sub['profit'].sum()/(n*10)*100:+.2f}%")
    print()
    print("=== Detalle de cada apuesta ===")
    detalle = sub[["match_date","home_team","away_team","home_pos","away_pos","odds_away","actual","profit"]]
    print(detalle.to_string(index=False))
    