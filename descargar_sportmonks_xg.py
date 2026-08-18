"""
Descarga partidos de Scottish Premiership con xG desde la API de Sportmonks.

IMPORTANTE: pega tu token API_TOKEN abajo, directamente en tu computadora.
Nunca compartas este archivo (ya con el token pegado) por chat, email, o
lo subas a un repositorio publico.
"""

import requests
import pandas as pd
import time

API_TOKEN = "uRAqmaGk6aDpDBgyE9KrcqnxCts3L5J5UsrUMqPe3drpNm6pk6AEp1B7Cwmj"   # <-- reemplazar en tu computadora
BASE_URL = "https://api.sportmonks.com/v3/football"

SEASON_ID = None  # lo buscamos en el paso 1 de este script


def buscar_liga_scotland():
    """Paso 1: encontrar el ID de Scottish Premiership y sus temporadas disponibles.
    OJO: la busqueda por texto de Sportmonks es difusa y puede devolver ligas de
    otros paises con nombres parecidos (ej. "Superliga" de Dinamarca aparecio en
    una prueba real). Por eso filtramos por nombre EXACTO "Premiership",
    excluyendo variantes de Play-Offs."""
    resp = requests.get(
        f"{BASE_URL}/leagues",
        params={"api_token": API_TOKEN, "search": "Scottish Premiership"},
    )
    resp.raise_for_status()
    data = resp.json()
    print("Ligas encontradas (busqueda difusa, puede incluir falsos positivos):")
    for liga in data.get("data", []):
        print(f"  ID: {liga['id']}  |  Nombre: {liga['name']}  |  Pais: {liga.get('country_id')}")

    candidatas = [
        liga for liga in data.get("data", [])
        if liga["name"].strip().lower() == "premiership" and "play" not in liga["name"].lower()
    ]

    if not candidatas:
        print("\n  [AVISO] No se encontro una liga con nombre EXACTO 'Premiership'.")
        print("  Revisa la lista de arriba a mano y ajusta el filtro si hace falta.")
        return []

    if len(candidatas) > 1:
        print(f"\n  [AVISO] Hay {len(candidatas)} ligas llamadas 'Premiership' (distintos paises).")
        print("  Verifica manualmente cual country_id corresponde a Escocia antes de continuar.")

    print(f"\n  Liga seleccionada: ID {candidatas[0]['id']} ({candidatas[0]['name']}, pais {candidatas[0].get('country_id')})")
    return candidatas


def buscar_temporadas(league_id):
    """Paso 2: ver que temporadas de esa liga estan disponibles en tu plan."""
    resp = requests.get(
        f"{BASE_URL}/leagues/{league_id}",
        params={"api_token": API_TOKEN, "include": "seasons"},
    )
    resp.raise_for_status()
    data = resp.json()
    temporadas = data.get("data", {}).get("seasons", [])
    print(f"\nTemporadas disponibles para league_id={league_id}:")
    for t in temporadas:
        print(f"  season_id: {t['id']}  |  {t.get('name')}")
    return temporadas


def descargar_partidos_con_xg(season_id):
    """Paso 3: descargar los partidos de una temporada con su xG."""
    partidos = []
    page = 1
    while True:
        resp = requests.get(
            f"{BASE_URL}/fixtures",
            params={
                "api_token": API_TOKEN,
                "filters": f"fixtureSeasons:{season_id}",
                "include": "participants;scores;xgfixture",
                "page": page,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", [])
        if not items:
            break
        partidos.extend(items)
        print(f"  Pagina {page}: {len(items)} partidos descargados")
        if not data.get("pagination", {}).get("has_more", False):
            break
        page += 1
        time.sleep(0.5)  # ser prudente con el rate limit del plan gratis
    return partidos


def parsear_a_dataframe(partidos):
    filas = []
    for p in partidos:
        participantes = p.get("participants", [])
        home = next((x for x in participantes if x.get("meta", {}).get("location") == "home"), None)
        away = next((x for x in participantes if x.get("meta", {}).get("location") == "away"), None)

        xg_data = p.get("xgfixture", [])
        xg_home = next((x["data"]["value"] for x in xg_data if x.get("location") == "home"), None)
        xg_away = next((x["data"]["value"] for x in xg_data if x.get("location") == "away"), None)

        filas.append({
            "fixture_id": p["id"],
            "fecha": p.get("starting_at"),
            "home_team": home["name"] if home else None,
            "away_team": away["name"] if away else None,
            "xg_home": xg_home,
            "xg_away": xg_away,
        })
    return pd.DataFrame(filas)


def probar_acceso_basico(season_id):
    """Diagnostico: probar el endpoint SIN el include de xG, para saber si
    el problema es de la temporada en general o especifico del addon de xG."""
    resp = requests.get(
        f"{BASE_URL}/fixtures",
        params={
            "api_token": API_TOKEN,
            "filters": f"fixtureSeasons:{season_id}",
            "include": "participants",
            "page": 1,
        },
    )
    print(f"  Prueba SIN xG -> status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"  Respuesta: {resp.text[:300]}")
    return resp.status_code == 200


if __name__ == "__main__":
    print("=== Paso 1: buscar la liga ===")
    ligas = buscar_liga_scotland()

    if not ligas:
        print("No se encontro la liga. Revisa el nombre de busqueda o tu plan.")
    else:
        league_id = ligas[0]["id"]
        print(f"\n=== Paso 2: buscar temporadas de league_id={league_id} ===")
        temporadas = buscar_temporadas(league_id)

        if temporadas:
            # Elegir la temporada MAS RECIENTE por nombre (ej. "2025/2026"),
            # no la primera de la lista (el orden de la API no es cronologico)
            temporadas_ordenadas = sorted(temporadas, key=lambda t: t.get("name", ""), reverse=True)
            season_id = temporadas_ordenadas[0]["id"]
            print(f"\nTemporada mas reciente detectada: {temporadas_ordenadas[0]['name']} (season_id={season_id})")

            print(f"\n=== Paso 2.5: diagnostico de acceso (sin xG primero) ===")
            acceso_ok = probar_acceso_basico(season_id)

            if not acceso_ok:
                print("\n  El 403 ocurre incluso SIN pedir xG -> el plan gratis no da acceso")
                print("  a fixtures de esta temporada/liga por algun otro motivo (revisar plan).")
            else:
                print(f"\n=== Paso 3: descargando partidos de season_id={season_id} (con xG) ===")
                partidos = descargar_partidos_con_xg(season_id)
                df = parsear_a_dataframe(partidos)
                print(f"\nTotal partidos con datos: {len(df)}")
                print(df.head(10).to_string(index=False))
                df.to_csv("sportmonks_sc0_xg.csv", index=False)
                print("\nGuardado en sportmonks_sc0_xg.csv")
