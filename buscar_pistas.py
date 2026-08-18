with open("understat_pagina_cruda.html", encoding="utf-8") as f:
    html = f.read()

import re

print("=== Todos los <script src=...> (JS externos que carga la pagina) ===")
for m in re.finditer(r'<script[^>]+src="([^"]+)"', html):
    print(f"  {m.group(1)}")

print()
print("=== Menciones de 'api' en el HTML ===")
for m in re.finditer(r'.{40}api.{40}', html, re.IGNORECASE):
    print(f"  ...{m.group(0)}...")

print()
print("=== Buscando cualquier variable con JSON.parse o fetch( ===")
for patron in [r'JSON\.parse', r'fetch\(', r'axios\.', r'XMLHttpRequest']:
    n = len(re.findall(patron, html))
    print(f"  '{patron}': {n} ocurrencias")
    