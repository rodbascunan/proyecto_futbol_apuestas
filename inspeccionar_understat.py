import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

url = "https://understat.com/league/EPL/2024"
resp = requests.get(url, headers=HEADERS, timeout=15)

print(f"Status: {resp.status_code}")
print(f"Tamano total: {len(resp.text)} caracteres")
print()

# Guardar el HTML completo para poder inspeccionarlo
with open("understat_pagina_cruda.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
print("HTML completo guardado en understat_pagina_cruda.html")
print()

# Buscar TODAS las apariciones de "JSON.parse(" y mostrar el contexto
# (que variable las contiene), para ver la estructura real sin adivinar
import re
ocurrencias = list(re.finditer(r"(\w+)\s*=\s*JSON\.parse\(", resp.text))
print(f"Variables con JSON.parse encontradas: {len(ocurrencias)}")
for m in ocurrencias:
    print(f"  -> variable: {m.group(1)}")

print()
print("=== Primeros 1000 caracteres del HTML (para ver la estructura general) ===")
print(resp.text[:1000])
