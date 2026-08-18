"""
Explorador de estrategias simples
====================================
Herramienta generica para probar reglas de apuesta contra el historial
real (cuotas + resultados), sin depender del modelo Dixon-Coles.

Uso: define una funcion de filtro (que reglas cumple un partido) y
llama a backtest_regla(). El script evalua la regla en TRAIN y, si se
ve prometedora, hay que confirmarla en TEST antes de creer que es real.
"""

import sqlite3
import pandas as pd

DB_PATH = "futbol_apuestas.db"

TRAIN_SEASONS = ["2021-2022", "2022-2023", "2023-2024", "2024-2025"]
TEST_SEASON = "2025-2026"


def cargar_partidos_con_cuotas(db_path, league_codes=None, season_labels=None, bookmaker="Market Avg"):
    """Trae TODOS los partidos con sus cuotas 1x2 (Market Avg, apertura) en
    una sola tabla ancha, lista para filtrar con cualquier regla."""
    conn = sqlite3.connect(db_path)

    league_filter = ""
    params = [bookmaker]
    if league_codes:
        placeholders = ",".join(["?"] * len(league_codes))
        league_filter += f" AND l.code IN ({placeholders})"
        params = league_codes + params
    if season_labels:
        placeholders = ",".join(["?"] * len(season_labels))
        league_filter += f" AND s.label IN ({placeholders})"
        params = params[:len(league_codes) if league_codes else 0] + (season_labels if not league_codes else season_labels) + [bookmaker] if False else params

    # (construccion de query mas simple y explicita para evitar errores)
    query = """
        SELECT m.match_id, l.code AS league, s.label AS season, m.match_date,
               t1.name AS home_team, t2.name AS away_team,
               m.ft_home_goals AS hg, m.ft_away_goals AS ag,
               m.home_shots, m.away_shots, m.home_corners, m.away_corners
        FROM matches m
        JOIN leagues l ON l.league_id = m.league_id
        JOIN seasons s ON s.season_id = m.season_id
        JOIN teams t1 ON t1.team_id = m.home_team_id
        JOIN teams t2 ON t2.team_id = m.away_team_id
    """
    conditions = []
    args = []
    if league_codes:
        conditions.append(f"l.code IN ({','.join(['?']*len(league_codes))})")
        args += league_codes
    if season_labels:
        conditions.append(f"s.label IN ({','.join(['?']*len(season_labels))})")
        args += season_labels
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    matches = pd.read_sql(query, conn, params=args)

    odds_query = """
        SELECT m.match_id, o.selection, o.price
        FROM odds o
        JOIN matches m ON m.match_id = o.match_id
        WHERE o.bookmaker = ? AND o.market_type = '1x2' AND o.snapshot = 'open'
    """
    odds = pd.read_sql(odds_query, conn, params=[bookmaker])
    conn.close()

    odds_wide = odds.pivot(index="match_id", columns="selection", values="price")
    odds_wide.columns = [f"odds_{c}" for c in odds_wide.columns]

    df = matches.merge(odds_wide, on="match_id", how="left")
    df["actual"] = df.apply(
        lambda r: "home" if r["hg"] > r["ag"] else ("away" if r["ag"] > r["hg"] else "draw"), axis=1
    )
    return df


def backtest_regla(df, filtro_fn, seleccion, nombre_regla="Regla sin nombre", stake_fijo=10.0):
    """
    df: resultado de cargar_partidos_con_cuotas()
    filtro_fn: funcion que recibe una fila y devuelve True/False (que partidos entran en la regla)
    seleccion: 'home', 'draw' o 'away' -- que se apuesta cuando la regla se cumple
    stake_fijo: monto fijo apostado por partido (para medir ROI simple, sin Kelly)
    """
    sub = df[df.apply(filtro_fn, axis=1)].copy()
    sub = sub.dropna(subset=[f"odds_{seleccion}"])

    n = len(sub)
    if n == 0:
        print(f"--- {nombre_regla}: 0 partidos cumplen la regla ---")
        return None

    sub["gano"] = sub["actual"] == seleccion
    sub["profit"] = sub.apply(
        lambda r: stake_fijo * (r[f"odds_{seleccion}"] - 1) if r["gano"] else -stake_fijo, axis=1
    )

    acierto = sub["gano"].mean() * 100
    profit_total = sub["profit"].sum()
    roi = (profit_total / (n * stake_fijo)) * 100
    cuota_prom = sub[f"odds_{seleccion}"].mean()

    print(f"--- {nombre_regla} ---")
    print(f"  Apuestas: {n}")
    print(f"  Cuota promedio: {cuota_prom:.2f}")
    print(f"  Acierto real: {acierto:.1f}%")
    print(f"  Profit total (stake fijo ${stake_fijo:.0f}/apuesta): ${profit_total:+.2f}")
    print(f"  ROI: {roi:+.2f}%")
    print()
    return sub


if __name__ == "__main__":
    print("Este archivo es una libreria de funciones. Importa cargar_partidos_con_cuotas")
    print("y backtest_regla desde otro script para probar una regla especifica.")
    print("Ejemplo minimo:")
    print()
    print("  from explorador import cargar_partidos_con_cuotas, backtest_regla, TRAIN_SEASONS")
    print("  df = cargar_partidos_con_cuotas('futbol_apuestas.db', season_labels=TRAIN_SEASONS)")
    print("  backtest_regla(df, lambda r: r['odds_home'] < 1.5, 'home', 'Favoritos fuertes de local')")
