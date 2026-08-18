"""
Validación del modelo: Log-Loss y Brier Score (version generalizada)
=====================================================================
A diferencia de la version anterior (hardcodeada a SP1 / una temporada),
esta version:
  1. Recibe LEAGUE y TRAIN_SEASONS como configuracion explicita
  2. Carga el modelo correcto: dixon_coles_model_{LEAGUE}.pkl
  3. Corre para las 4 ligas en un solo comando (bucle FOR al final)

IMPORTANTE: esto sigue siendo una validacion IN-SAMPLE (el modelo se
entreno con estas mismas temporadas). Sirve para confirmar que el ajuste
"tiene sentido" antes de gastar tiempo en el backtest real -- la prueba
que importa de verdad es backtest.py contra la temporada 2025/26, nunca
vista por el modelo.
"""

import sqlite3
import pickle
import numpy as np
import pandas as pd
from dixon_coles import load_matches, match_probabilities

DB_PATH = "futbol_apuestas.db"

# Debe coincidir EXACTO con TRAIN_SEASONS usado al ajustar cada modelo
TRAIN_SEASONS = ["2021-2022", "2022-2023", "2023-2024", "2024-2025"]
LEAGUES = ["SP1", "E0", "N1", "P1"]


def load_market_odds(db_path, league_code, season_labels, bookmaker="Market Avg"):
    conn = sqlite3.connect(db_path)
    placeholders = ",".join(["?"] * len(season_labels))
    query = f"""
        SELECT m.match_id, o.selection, o.price
        FROM odds o
        JOIN matches m ON m.match_id = o.match_id
        JOIN leagues l ON l.league_id = m.league_id
        JOIN seasons s ON s.season_id = m.season_id
        WHERE l.code = ? AND s.label IN ({placeholders})
          AND o.bookmaker = ? AND o.market_type = '1x2' AND o.snapshot = 'open'
    """
    df = pd.read_sql(query, conn, params=(league_code, *season_labels, bookmaker))
    conn.close()
    if df.empty:
        return pd.DataFrame(columns=["home", "draw", "away"])
    return df.pivot(index="match_id", columns="selection", values="price")


def devig(row):
    inv = 1.0 / row
    return inv / inv.sum()


def log_loss_one(p_dict, actual):
    return -np.log(max(p_dict[actual], 1e-10))


def brier_score_one(p_dict, actual):
    return sum((p_dict[o] - (1.0 if o == actual else 0.0)) ** 2 for o in ["home", "draw", "away"])


def validate_league(league_code, train_seasons, db_path=DB_PATH):
    model_path = f"dixon_coles_model_{league_code}.pkl"
    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)
    except FileNotFoundError:
        print(f"  [SALTADO] No se encontro {model_path}. Corre dixon_coles.py para esta liga primero.")
        return None

    odds = load_market_odds(db_path, league_code, train_seasons)
    if odds.empty:
        print(f"  [SALTADO] No hay cuotas Market Avg cargadas para {league_code} en estas temporadas.")
        return None

    conn = sqlite3.connect(db_path)
    placeholders = ",".join(["?"] * len(train_seasons))
    match_ids = pd.read_sql(
        f"""SELECT m.match_id, t1.name AS home_team, t2.name AS away_team,
                   m.ft_home_goals AS hg, m.ft_away_goals AS ag
            FROM matches m
            JOIN teams t1 ON t1.team_id = m.home_team_id
            JOIN teams t2 ON t2.team_id = m.away_team_id
            JOIN leagues l ON l.league_id = m.league_id
            JOIN seasons s ON s.season_id = m.season_id
            WHERE l.code=? AND s.label IN ({placeholders})""",
        conn, params=(league_code, *train_seasons),
    )
    conn.close()

    results = []
    for _, row in match_ids.iterrows():
        mid = row["match_id"]
        if mid not in odds.index:
            continue
        market_row = odds.loc[mid]
        if market_row.isnull().any():
            continue
        actual = "home" if row["hg"] > row["ag"] else ("away" if row["ag"] > row["hg"] else "draw")
        mp = match_probabilities(model, row["home_team"], row["away_team"])
        model_p = {"home": mp["home"], "draw": mp["draw"], "away": mp["away"]}
        market_p_arr = devig(market_row[["home", "draw", "away"]])
        market_p = {"home": market_p_arr["home"], "draw": market_p_arr["draw"], "away": market_p_arr["away"]}
        results.append({
            "log_loss_model": log_loss_one(model_p, actual),
            "log_loss_market": log_loss_one(market_p, actual),
            "brier_model": brier_score_one(model_p, actual),
            "brier_market": brier_score_one(market_p, actual),
        })

    if not results:
        print(f"  [SALTADO] Ningun partido con cuota completa para cruzar en {league_code}.")
        return None

    res = pd.DataFrame(results)
    print(f"  Partidos evaluados: {len(res)} de {len(match_ids)}")
    print(f"  Log-Loss   -> Modelo: {res['log_loss_model'].mean():.4f}  |  Mercado: {res['log_loss_market'].mean():.4f}")
    print(f"  Brier      -> Modelo: {res['brier_model'].mean():.4f}  |  Mercado: {res['brier_market'].mean():.4f}")
    return res


if __name__ == "__main__":
    for league in LEAGUES:
        print(f"\n=== Validando {league} (in-sample, {TRAIN_SEASONS[0]} a {TRAIN_SEASONS[-1]}) ===")
        validate_league(league, TRAIN_SEASONS)
