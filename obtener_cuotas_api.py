import requests
import pandas as pd
from thefuzz import process


# Registro gratuito en https://the-odds-api.com/ para obtener tu clave de 500 peticiones/mes
API_KEY = "TU_API_KEY_AQUI"  # Reemplaza con tu API key real

# Claves de ligas en The Odds API:
# Premier League: 'soccer_epl'
# La Liga España: 'soccer_spain_la_liga'
# Champions League: 'soccer_uefa_champs_league'
# Primera División Chile: 'soccer_chile_primera_division'
SPORT = "soccer_epl" 
REGION = "eu"   # Casas europeas (Pinnacle, Bet365, 888sport, etc.)
MARKET = "h2h"  # Mercado 1X2


def obtener_equipos_dataset_local():
    """Carga los nombres exactos de equipos que ya existen en tu dataset."""
    try:
        df = pd.read_csv("dataset_xg_con_cuotas.csv")
        # Identificar columnas de equipos
        col_home = next((c for c in ["home_team", "equipo_home", "local", "equipo_local"] if c in df.columns), None)
        col_away = next((c for c in ["away_team", "equipo_away", "visita", "visitante"] if c in df.columns), None)
        
        if col_home and col_away:
            equipos_validos = pd.concat([df[col_home], df[col_away]]).unique().tolist()
            return equipos_validos
    except Exception as e:
        print(f"[AVISO] No se pudo cargar el dataset para mapeo de nombres: {e}")
    return []


def mapear_nombre_equipo(nombre_api, lista_equipos_conocidos, umbral_coincidencia=70):
    """Mapea el nombre proveniente de la API al nombre exacto en tu dataset de xG."""
    if not lista_equipos_conocidos:
        return nombre_api
    
    # Buscar el nombre más cercano
    mejor_coincidencia, puntaje = process.extractOne(nombre_api, lista_equipos_conocidos)
    
    if puntaje >= umbral_coincidencia:
        return mejor_coincidencia
    else:
        print(f"[AVISO] Coincidencia baja para '{nombre_api}'. Se usará el nombre original. (Mejor: {mejor_coincidencia} - {puntaje}%)")
        return nombre_api


def obtener_proximos_partidos_con_cuotas(usar_modo_prueba=False):
    equipos_conocidos = obtener_equipos_dataset_local()

    if usar_modo_prueba or API_KEY == "TU_API_KEY_AQUI":
        print("\n[MODO DEMOSTRACIÓN] Usando datos de prueba estructurados...")
        partidos_raw = [
            {
                "home_team": "Arsenal FC", 
                "away_team": "Chelsea FC",
                "cuota_local": 1.95, "cuota_empate": 3.60, "cuota_visita": 3.90
            },
            {
                "home_team": "FC Barcelona", 
                "away_team": "Real Madrid",
                "cuota_local": 2.20, "cuota_empate": 3.40, "cuota_visita": 3.10
            }
        ]
        
        partidos_procesados = []
        for p in partidos_raw:
            local_mapeado = mapear_nombre_equipo(p["home_team"], equipos_conocidos)
            visita_mapeada = mapear_nombre_equipo(p["away_team"], equipos_conocidos)
            partidos_procesados.append({
                "local": local_mapeado,
                "visita": visita_mapeada,
                "cuota_local": p["cuota_local"],
                "cuota_empate": p["cuota_empate"],
                "cuota_visita": p["cuota_visita"]
            })
        return partidos_procesados

    print(f"\n[1/2] Consultando The Odds API para la liga: {SPORT}...")
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/"
    params = {
        "apiKey": API_KEY,
        "regions": REGION,
        "markets": MARKET,
        "oddsFormat": "decimal",
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"Error al conectar con la API ({response.status_code}): {response.text}")
        return []

    eventos = response.json()
    print(f"[2/2] {len(eventos)} partidos encontrados. Homologando nombres de equipos...")

    partidos_procesados = []

    for evento in eventos:
        home_api = evento["home_team"]
        away_api = evento["away_team"]

        # Homologar nombres contra el CSV
        local_normalizado = mapear_nombre_equipo(home_api, equipos_conocidos)
        visita_normalizada = mapear_nombre_equipo(away_api, equipos_conocidos)

        if evento["bookmakers"]:
            # Tomamos la primera casa de apuestas (ej. Pinnacle o Bet365)
            bookmaker = evento["bookmakers"][0]
            h2h = next((m for m in bookmaker["markets"] if m["key"] == "h2h"), None)

            if h2h:
                cuotas = {outcome["name"]: outcome["price"] for outcome in h2h["outcomes"]}
                
                c_local = cuotas.get(home_api, 0.0)
                c_visita = cuotas.get(away_api, 0.0)
                c_empate = cuotas.get("Draw", 0.0)

                if c_local > 0 and c_visita > 0 and c_empate > 0:
                    partidos_procesados.append({
                        "local": local_normalizado,
                        "visita": visita_normalizada,
                        "cuota_local": c_local,
                        "cuota_empate": c_empate,
                        "cuota_visita": c_visita,
                        "casa_apuestas": bookmaker["title"]
                    })

    return partidos_procesados


if __name__ == "__main__":
    partidos = obtener_proximos_partidos_con_cuotas(usar_modo_prueba=True)
    print("\nPartidos listos para enviar al modelo predictivo:")
    for p in partidos:
        print(p)
        