"""
Fase 2 — Extracción y carga
============================
Descarga los CSV de football-data.co.uk para las 4 ligas definidas en la
Fase 1, y los carga al esquema SQLite diseñado en la Fase 1
(futbol_apuestas.db).

Diseñado para correr diariamente sin duplicar datos: reintentar sobre un
partido ya cargado no genera filas repetidas, gracias a las restricciones
UNIQUE del esquema.

IMPORTANTE: este script necesita acceso normal a internet hacia
football-data.co.uk. Debe ejecutarse en tu máquina o servidor, no dentro
de un sandbox con lista blanca de dominios restringida.

Uso:
    python3 extract_load.py                  # temporada actual, las 4 ligas
    python3 extract_load.py --season 2425     # una temporada específica
    python3 extract_load.py --league SP1      # solo una liga
    python3 extract_load.py --offline archivo.csv --league SP1 --season 2526
                                              # cargar un CSV ya descargado
                                              # (útil para pruebas o si no
                                              # hay red hacia el sitio)
"""

import argparse
import csv
import io
import json
import sqlite3
import sys
from datetime import date, datetime

try:
    import requests
except ImportError:
    requests = None  # el modo --offline no lo necesita

DB_PATH = "futbol_apuestas.db"

LEAGUES = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "N1": "Eredivisie",
    "P1": "Primeira Liga",
    "E1": "Championship",
    "B1": "Jupiler Pro League",
    "T1": "Super Lig",
    "G1": "Super League Greece",
    "SC0": "Scottish Premiership",
}

# Casas de apuestas cubiertas por mercado. football-data.co.uk usa prefijos
# de columna inconsistentes entre mercados (ej. Pinnacle es "PS" en 1X2 pero
# "P" en Over/Under y Hándicap Asiático) — de ahí que estén separados por
# mercado en vez de un único diccionario. Se puede ampliar agregando más
# entradas; ver notes.txt del sitio para la lista completa de prefijos.
BOOKMAKERS = {
    "1x2": {"B365": "Bet365", "PS": "Pinnacle", "Max": "Market Max",
             "Avg": "Market Avg", "BFE": "Betfair Exchange"},
    "ou_2_5": {"B365": "Bet365", "P": "Pinnacle", "Max": "Market Max",
               "Avg": "Market Avg", "BFE": "Betfair Exchange"},
    "ah": {"B365": "Bet365", "P": "Pinnacle", "Max": "Market Max",
           "Avg": "Market Avg", "BFE": "Betfair Exchange"},
}


# ----------------------------------------------------------------------
# Utilidades de temporada
# ----------------------------------------------------------------------
def current_season_code(today=None):
    """Devuelve el código de temporada de football-data.co.uk (ej. '2526')
    para la fecha actual. La temporada europea corre de julio a junio."""
    today = today or date.today()
    start_year = today.year if today.month >= 7 else today.year - 1
    end_year = start_year + 1
    return f"{str(start_year)[2:]}{str(end_year)[2:]}"


def season_label(season_code):
    """'2526' -> '2025-2026'"""
    start_year = 2000 + int(season_code[:2])
    end_year = 2000 + int(season_code[2:])
    return f"{start_year}-{end_year}"


def build_url(league_code, season_code):
    return f"https://www.football-data.co.uk/mmz4281/{season_code}/{league_code}.csv"


# ----------------------------------------------------------------------
# Descarga
# ----------------------------------------------------------------------
def download_csv(url):
    if requests is None:
        raise RuntimeError(
            "El paquete 'requests' no está instalado. Instálalo con: "
            "pip install requests --break-system-packages"
        )
    headers = {"User-Agent": "Mozilla/5.0 (compatible; futbol-etl/1.0)"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8-sig"  # el CSV trae BOM al inicio
    return resp.text


# ----------------------------------------------------------------------
# Parseo de una fila del CSV a cuotas en formato largo
# ----------------------------------------------------------------------
def _to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_odds_from_row(row):
    """A partir de una fila del CSV (dict), genera una lista de dicts listos
    para insertar en la tabla `odds`. Ignora columnas vacías (comunes en
    partidos donde una casa no cotizó ese mercado)."""
    odds_rows = []

    def add(bookmaker, market_type, snapshot, selection, raw_price, line=None):
        price = _to_float(raw_price)
        if price is None:
            return
        odds_rows.append({
            "bookmaker": bookmaker,
            "market_type": market_type,
            "snapshot": snapshot,
            "selection": selection,
            "price": price,
            "handicap_line": _to_float(line),
        })

    # Mercado 1X2 (apertura y cierre)
    for prefix, name in BOOKMAKERS["1x2"].items():
        add(name, "1x2", "open", "home", row.get(f"{prefix}H"))
        add(name, "1x2", "open", "draw", row.get(f"{prefix}D"))
        add(name, "1x2", "open", "away", row.get(f"{prefix}A"))
        add(name, "1x2", "close", "home", row.get(f"{prefix}CH"))
        add(name, "1x2", "close", "draw", row.get(f"{prefix}CD"))
        add(name, "1x2", "close", "away", row.get(f"{prefix}CA"))

    # Mercado Over/Under 2.5 goles (apertura y cierre)
    for prefix, name in BOOKMAKERS["ou_2_5"].items():
        add(name, "ou_2_5", "open", "over", row.get(f"{prefix}>2.5"))
        add(name, "ou_2_5", "open", "under", row.get(f"{prefix}<2.5"))
        add(name, "ou_2_5", "close", "over", row.get(f"{prefix}C>2.5"))
        add(name, "ou_2_5", "close", "under", row.get(f"{prefix}C<2.5"))

    # Hándicap Asiático (apertura y cierre). La línea es única por partido,
    # no por casa (así viene en el CSV de origen: columnas AHh / AHCh).
    ah_line_open = row.get("AHh")
    ah_line_close = row.get("AHCh")
    for prefix, name in BOOKMAKERS["ah"].items():
        add(name, "ah", "open", "home_ah", row.get(f"{prefix}AHH"), line=ah_line_open)
        add(name, "ah", "open", "away_ah", row.get(f"{prefix}AHA"), line=ah_line_open)
        add(name, "ah", "close", "home_ah", row.get(f"{prefix}CAHH"), line=ah_line_close)
        add(name, "ah", "close", "away_ah", row.get(f"{prefix}CAHA"), line=ah_line_close)

    return odds_rows


# ----------------------------------------------------------------------
# Carga a la base de datos
# ----------------------------------------------------------------------
def get_or_create_league(conn, code, name):
    cur = conn.execute("SELECT league_id FROM leagues WHERE code = ?", (code,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        "INSERT INTO leagues (code, name, country) VALUES (?, ?, ?)",
        (code, name, ""),
    )
    return cur.lastrowid


def get_or_create_season(conn, league_id, label):
    cur = conn.execute(
        "SELECT season_id FROM seasons WHERE league_id = ? AND label = ?",
        (league_id, label),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        "INSERT INTO seasons (league_id, label) VALUES (?, ?)",
        (league_id, label),
    )
    return cur.lastrowid


def get_or_create_team(conn, name):
    name = name.strip()
    cur = conn.execute("SELECT team_id FROM teams WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur = conn.execute("INSERT INTO teams (name) VALUES (?)", (name,))
    return cur.lastrowid


def parse_match_date(raw_date):
    """El CSV usa dd/mm/yy o dd/mm/yyyy según la temporada."""
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw_date, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Formato de fecha no reconocido: {raw_date!r}")


def load_csv_text(conn, csv_text, league_code, season_code, source_file):
    league_name = LEAGUES.get(league_code, league_code)
    league_id = get_or_create_league(conn, league_code, league_name)
    season_id = get_or_create_season(conn, league_id, season_label(season_code))

    reader = csv.DictReader(io.StringIO(csv_text))
    stats = {"filas_leidas": 0, "partidos_nuevos": 0, "partidos_duplicados": 0,
             "cuotas_insertadas": 0}

    for row in reader:
        stats["filas_leidas"] += 1

        # 1) Staging: guardar la fila cruda tal cual, sin transformar
        conn.execute(
            "INSERT INTO raw_matches_import (league_code, season_label, source_file, row_json) "
            "VALUES (?, ?, ?, ?)",
            (league_code, season_label(season_code), source_file, json.dumps(row, ensure_ascii=False)),
        )

        if not row.get("HomeTeam") or not row.get("AwayTeam"):
            continue  # fila vacía o incompleta al final del archivo

        home_id = get_or_create_team(conn, row["HomeTeam"])
        away_id = get_or_create_team(conn, row["AwayTeam"])
        match_date = parse_match_date(row["Date"])

        cur = conn.execute(
            """INSERT OR IGNORE INTO matches
               (league_id, season_id, home_team_id, away_team_id, match_date, match_time,
                referee, attendance,
                ft_home_goals, ft_away_goals, ft_result,
                ht_home_goals, ht_away_goals, ht_result,
                home_shots, away_shots, home_shots_target, away_shots_target,
                home_corners, away_corners, home_fouls, away_fouls,
                home_yellow, away_yellow, home_red, away_red, source)
               VALUES (?,?,?,?,?,?, ?,?, ?,?,?, ?,?,?, ?,?,?,?, ?,?,?,?, ?,?,?,?, ?)""",
            (
                league_id, season_id, home_id, away_id, match_date, row.get("Time"),
                row.get("Referee"), row.get("Attendance") or None,
                row.get("FTHG") or None, row.get("FTAG") or None, row.get("FTR") or None,
                row.get("HTHG") or None, row.get("HTAG") or None, row.get("HTR") or None,
                row.get("HS") or None, row.get("AS") or None,
                row.get("HST") or None, row.get("AST") or None,
                row.get("HC") or None, row.get("AC") or None,
                row.get("HF") or None, row.get("AF") or None,
                row.get("HY") or None, row.get("AY") or None,
                row.get("HR") or None, row.get("AR") or None,
                "football-data.co.uk",
            ),
        )

        if cur.rowcount == 0:
            # Ya existía (mismo league_id + fecha + local + visitante): se ignora.
            stats["partidos_duplicados"] += 1
            match_id = conn.execute(
                "SELECT match_id FROM matches WHERE league_id=? AND match_date=? "
                "AND home_team_id=? AND away_team_id=?",
                (league_id, match_date, home_id, away_id),
            ).fetchone()[0]
        else:
            stats["partidos_nuevos"] += 1
            match_id = cur.lastrowid

        for odd in parse_odds_from_row(row):
            cur2 = conn.execute(
                """INSERT OR IGNORE INTO odds
                   (match_id, bookmaker, market_type, snapshot, selection, handicap_line, price)
                   VALUES (?,?,?,?,?,?,?)""",
                (match_id, odd["bookmaker"], odd["market_type"], odd["snapshot"],
                 odd["selection"], odd["handicap_line"], odd["price"]),
            )
            if cur2.rowcount:
                stats["cuotas_insertadas"] += 1

    conn.commit()
    return stats


def load_league_season(conn, league_code, season_code, offline_path=None):
    if offline_path:
        with open(offline_path, encoding="utf-8-sig") as f:
            csv_text = f.read()
        source = offline_path
    else:
        url = build_url(league_code, season_code)
        csv_text = download_csv(url)
        source = url

    stats = load_csv_text(conn, csv_text, league_code, season_code, source)
    return stats


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Extracción y carga de football-data.co.uk")
    parser.add_argument("--league", choices=list(LEAGUES.keys()),
                         help="Cargar solo esta liga (por defecto: las 4)")
    parser.add_argument("--season", help="Código de temporada, ej. 2425 (por defecto: temporada actual)")
    parser.add_argument("--offline", help="Ruta a un CSV ya descargado, en vez de bajarlo de internet")
    parser.add_argument("--db", default=DB_PATH, help="Ruta al archivo .db (por defecto: futbol_apuestas.db)")
    args = parser.parse_args()

    season_code = args.season or current_season_code()
    leagues = [args.league] if args.league else list(LEAGUES.keys())

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON")

    for league_code in leagues:
        print(f"\n=== {LEAGUES[league_code]} ({league_code}), temporada {season_label(season_code)} ===")
        try:
            stats = load_league_season(conn, league_code, season_code, offline_path=args.offline)
            print(f"  Filas leídas:          {stats['filas_leidas']}")
            print(f"  Partidos nuevos:       {stats['partidos_nuevos']}")
            print(f"  Partidos ya existentes:{stats['partidos_duplicados']}")
            print(f"  Cuotas insertadas:     {stats['cuotas_insertadas']}")
        except Exception as e:
            print(f"  ERROR al cargar {league_code}: {e}", file=sys.stderr)

    conn.close()


if __name__ == "__main__":
    main()
