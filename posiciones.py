"""
Calculo de posicion en tabla ANTES de cada partido (no la tabla final).
Se usa el criterio de desempate estandar: puntos, diferencia de gol, goles a favor.
"""

import sqlite3
import pandas as pd


def calcular_posiciones(db_path, league_code, season_labels, min_jugados=5):
    conn = sqlite3.connect(db_path)
    placeholders = ",".join(["?"] * len(season_labels))
    query = f"""
        SELECT m.match_id, s.label AS season, m.match_date,
               t1.name AS home_team, t2.name AS away_team,
               m.ft_home_goals AS hg, m.ft_away_goals AS ag
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
        stats = {}  # team -> {puntos, gf, ga, jugados}

        for _, row in grupo.iterrows():
            home, away = row["home_team"], row["away_team"]
            for t in (home, away):
                if t not in stats:
                    stats[t] = {"puntos": 0, "gf": 0, "ga": 0, "jugados": 0}

            # --- Tabla ANTES de este partido ---
            tabla = [
                (t, s["puntos"], s["gf"] - s["ga"], s["gf"], s["jugados"])
                for t, s in stats.items()
            ]
            tabla.sort(key=lambda x: (-x[1], -x[2], -x[3]))
            posicion = {t: i + 1 for i, (t, *_ ) in enumerate(tabla)}
            jugados_map = {t: s["jugados"] for t, s in stats.items()}

            home_pos = posicion.get(home) if jugados_map.get(home, 0) >= min_jugados else None
            away_pos = posicion.get(away) if jugados_map.get(away, 0) >= min_jugados else None

            resultados.append({
                "match_id": row["match_id"], "season": season, "match_date": row["match_date"],
                "home_team": home, "away_team": away,
                "home_pos": home_pos, "away_pos": away_pos,
                "hg": row["hg"], "ag": row["ag"],
            })

            # --- Actualizar stats DESPUES de registrar la tabla previa ---
            hg, ag = row["hg"], row["ag"]
            stats[home]["gf"] += hg; stats[home]["ga"] += ag; stats[home]["jugados"] += 1
            stats[away]["gf"] += ag; stats[away]["ga"] += hg; stats[away]["jugados"] += 1
            if hg > ag:
                stats[home]["puntos"] += 3
            elif ag > hg:
                stats[away]["puntos"] += 3
            else:
                stats[home]["puntos"] += 1
                stats[away]["puntos"] += 1

    out = pd.DataFrame(resultados)
    out["actual"] = out.apply(
        lambda r: "home" if r["hg"] > r["ag"] else ("away" if r["ag"] > r["hg"] else "draw"), axis=1
    )
    return out


if __name__ == "__main__":
    # Prueba rapida con los datos disponibles localmente
    df = calcular_posiciones("futbol_apuestas.db", "SP1", ["2024-2025"])
    print(f"Partidos procesados: {len(df)}")
    print(df[["match_date", "home_team", "home_pos", "away_team", "away_pos"]].tail(10).to_string(index=False))
