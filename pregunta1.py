from explorador import cargar_partidos_con_cuotas, backtest_regla, TRAIN_SEASONS

df = cargar_partidos_con_cuotas('futbol_apuestas.db', league_codes=['SP1'], season_labels=TRAIN_SEASONS)

print(f"Total de partidos: {len(df)}")
print()
print("=== Distribucion real de resultados ===")
print(df['actual'].value_counts(normalize=True).mul(100).round(1))
print()

# Ademas, vemos si "apostar siempre al local" habria sido rentable
# a la cuota de mercado (Market Avg)
backtest_regla(df, lambda r: True, 'home', 'Apostar SIEMPRE al local (La Liga)')
