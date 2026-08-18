import pandas as pd

df = pd.read_csv('backtest_consolidado_real.csv')

bankroll = 1000.0
peak = bankroll
max_dd = 0.0

for _, row in df.iterrows():
    stake = bankroll * row['kelly_stake_frac']
    if row['won']:
        bankroll += stake * (row['odds'] - 1)
    else:
        bankroll -= stake
    peak = max(peak, bankroll)
    dd = (peak - bankroll) / peak if peak > 0 else 0
    max_dd = max(max_dd, dd)

print(f"Banca final REAL (trayectoria unica, resultados verdaderos): {bankroll:.2f}")
print(f"Retorno: {(bankroll/1000-1)*100:+.1f}%")
print(f"Drawdown maximo REAL: {max_dd*100:.1f}%")