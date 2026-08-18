import pandas as pd

df = pd.read_csv('backtest_consolidado_real.csv')

print("=== Desglose por tipo de selección (todas las ligas juntas) ===\n")

for sel in ['home', 'draw', 'away']:
    sub = df[df['selection'] == sel]
    n = len(sub)
    if n == 0:
        print(f"--- {sel}: sin apuestas EV>0 ---\n")
        continue

    acierto_real = sub['won'].mean() * 100
    acierto_pred = sub['p_model'].mean() * 100
    ev_prom = sub['ev'].mean() * 100
    odds_prom = sub['odds'].mean()

    print(f"--- {sel} ---")
    print(f"  Apuestas EV>0: {n}")
    print(f"  Cuota promedio: {odds_prom:.2f}")
    print(f"  EV promedio: {ev_prom:.2f}%")
    print(f"  Acierto real: {acierto_real:.1f}%  |  predicho por el modelo: {acierto_pred:.1f}%  (brecha: {acierto_pred - acierto_real:+.1f} pts)")
    print()

print("\n=== Lo mismo, pero separado por liga y selección ===\n")
tabla = df.groupby(['league', 'selection']).agg(
    n=('won', 'count'),
    acierto_real=('won', 'mean'),
    acierto_pred=('p_model', 'mean'),
).reset_index()
tabla['acierto_real'] = (tabla['acierto_real'] * 100).round(1)
tabla['acierto_pred'] = (tabla['acierto_pred'] * 100).round(1)
tabla['brecha'] = (tabla['acierto_pred'] - tabla['acierto_real']).round(1)
print(tabla.to_string(index=False))
