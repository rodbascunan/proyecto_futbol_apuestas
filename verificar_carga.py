import sqlite3

conn = sqlite3.connect('futbol_apuestas.db')
cur = conn.cursor()

query = """
    SELECT l.name, l.code, s.label, COUNT(*)
    FROM matches m
    JOIN leagues l ON l.league_id = m.league_id
    JOIN seasons s ON s.season_id = m.season_id
    WHERE l.code IN ('E0', 'SP1', 'N1', 'P1', 'E1', 'B1', 'T1', 'G1', 'SC0')
    GROUP BY l.name, s.label
    ORDER BY l.name, s.label
"""

print(f"{'Liga':22s} {'Codigo':7s} {'Temporada':12s} Partidos")
print("-" * 55)

total_por_liga = {}
for nombre, codigo, temporada, n in cur.execute(query).fetchall():
    print(f"{nombre:22s} {codigo:7s} {temporada:12s} {n:4d}")
    total_por_liga[nombre] = total_por_liga.get(nombre, 0) + n

print("-" * 55)
print("\n=== Total de partidos por liga (5 temporadas sumadas) ===")
for nombre, total in total_por_liga.items():
    print(f"  {nombre:22s} {total:5d} partidos")

print(f"\nTotal general: {sum(total_por_liga.values())} partidos")

# Aviso si alguna liga no llego a las 5 temporadas esperadas
print("\n=== Chequeo de temporadas faltantes ===")
conn2 = sqlite3.connect('futbol_apuestas.db')
cur2 = conn2.cursor()
check_query = """
    SELECT l.name, COUNT(DISTINCT s.label)
    FROM matches m
    JOIN leagues l ON l.league_id = m.league_id
    JOIN seasons s ON s.season_id = m.season_id
    WHERE l.code IN ('E0', 'SP1', 'N1', 'P1', 'E1', 'B1', 'T1', 'G1', 'SC0')
    GROUP BY l.name
"""
hay_faltantes = False
for nombre, n_temporadas in cur2.execute(check_query).fetchall():
    if n_temporadas < 5:
        print(f"  [AVISO] {nombre}: solo {n_temporadas} de 5 temporadas cargadas")
        hay_faltantes = True
if not hay_faltantes:
    print("  Todas las ligas tienen las 5 temporadas completas.")

conn.close()
conn2.close()
