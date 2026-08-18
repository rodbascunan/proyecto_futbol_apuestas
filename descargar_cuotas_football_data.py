import os
import io
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Configuración
BASE_URL = "https://www.football-data.co.uk/"
TARGET_URL = "https://www.football-data.co.uk/data.php"
OUTPUT_FILE = "cuotas_mercado_real.csv"

def descargar_y_consolidar_cuotas():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print(f"[1/3] Obteniendo la página principal: {TARGET_URL}...")
    response = requests.get(TARGET_URL, headers=headers)
    if response.status_code != 200:
        print(f"[ERROR] No se pudo acceder a la página. Código de estado: {response.status_code}")
        return

    soup = BeautifulSoup(response.content, "html.parser")
    
    # Encontrar todos los enlaces que terminen en .csv
    csv_links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.lower().endswith(".csv"):
            # Construir URL completa
            full_url = href if href.startswith("http") else BASE_URL + href.lstrip("/")
            if full_url not in csv_links:
                csv_links.append(full_url)

    print(f"[ÉXITO] Se encontraron {len(csv_links)} archivos CSV disponibles.\n")

    dfs = []
    print("[2/3] Descargando y procesando cada archivo CSV...")
    
    for idx, url in enumerate(csv_links, 1):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                # Probar distintas codificaciones comunes en Football-Data
                content = res.content
                try:
                    df = pd.read_csv(io.BytesIO(content), encoding="utf-8")
                except UnicodeDecodeError:
                    df = pd.read_csv(io.BytesIO(content), encoding="latin1")

                # Limpiar filas totalmente vacías
                df = df.dropna(how="all")

                if not df.empty:
                    # Añadir columna con el origen del archivo para trazabilidad
                    df["origen_csv"] = url.split("/")[-1]
                    dfs.append(df)
                    print(f"  [{idx}/{len(csv_links)}] Descargado con éxito: {url.split('/')[-1]} ({len(df)} filas)")
            else:
                print(f"  [{idx}/{len(csv_links)}] Falló la descarga ({res.status_code}): {url}")
        except Exception as e:
            print(f"  [{idx}/{len(csv_links)}] Error al procesar {url}: {e}")

    if not dfs:
        print("\n[ERROR] No se pudo procesar ningún archivo CSV.")
        return

    print("\n[3/3] Consolidando datos en un único CSV...")
    # Unir todos los DataFrames
    df_consolidado = pd.concat(dfs, ignore_index=True, sort=False)

    # Guardar en el directorio actual
    df_consolidado.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print("\n" + "="*60)
    print(f"[PROCESO FINALIZADO] Datos consolidados guardados en: {OUTPUT_FILE}")
    print(f"Total de registros acumulados: {len(df_consolidado)}")
    print("="*60)

if __name__ == "__main__":
    descargar_y_consolidar_cuotas()
    