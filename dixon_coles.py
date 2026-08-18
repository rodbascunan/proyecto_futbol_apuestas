"""
Fase 4 — Punto B: Modelo de probabilidad propia
================================================
Poisson bivariado con corrección de Dixon-Coles (1997) para marcadores
de bajo volumen de goles, ponderación temporal por decaimiento exponencial,
y ventaja de localía.

Prueba de concepto sobre los datos ya cargados (La Liga 2024/25, 230
partidos, una sola temporada). El decaimiento temporal y la robustez del
modelo se validan de verdad recién con las 5 temporadas x 4 ligas que
correrá el punto A en su máquina — aquí se valida que la METODOLOGÍA
está bien implementada.
"""

import sqlite3
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson
from datetime import datetime
from math import log

DB_PATH = "futbol_apuestas.db"

# ------------------------------------------------------------------
# 1. Cargar datos
# ------------------------------------------------------------------
def load_matches(db_path, league_code="SP1", season_labels=None):
    """season_labels puede ser un string (una temporada) o una lista
    (varias temporadas, ej. para el set de entrenamiento)."""
    if season_labels is None:
        season_labels = ["2024-2025"]
    if isinstance(season_labels, str):
        season_labels = [season_labels]

    conn = sqlite3.connect(db_path)
    placeholders = ",".join(["?"] * len(season_labels))
    query = f"""
        SELECT m.match_date, t1.name AS home_team, t2.name AS away_team,
               m.ft_home_goals AS hg, m.ft_away_goals AS ag
        FROM matches m
        JOIN teams t1 ON t1.team_id = m.home_team_id
        JOIN teams t2 ON t2.team_id = m.away_team_id
        JOIN leagues l ON l.league_id = m.league_id
        JOIN seasons s ON s.season_id = m.season_id
        WHERE l.code = ? AND s.label IN ({placeholders})
        ORDER BY m.match_date
    """
    df = pd.read_sql(query, conn, params=(league_code, *season_labels))
    conn.close()
    df["match_date"] = pd.to_datetime(df["match_date"])
    df["hg"] = df["hg"].astype(int)
    df["ag"] = df["ag"].astype(int)
    return df
    conn = sqlite3.connect(db_path)
    query = """
        SELECT m.match_date, t1.name AS home_team, t2.name AS away_team,
               m.ft_home_goals AS hg, m.ft_away_goals AS ag
        FROM matches m
        JOIN teams t1 ON t1.team_id = m.home_team_id
        JOIN teams t2 ON t2.team_id = m.away_team_id
        JOIN leagues l ON l.league_id = m.league_id
        JOIN seasons s ON s.season_id = m.season_id
        WHERE l.code = ? AND s.label = ?
        ORDER BY m.match_date
    """
    df = pd.read_sql(query, conn, params=(league_code, season_label))
    conn.close()
    df["match_date"] = pd.to_datetime(df["match_date"])
    df["hg"] = df["hg"].astype(int)
    df["ag"] = df["ag"].astype(int)
    return df


# ------------------------------------------------------------------
# 2. Ponderación temporal (decaimiento exponencial, Dixon-Coles §3)
# ------------------------------------------------------------------
def time_weights(dates, xi=0.0018):
    """xi controla qué tan rápido 'olvida' el modelo partidos viejos.
    xi=0.0018 da una vida media (half-life) de ~385 dias, un punto de
    partida razonable citado en la literatura de Dixon-Coles."""
    most_recent = dates.max()
    days_diff = (most_recent - dates).dt.days.values
    return np.exp(-xi * days_diff)


# ------------------------------------------------------------------
# 3. Función tau de Dixon-Coles: corrige la subestimación/sobreestimación
#    de empates y marcadores bajos que el Poisson independiente comete.
# ------------------------------------------------------------------
def tau(hg, ag, lambda_home, lambda_away, rho):
    if hg == 0 and ag == 0:
        return 1 - lambda_home * lambda_away * rho
    elif hg == 0 and ag == 1:
        return 1 + lambda_home * rho
    elif hg == 1 and ag == 0:
        return 1 + lambda_away * rho
    elif hg == 1 and ag == 1:
        return 1 - rho
    else:
        return 1.0


# ------------------------------------------------------------------
# 4. Log-verosimilitud negativa del modelo
# ------------------------------------------------------------------
def build_team_index(df):
    teams = sorted(set(df["home_team"]) | set(df["away_team"]))
    return {t: i for i, t in enumerate(teams)}, teams


def unpack_params(params, n_teams):
    attack = params[:n_teams]
    defense = params[n_teams:2 * n_teams]
    home_adv = params[2 * n_teams]
    rho = params[2 * n_teams + 1]
    return attack, defense, home_adv, rho


def neg_log_likelihood(params, df, team_idx, n_teams, weights):
    attack, defense, home_adv, rho = unpack_params(params, n_teams)
    ll = 0.0
    for (_, row), w in zip(df.iterrows(), weights):
        i = team_idx[row["home_team"]]
        j = team_idx[row["away_team"]]
        lam_home = np.exp(attack[i] - defense[j] + home_adv)
        lam_away = np.exp(attack[j] - defense[i])
        hg, ag = row["hg"], row["ag"]

        base_prob = poisson.pmf(hg, lam_home) * poisson.pmf(ag, lam_away)
        adj = tau(hg, ag, lam_home, lam_away, rho)
        adj = max(adj, 1e-10)  # evitar log(0) si la optimizacion pasa por una zona invalida
        prob = max(base_prob * adj, 1e-10)
        ll += w * log(prob)
    return -ll


def fit_dixon_coles(df):
    team_idx, teams = build_team_index(df)
    n_teams = len(teams)
    weights = time_weights(df["match_date"])

    # Punto de partida: ataque/defensa en 0, ventaja de localia leve, rho=0
    x0 = np.zeros(2 * n_teams + 2)
    x0[2 * n_teams] = 0.25   # home_adv inicial
    x0[2 * n_teams + 1] = 0.0  # rho inicial

    # Restriccion de identificabilidad: fijar el ataque medio en 0
    # (si no, attack y defense pueden desplazarse todos juntos sin
    # cambiar la verosimilitud, y el optimizador no converge bien)
    constraints = [{
        "type": "eq",
        "fun": lambda p: np.mean(p[:n_teams])
    }]

    result = minimize(
        neg_log_likelihood, x0, args=(df, team_idx, n_teams, weights),
        method="SLSQP", constraints=constraints,
        options={"maxiter": 300, "ftol": 1e-8},
    )
    attack, defense, home_adv, rho = unpack_params(result.x, n_teams)
    return {
        "teams": teams,
        "attack": dict(zip(teams, attack)),
        "defense": dict(zip(teams, defense)),
        "home_adv": home_adv,
        "rho": rho,
        "converged": result.success,
        "neg_log_lik": result.fun,
    }


# ------------------------------------------------------------------
# 5. Probabilidades de resultado (1X2) a partir del modelo ajustado
# ------------------------------------------------------------------
def match_probabilities(model, home_team, away_team, max_goals=10):
    attack, defense = model["attack"], model["defense"]
    home_adv, rho = model["home_adv"], model["rho"]

    lam_home = np.exp(attack[home_team] - defense[away_team] + home_adv)
    lam_away = np.exp(attack[away_team] - defense[home_team])

    score_matrix = np.zeros((max_goals + 1, max_goals + 1))
    for hg in range(max_goals + 1):
        for ag in range(max_goals + 1):
            base = poisson.pmf(hg, lam_home) * poisson.pmf(ag, lam_away)
            score_matrix[hg, ag] = base * tau(hg, ag, lam_home, lam_away, rho)

    score_matrix /= score_matrix.sum()  # renormalizar (la correccion tau puede desbalancear levemente)

    p_home = np.tril(score_matrix, -1).sum()
    p_draw = np.trace(score_matrix)
    p_away = np.triu(score_matrix, 1).sum()
    return {"home": p_home, "draw": p_draw, "away": p_away,
            "lambda_home": lam_home, "lambda_away": lam_away}


if __name__ == "__main__":
    TRAIN_SEASONS = ["2021-2022", "2022-2023", "2023-2024", "2024-2025"]
    LEAGUE = "P1"

    df = load_matches(DB_PATH, league_code=LEAGUE, season_labels=TRAIN_SEASONS)
    print(f"Partidos cargados para el ajuste ({LEAGUE}, temporadas {TRAIN_SEASONS}): {len(df)}")
    print(f"Rango de fechas: {df['match_date'].min().date()} a {df['match_date'].max().date()}")
    print()

    model = fit_dixon_coles(df)
    print(f"Convergencia del optimizador: {model['converged']}")
    print(f"Log-verosimilitud negativa final: {model['neg_log_lik']:.2f}")
    print(f"Ventaja de localia (home_adv, en escala log): {model['home_adv']:.4f}")
    print(f"Rho (correccion Dixon-Coles): {model['rho']:.4f}")
    print()

    print("=== Ranking de ataque (top 5) ===")
    for team, val in sorted(model["attack"].items(), key=lambda x: -x[1])[:5]:
        print(f"  {team:15s} {val:+.3f}")
    print()
    print("=== Ranking de defensa (top 5, valor mas ALTO = mejor defensa) ===")
    for team, val in sorted(model["defense"].items(), key=lambda x: -x[1])[:5]:
        print(f"  {team:15s} {val:+.3f}")

    import pickle
    with open(f"dixon_coles_model_{LEAGUE}.pkl", "wb") as f:
        pickle.dump(model, f)
    print()
    print(f"Modelo guardado en dixon_coles_model_{LEAGUE}.pkl")