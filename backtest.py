"""
Fase 4 — Punto C: Backtesting real (version generalizada)
=============================================================
Diferencias clave respecto al ensayo anterior:
  1. El split ya NO es por fecha dentro de una temporada (70/30) -- es el
     split REAL del plan: TRAIN_SEASONS (2021/22-2024/25) vs TEST_SEASON
     (2025/26), una temporada genuinamente nunca vista por el modelo.
  2. Usa el modelo YA AJUSTADO (dixon_coles_model_{LEAGUE}.pkl) en vez de
     reajustarlo -- porque ese modelo ya fue entrenado exclusivamente con
     TRAIN_SEASONS, asi que cargarlo tal cual preserva la separacion
     out-of-sample.
  3. Corre las 4 ligas en un solo comando y consolida el resultado.

RECORDATORIO DEL PROTOCOLO: ninguna conclusion de edge es valida con
menos de n>=500 apuestas EV>0 acumuladas. Si al sumar las 4 ligas no se
llega a eso, hay que reportar los numeros como preliminares, no como
evidencia de ventaja real.
"""

import sqlite3
import pickle
import numpy as np
import pandas as pd
from dixon_coles import match_probabilities

DB_PATH = "futbol_apuestas.db"
TRAIN_SEASONS = ["2021-2022", "2022-2023", "2023-2024", "2024-2025"]
TEST_SEASON = "2025-2026"
LEAGUES = ["SP1", "E0", "N1", "P1"]

KELLY_FRACTION = 0.25
MAX_STAKE_PER_BET = 0.05  # tope duro, hallazgo del ensayo anterior
N_SIMULATIONS = 10_000
INITIAL_BANKROLL = 1000.0


def load_raw_market_odds(db_path, league_code, season_label, bookmaker="Market Avg"):
    conn = sqlite3.connect(db_path)
    query = """
        SELECT m.match_id, o.selection, o.price
        FROM odds o
        JOIN matches m ON m.match_id = o.match_id
        JOIN leagues l ON l.league_id = m.league_id
        JOIN seasons s ON s.season_id = m.season_id
        WHERE l.code = ? AND s.label = ?
          AND o.bookmaker = ? AND o.market_type = '1x2' AND o.snapshot = 'open'
    """
    df = pd.read_sql(query, conn, params=(league_code, season_label, bookmaker))
    conn.close()
    if df.empty:
        return pd.DataFrame(columns=["home", "draw", "away"])
    return df.pivot(index="match_id", columns="selection", values="price")


def get_test_matches(db_path, league_code, season_label):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        """SELECT m.match_id, m.match_date, t1.name AS home_team, t2.name AS away_team,
                  m.ft_home_goals AS hg, m.ft_away_goals AS ag
           FROM matches m
           JOIN teams t1 ON t1.team_id = m.home_team_id
           JOIN teams t2 ON t2.team_id = m.away_team_id
           JOIN leagues l ON l.league_id = m.league_id
           JOIN seasons s ON s.season_id = m.season_id
           WHERE l.code=? AND s.label=?
           ORDER BY m.match_date""",
        conn, params=(league_code, season_label),
    )
    conn.close()
    return df


def kelly_stake(p, decimal_odds, fraction=KELLY_FRACTION, max_stake=MAX_STAKE_PER_BET):
    b = decimal_odds - 1
    q = 1 - p
    f_star = (p * b - q) / b
    return min(max(f_star, 0) * fraction, max_stake)


def find_value_bets(model, test_df, odds_df, league_code):
    bets = []
    equipos_desconocidos = set()
    for _, row in test_df.iterrows():
        mid = row["match_id"]
        if mid not in odds_df.index:
            continue
        market_row = odds_df.loc[mid]
        if market_row.isnull().any():
            continue

        # Saltar partidos con equipos recien ascendidos que el modelo nunca
        # vio en las temporadas de entrenamiento (ej. Oviedo en 2025/26).
        # No tiene sentido inventarles una calificacion de ataque/defensa.
        if row["home_team"] not in model["attack"] or row["away_team"] not in model["attack"]:
            if row["home_team"] not in model["attack"]:
                equipos_desconocidos.add(row["home_team"])
            if row["away_team"] not in model["attack"]:
                equipos_desconocidos.add(row["away_team"])
            continue

        probs = match_probabilities(model, row["home_team"], row["away_team"])
        actual = "home" if row["hg"] > row["ag"] else ("away" if row["ag"] > row["hg"] else "draw")

        for selection in ["home", "draw", "away"]:
            p_model = probs[selection]
            odds = market_row[selection]
            ev = p_model * odds - 1
            if ev > 0:
                bets.append({
                    "league": league_code, "match_id": mid,
                    "home_team": row["home_team"], "away_team": row["away_team"],
                    "selection": selection, "p_model": p_model, "odds": odds, "ev": ev,
                    "kelly_stake_frac": kelly_stake(p_model, odds),
                    "won": (selection == actual),
                })

    if equipos_desconocidos:
        print(f"    [AVISO] Equipos sin historial en el modelo, partidos excluidos: {sorted(equipos_desconocidos)}")

    return pd.DataFrame(bets)


def monte_carlo_bankroll(bets_df, n_sims=N_SIMULATIONS, initial_bankroll=INITIAL_BANKROLL):
    n_bets = len(bets_df)
    stakes_frac = bets_df["kelly_stake_frac"].values
    odds = bets_df["odds"].values
    p_model = bets_df["p_model"].values

    final_bankrolls = np.zeros(n_sims)
    max_drawdowns = np.zeros(n_sims)

    for sim in range(n_sims):
        bankroll = initial_bankroll
        peak = initial_bankroll
        max_dd = 0.0
        outcomes = np.random.random(n_bets) < p_model

        for i in range(n_bets):
            stake = bankroll * stakes_frac[i]
            if outcomes[i]:
                bankroll += stake * (odds[i] - 1)
            else:
                bankroll -= stake
            peak = max(peak, bankroll)
            dd = (peak - bankroll) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        final_bankrolls[sim] = bankroll
        max_drawdowns[sim] = max_dd

    return final_bankrolls, max_drawdowns


def backtest_league(league_code, db_path=DB_PATH):
    model_path = f"dixon_coles_model_{league_code}.pkl"
    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)
    except FileNotFoundError:
        print(f"  [SALTADO] No se encontro {model_path}.")
        return None

    test_df = get_test_matches(db_path, league_code, TEST_SEASON)
    if test_df.empty:
        print(f"  [SALTADO] No hay partidos de {TEST_SEASON} cargados para {league_code} todavia.")
        return None

    odds_df = load_raw_market_odds(db_path, league_code, TEST_SEASON)
    if odds_df.empty:
        print(f"  [SALTADO] No hay cuotas Market Avg de {TEST_SEASON} para {league_code}.")
        return None

    bets = find_value_bets(model, test_df, odds_df, league_code)
    print(f"  Partidos en test ({TEST_SEASON}): {len(test_df)}")
    print(f"  Apuestas EV>0 encontradas: {len(bets)} de {len(test_df)*3} selecciones posibles")
    if len(bets) > 0:
        print(f"    EV promedio: {bets['ev'].mean()*100:.2f}%")
        print(f"    Tasa de acierto real: {bets['won'].mean()*100:.1f}%  |  predicha por el modelo: {bets['p_model'].mean()*100:.1f}%")
    return bets


if __name__ == "__main__":
    all_bets = []
    for league in LEAGUES:
        print(f"\n=== Backtest {league}: train={TRAIN_SEASONS[0]}-{TRAIN_SEASONS[-1]}, test={TEST_SEASON} ===")
        bets = backtest_league(league)
        if bets is not None and len(bets) > 0:
            all_bets.append(bets)

    if not all_bets:
        print("\nNo hay apuestas EV>0 para analizar todavia en ninguna liga.")
    else:
        combined = pd.concat(all_bets, ignore_index=True)
        print(f"\n=== CONSOLIDADO: {len(combined)} apuestas EV>0 en las {len(all_bets)} ligas con datos ===")
        print(f"  Umbral del protocolo (n>=500): {'CUMPLIDO' if len(combined) >= 500 else 'NO CUMPLIDO -- tratar resultados como preliminares'}")
        print(f"  Tasa de acierto real combinada: {combined['won'].mean()*100:.1f}%")
        print(f"  Tasa de acierto predicha combinada: {combined['p_model'].mean()*100:.1f}%")

        if len(combined) >= 5:
            final_br, max_dd = monte_carlo_bankroll(combined)
            print(f"\n=== Montecarlo consolidado ({N_SIMULATIONS} iteraciones, banca inicial ${INITIAL_BANKROLL:.0f}) ===")
            print(f"  Banca final promedio: ${final_br.mean():.2f}")
            print(f"  P(banca final > inicial): {(final_br > INITIAL_BANKROLL).mean()*100:.1f}%")
            print(f"  Drawdown maximo promedio: {max_dd.mean()*100:.1f}%")
            print(f"  P(drawdown > 20%): {(max_dd > 0.20).mean()*100:.1f}%")

        combined.to_csv("backtest_consolidado_real.csv", index=False)
        print("\nDetalle guardado en backtest_consolidado_real.csv")
