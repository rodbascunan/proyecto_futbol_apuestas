"""
Liquidacion de apuestas de handicap asiatico, incluyendo lineas de cuarto
(ej. -0.25, -0.75) que en realidad dividen el stake en dos mitades con
liquidacion independiente cada una.
"""

def liquidar_ah(line, margin, lado, odds, stake=10.0):
    """
    line: la linea de hándicap tal como aparece en el CSV (AHh), aplicada al LOCAL
    margin: hg - ag (goles local menos goles visita)
    lado: 'home' o 'away' -- a quien se aposto
    odds: cuota de esa apuesta
    """
    if lado == "away":
        line_eff = -line
        margin_eff = -margin
    else:
        line_eff = line
        margin_eff = margin

    doubled = round(line_eff * 4)
    es_cuarto = doubled % 2 != 0

    if es_cuarto:
        subs = [(doubled - 1) / 4, (doubled + 1) / 4]
    else:
        subs = [line_eff]

    resultados = []
    for L in subs:
        val = margin_eff + L
        if val > 1e-9:
            resultados.append(odds - 1)   # gana esa mitad
        elif val < -1e-9:
            resultados.append(-1)          # pierde esa mitad
        else:
            resultados.append(0)           # push (devolucion) en esa mitad

    return stake * (sum(resultados) / len(resultados))


if __name__ == "__main__":
    # Casos de prueba con resultados conocidos de antemano
    casos = [
        # (line, margin, lado, odds, resultado_esperado_aprox, descripcion)
        (-1.0, 2, "home", 2.0, 10.0, "Local -1.0, gana por 2 -> gana completo"),
        (-1.0, 1, "home", 2.0, 0.0, "Local -1.0, gana por 1 -> push (empate en la linea)"),
        (-1.0, 0, "home", 2.0, -10.0, "Local -1.0, empatan -> pierde completo"),
        (-0.5, 1, "home", 2.0, 10.0, "Local -0.5, gana por 1 -> gana completo (sin push posible)"),
        (-0.5, 0, "home", 2.0, -10.0, "Local -0.5, empatan -> pierde completo"),
        (-0.75, 1, "home", 2.0, 5.0, "Local -0.75, gana por 1 -> media gana / media push -> +5"),
        (-0.75, 0, "home", 2.0, -10.0, "Local -0.75, empatan -> ambas mitades pierden -> -10"),
        (-0.25, 0, "home", 2.0, -5.0, "Local -0.25, empatan -> mitad push, mitad pierde -> -5"),
        (-0.25, 1, "home", 2.0, 10.0, "Local -0.25, gana por 1 -> gana completo"),
        (0.0, 0, "home", 2.0, 0.0, "Local 0 (linea pareja), empatan -> push completo"),
        (1.5, -2, "away", 1.8, 8.0, "Visita +1.5 (line=1.5 en local), pierde por 2 -> visita cubre, gana completo"),
    ]

    print("Verificacion de la funcion de liquidacion AH:\n")
    todos_ok = True
    for line, margin, lado, odds, esperado, desc in casos:
        resultado = liquidar_ah(line, margin, lado, odds, stake=10.0)
        ok = abs(resultado - esperado) < 0.01
        todos_ok = todos_ok and ok
        estado = "OK" if ok else "FALLO"
        print(f"  [{estado}] {desc}")
        print(f"         Calculado: {resultado:+.2f}  |  Esperado: {esperado:+.2f}")

    print()
    print("TODOS LOS CASOS PASARON" if todos_ok else "HAY CASOS QUE FALLAN -- REVISAR")
