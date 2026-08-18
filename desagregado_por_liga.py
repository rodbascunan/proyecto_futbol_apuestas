import pandas as pd

df = pd.read_csv('backtest_consolidado_real.csv')

print("=== Resumen por liga ===\n")

for liga in sorted(df['league'].unique()):
    sub = df[df['league'] == liga]

    n = len(sub)
    ev_prom = sub['ev'].mean() * 100
    acierto_real = sub['won'].mean() * 100
    acierto_pred = sub['p_model'].mean() * 100

    # Trayectoria real de banca, SOLO para esta liga (banca separada de 1000)
    bankroll = 1000.0
    peak = bankroll
    max_dd = 0.0
    for _, row in sub.iterrows():
        stake = bankroll * row['kelly_stake_frac']
        if row['won']:
            bankroll += stake * (row['odds'] - 1)
        else:
            bankroll -= stake
        peak = max(peak, bankroll)
        dd = (peak - bankroll) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)

    retorno = (bankroll / 1000 - 1) * 100

    print(f"--- {liga} ---")
    print(f"  Apuestas EV>0: {n}")
    print(f"  EV promedio: {ev_prom:.2f}%")
    print(f"  Acierto real: {acierto_real:.1f}%  |  predicho por el modelo: {acierto_pred:.1f}%")
    print(f"  Banca final (partiendo de 1000, trayectoria real): {bankroll:.2f}  ({retorno:+.1f}%)")
    print(f"  Drawdown maximo real: {max_dd*100:.1f}%")
    print()