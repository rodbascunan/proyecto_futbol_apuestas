"""
Calcula el promedio movil de tiros a puerta (a favor y en contra) de
cada equipo, usando SOLO sus partidos anteriores en la misma temporada.
Sirve como proxy de "tendencia ofensiva reciente" para el mercado O/U.
"""

import sqlite3
import pandas as pd
from collections import deque

def calcular_rolling_shots(db_path, league_code, season_labels, ventana=5, min_partidos=5):
    conn = sqlite3.connect(db_path)
    placeholders = ",".join(["?"] * len(season_labels))
    query = f"""
        SELECT m.match_id, s.label AS season, m.match_date,
               t1.name AS home_team, t2.name AS away_team,
               m.ft_home_goals AS hg, m.ft_away_goals AS ag,
               m.home_shots_target AS hst, m.away_shots_target AS ast
        FROM matches m
        JOIN leagues l ON l.league_id = m.league_id
        JOIN seasons s ON s.season_id = m.season_id
        JOIN teams t1 ON t1.team_id = m.home_team_id
        JOIN teams t2 ON t2.team_id = m.away_team_id
        WHERE l.code = ? AND s.label IN ({placeholders})
        ORDER BY s.label, m.match_date
    """
    df = pd.read_sql(query, conn, params=(league_code, *season_labels))
    conn.close()

    resultados = []
    for season, grupo in df.groupby("season"):
        stats = {}  # team -> {'for': deque, 'against': deque}

        for _, row in grupo.iterrows():
            home, away = row["home_team"], row["away_team"]
            hst, ast = row["hst"], row["ast"]

            for t in (home, away):
                if t not in stats:
                    stats[t] = {"for": deque(maxlen=ventana), "against": deque(maxlen=ventana)}

            home_listo = len(stats[home]["for"]) >= min_partidos
            away_listo = len(stats[away]["for"]) >= min_partidos

            if home_listo and away_listo and pd.notna(hst) and pd.notna(ast):
                home_avg_for = sum(stats[home]["for"]) / len(stats[home]["for"])
                away_avg_for = sum(stats[away]["for"]) / len(stats[away]["for"])
                home_avg_against = sum(stats[home]["against"]) / len(stats[home]["against"])
                away_avg_against = sum(stats[away]["against"]) / len(stats[away]["against"])

                resultados.append({
                    "match_id": row["match_id"], "season": season, "match_date": row["match_date"],
                    "home_team": home, "away_team": away,
                    "home_avg_for": home_avg_for, "away_avg_for": away_avg_for,
                    "home_avg_against": home_avg_against, "away_avg_against": away_avg_against,
                    "proxy_total": home_avg_for + away_avg_for,
                    "hg": row["hg"], "ag": row["ag"],
                })

            # Actualizar despues de registrar
            if pd.notna(hst) and pd.notna(ast):
                stats[home]["for"].append(hst)
                stats[home]["against"].append(ast)
                stats[away]["for"].append(ast)
                stats[away]["against"].append(hst)

    out = pd.DataFrame(resultados)
    if not out.empty:
        out["total_goles"] = out["hg"] + out["ag"]
        out["resultado_ou"] = out["total_goles"].apply(lambda g: "over" if g > 2.5 else "under")
    return out


if __name__ == "__main__":
    df = calcular_rolling_shots("futbol_apuestas.db", "SP1", ["2024-2025"])
    print(f"Partidos procesados: {len(df)}")
    print(df[["match_date","home_team","home_avg_for","away_team","away_avg_for","proxy_total","resultado_ou"]].head(10).to_string(index=False))
    