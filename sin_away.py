import pandas as pd

df = pd.read_csv('backtest_consolidado_real.csv')

def banca_real(sub, label):
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
    print(f"--- {label} ---")
    print(f"  Apuestas: {len(sub)}")
    print(f"  Acierto real: {sub['won'].mean()*100:.1f}%  |  predicho: {sub['p_model'].mean()*100:.1f}%")
    print(f"  Banca final: {bankroll:.2f}  ({retorno:+.1f}%)")
    print(f"  Drawdown maximo: {max_dd*100:.1f}%")
    print()

print("=== Comparacion: con vs. sin apuestas 'away' ===\n")

banca_real(df, "TODAS las apuestas (home+draw+away)")
banca_real(df[df['selection'] != 'away'], "SOLO home+draw (excluyendo away)")
banca_real(df[df['selection'] == 'away'], "SOLO away (para ver cuanto perdian por si solas)")

print("=== Desglose por liga, solo home+draw ===\n")
sin_away = df[df['selection'] != 'away']
for liga in sorted(sin_away['league'].unique()):
    banca_real(sin_away[sin_away['league'] == liga], f"Liga: {liga}")
    