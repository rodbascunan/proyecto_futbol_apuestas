import sqlite3
import pandas as pd
import webbrowser

DB_PATH = 'futbol_apuestas.db'

def obtener_columna_nombre_liga(conn):
    """Detecta automáticamente la columna con el nombre de la liga."""
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(leagues)")
        columns = [row[1] for row in cursor.fetchall()]
        posibles = ['league_name', 'name', 'caption', 'league_code', 'title']
        for col in posibles:
            if col in columns:
                return col
        if len(columns) > 1:
            return columns[1]
    except Exception:
        pass
    return None

def cargar_partidos_y_cuotas(conn):
    col_liga = obtener_columna_nombre_liga(conn)
    
    if col_liga:
        join_liga = "LEFT JOIN leagues l ON m.league_id = l.league_id"
        select_liga = f"COALESCE(l.{col_liga}, CAST(m.league_id AS TEXT)) AS league"
    else:
        join_liga = ""
        select_liga = "CAST(m.league_id AS TEXT) AS league"

    query = f"""
    SELECT 
        m.match_id,
        {select_liga},
        CAST(m.season_id AS TEXT) AS season,
        m.match_date AS date,
        CAST(m.home_team_id AS TEXT) AS home_team,
        CAST(m.away_team_id AS TEXT) AS away_team,
        m.ft_home_goals,
        m.ft_away_goals,
        m.ft_result AS ftr,
        o_home.price AS cuota_local,
        o_draw.price AS cuota_empate,
        o_away.price AS cuota_visita
    FROM matches m
    {join_liga}
    LEFT JOIN (
        SELECT match_id, AVG(price) AS price
        FROM odds
        WHERE UPPER(selection) IN ('H', '1', 'HOME')
        GROUP BY match_id
    ) o_home ON m.match_id = o_home.match_id
    LEFT JOIN (
        SELECT match_id, AVG(price) AS price
        FROM odds
        WHERE UPPER(selection) IN ('D', 'X', 'DRAW')
        GROUP BY match_id
    ) o_draw ON m.match_id = o_draw.match_id
    LEFT JOIN (
        SELECT match_id, AVG(price) AS price
        FROM odds
        WHERE UPPER(selection) IN ('A', '2', 'AWAY')
        GROUP BY match_id
    ) o_away ON m.match_id = o_away.match_id
    WHERE m.ft_result IS NOT NULL
    ORDER BY m.league_id, m.season_id, m.match_date ASC
    """
    return pd.read_sql_query(query, conn)

def procesar_diferencia_posiciones(df):
    resultados = []
    
    for (league, season), group in df.groupby(['league', 'season']):
        puntos = {}
        partidos_jugados = {}
        
        equipos = set(group['home_team']).union(set(group['away_team']))
        for eq in equipos:
            puntos[eq] = 0
            partidos_jugados[eq] = 0
            
        for _, match in group.iterrows():
            h_team = match['home_team']
            a_team = match['away_team']
            
            # Evaluación a partir de la jornada 4 por equipo para consolidar la tabla
            if partidos_jugados[h_team] >= 3 and partidos_jugados[a_team] >= 3:
                tabla = sorted(puntos.items(), key=lambda x: x[1], reverse=True)
                posiciones = {eq: pos + 1 for pos, (eq, _) in enumerate(tabla)}
                
                pos_h = posiciones[h_team]
                pos_a = posiciones[a_team]
                dif_pos = pos_a - pos_h
                
                resultados.append({
                    'league': league,
                    'season': season,
                    'home_team': h_team,
                    'away_team': a_team,
                    'dif_pos': dif_pos,
                    'ftr': str(match['ftr']).upper().strip(),
                    'cuota_local': match['cuota_local'],
                    'cuota_empate': match['cuota_empate'],
                    'cuota_visita': match['cuota_visita']
                })
            
            partidos_jugados[h_team] += 1
            partidos_jugados[a_team] += 1
            
            res = str(match['ftr']).upper().strip()
            if res == 'H':
                puntos[h_team] += 3
            elif res == 'A':
                puntos[a_team] += 3
            elif res == 'D':
                puntos[h_team] += 1
                puntos[a_team] += 1
                
    return pd.DataFrame(resultados)

def calcular_metricas(grp, resultado_evaluado, col_cuota, stake=100):
    grp_valid = grp.dropna(subset=[col_cuota])
    n = len(grp_valid)
    if n == 0:
        return "0.0%", "0.00%", "$0"
    
    ganados = grp_valid[grp_valid['ftr'] == resultado_evaluado]
    n_win = len(ganados)
    pct_win = (n_win / len(grp)) * 100
    
    inversion_total = n * stake
    retorno_total = (ganados[col_cuota].astype(float) * stake).sum()
    pnl = retorno_total - inversion_total
    roi = (pnl / inversion_total) * 100 if inversion_total > 0 else 0.0
    
    return f"{pct_win:.1f}%", f"{roi:+.2f}%", f"${pnl:+,.0f}"

def generar_tabla_resumen(grp_data, stake=100):
    resumen = []
    for tramo, grp in grp_data.groupby('tramo_diferencia', observed=True):
        n_partidos = len(grp)
        if n_partidos == 0:
            continue
        
        win_h, roi_h, pnl_h = calcular_metricas(grp, 'H', 'cuota_local', stake)
        win_d, roi_d, pnl_d = calcular_metricas(grp, 'D', 'cuota_empate', stake)
        win_a, roi_a, pnl_a = calcular_metricas(grp, 'A', 'cuota_visita', stake)

        resumen.append({
            'Tramo Diferencia': tramo,
            'Partidos': n_partidos,
            '% Win L': win_h,
            'ROI L': roi_h,
            'P&L L ($)': pnl_h,
            '% Win E': win_d,
            'ROI E': roi_d,
            'P&L E ($)': pnl_d,
            '% Win V': win_a,
            'ROI V': roi_a,
            'P&L V ($)': pnl_a
        })
    return pd.DataFrame(resumen)

def analizar_patron(df_res, stake=100):
    if df_res.empty:
        print("No se encontraron registros suficientes.")
        return

    bins = [-20, -11, -6, -1, 0, 5, 10, 20]
    labels = [
        'Local Muy Inferior (-20 a -11)',
        'Local Inferior (-10 a -6)',
        'Local Lig. Inferior (-5 a -1)',
        'Tabla Igualada (0)',
        'Local Lig. Superior (+1 a +5)',
        'Local Superior (+6 a +10)',
        'Local Muy Superior (+11 a +20)'
    ]
    
    df_res['tramo_diferencia'] = pd.cut(df_res['dif_pos'], bins=bins, labels=labels)
    
    # Configuración de ancho de Pandas en terminal
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 1000)
    
    df_global = generar_tabla_resumen(df_res, stake)
    
    print("\n" + "="*120)
    print(f" RESUMEN CONSOLIDADO GLOBAL (Apostando ${stake} por partido)")
    print(" L = Local | E = Empate | V = Visitante")
    print(" P&L = Profit & Loss (Ganancia o Pérdida en dinero)")
    print("="*120)
    print(df_global.to_string(index=False))
    
    print("\n" + "="*120)
    print(" DESGLOSE INDIVIDUAL POR LIGA")
    print("="*120)
    
    # Construcción de informe en HTML
    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Reporte de Apuestas por Posición</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
            h1 {{ color: #333; }}
            h2 {{ color: #0056b3; margin-top: 30px; }}
            h3 {{ color: #495057; margin-top: 25px; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; background-color: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }}
            th, td {{ border: 1px solid #dee2e6; padding: 10px; text-align: center; }}
            th {{ background-color: #343a40; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>Reporte Estrategia Apuestas por Diferencia de Posición</h1>
        <p><b>Stake evaluado:</b> ${stake} por partido en cada opción de manera independiente.</p>
        <h2>RESUMEN CONSOLIDADO GLOBAL</h2>
        {df_global.to_html(index=False, classes='table')}
        <h2>DESGLOSE POR LIGAS</h2>
    """
    
    for league, grp_league in df_res.groupby('league'):
        print(f"\n>>> LIGA: {league} (Partidos: {len(grp_league)}) <<<")
        df_liga = generar_tabla_resumen(grp_league, stake)
        if not df_liga.empty:
            print(df_liga.to_string(index=False))
            html_content += f"<h3>LIGA: {league} (Partidos: {len(grp_league)})</h3>" + df_liga.to_html(index=False, classes='table')
        else:
            print("Sin datos suficientes.")

    html_content += "</body></html>"

    with open("reporte_apuestas.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("\n" + "="*120)
    print("¡Reporte completo guardado! Abriendo 'reporte_apuestas.html' en el navegador...")
    webbrowser.open("reporte_apuestas.html")

if __name__ == '__main__':
    STAKE_POR_PARTIDO = 100  # $100 apostados en cada partido individual
    
    conn = sqlite3.connect(DB_PATH)
    print("Cargando base de datos...")
    df_matches = cargar_partidos_y_cuotas(conn)
    conn.close()
    
    print(f"Total partidos en la base de datos: {len(df_matches)}")
    print("Procesando tablas de posiciones fecha a fecha...")
    df_procesado = procesar_diferencia_posiciones(df_matches)
    
    print(f"Total partidos evaluados (desde Jornada 4): {len(df_procesado)}")
    analizar_patron(df_procesado, stake=STAKE_POR_PARTIDO)
    