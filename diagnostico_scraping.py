"""
Diagnostico de acceso: probar si FBref y Understat responden normalmente
desde tu conexion (a diferencia del sandbox de Claude, que las bloquea
a nivel de infraestructura de red).

Este script NO extrae datos todavia -- solo confirma si hay acceso basico,
con un User-Agent de navegador real y pausas prudentes entre requests.
"""

import requests
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

SITIOS = {
    "FBref (Eredivisie)": "https://fbref.com/en/comps/23/Eredivisie-Stats",
    "FBref (Championship)": "https://fbref.com/en/comps/10/Championship-Stats",
    "Understat (EPL)": "https://understat.com/league/EPL",
}


def probar_sitio(nombre, url):
    print(f"--- {nombre} ---")
    print(f"  URL: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"  Status code: {resp.status_code}")
        print(f"  Tamano de respuesta: {len(resp.text)} caracteres")
        if resp.status_code == 200:
            # Chequeo simple: la pagina real deberia tener contenido sustancial,
            # no una pagina de bloqueo/captcha (que suelen ser muy chicas)
            if len(resp.text) > 5000:
                print("  [OK] Respuesta parece valida (tamano razonable)")
            else:
                print("  [AVISO] Respuesta muy chica -- podria ser una pagina de bloqueo/captcha")
                print(f"  Primeros 300 caracteres: {resp.text[:300]}")
        elif resp.status_code == 403:
            print("  [BLOQUEADO] 403 Forbidden -- el sitio esta rechazando la solicitud")
        elif resp.status_code == 429:
            print("  [RATE LIMIT] 429 Too Many Requests -- hay que esperar mas entre requests")
        else:
            print(f"  [INESPERADO] Status {resp.status_code}, revisar manualmente")
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR DE CONEXION] {e}")
    print()


if __name__ == "__main__":
    for nombre, url in SITIOS.items():
        probar_sitio(nombre, url)
        time.sleep(4)  # pausa prudente entre sitios distintos

    print("=== Resumen ===")
    print("Si todos dieron [OK]: podemos construir el scraper completo.")
    print("Si alguno dio [BLOQUEADO] o [AVISO]: ese sitio en particular no sera viable")
    print("  desde tu conexion tampoco, y hay que descartarlo o probar otra tecnica.")
