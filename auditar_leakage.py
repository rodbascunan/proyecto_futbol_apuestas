import pandas as pd
import numpy as np

def auditar_dataset():
    df = pd.read_csv("dataset_xg_con_cuotas.csv")
    
    col_gh = next((c for c in ["goles_favor_home", "home_goals", "goles_home"] if c in df.columns), "goles_favor_home")
    col_ga = next((c for c in ["goles_favor_away", "away_goals", "goles_away"] if c in df.columns), "goles_favor_away")
    
    df["target_1x2"] = np.where(df[col_gh] > df[col_ga], 1, np.where(df[col_gh] < df[col_ga], 2, 0))
    
    print("=== AUDITORÍA DE CONTAMINACIÓN DE DATOS (DATA LEAKAGE) ===")
    
    # Revisar correlación entre features y el resultado actual
    features_check = ["xg_favor_roll_5_home", "xg_diff_roll_5_home", "conversion_ratio_10_home"]
    cols_existentes = [c for c in features_check if c in df.columns]
    
    correlaciones = df[cols_existentes + [col_gh, col_ga, "target_1x2"]].corr()
    print("\nMatriz de Correlación con el partido actual:")
    print(correlaciones["target_1x2"])
    
if __name__ == "__main__":
    auditar_dataset()
    