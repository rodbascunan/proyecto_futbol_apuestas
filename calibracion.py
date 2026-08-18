import pandas as pd
import numpy as np

df = pd.read_csv('backtest_consolidado_real.csv')

print("=== Calibracion por deciles de probabilidad del modelo (todas las ligas) ===\n")

# Deciles: cada grupo tiene aprox. el mismo numero de apuestas
df['decil'] = pd.qcut(df['p_model'], q=10, duplicates='drop')

resumen = df.groupby('decil', observed=True).agg(
    n=('won', 'count'),
    prob_predicha=('p_model', 'mean'),
    acierto_real=('won', 'mean'),
).reset_index()

resumen['prob_predicha'] = (resumen['prob_predicha'] * 100).round(1)
resumen['acierto_real'] = (resumen['acierto_real'] * 100).round(1)
resumen['brecha'] = (resumen['prob_predicha'] - resumen['acierto_real']).round(1)
resumen['factor_correccion'] = (resumen['acierto_real'] / resumen['prob_predicha']).round(3)

print(resumen.to_string(index=False))

print()
print("=== Resumen general ===")
print(f"Probabilidad promedio predicha: {df['p_model'].mean()*100:.1f}%")
print(f"Acierto real promedio: {df['won'].mean()*100:.1f}%")
print(f"Factor de correccion global (acierto_real / prob_predicha): {df['won'].mean() / df['p_model'].mean():.3f}")

# Guardamos para poder graficar despues si hace falta
resumen.to_csv('calibracion_deciles.csv', index=False)
