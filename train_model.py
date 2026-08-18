import sqlite3
import pandas as pd
import numpy as np
import pickle
from xgboost import XGBClassifier
from sklearn.metrics import log_loss, accuracy_score, classification_report

DB_PATH = "data/futbol_master.db"

def cargar_datos_entrenamiento():
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT 
            mf.*,
            p.odd_1, p.odd_x, p.odd_2
        FROM matriz_features mf
        LEFT JOIN partidos p ON mf.id_partido = p.id_partido
        ORDER BY mf.fecha ASC
    """
    try:
        df = pd.read_sql_query(query, conn)
    except Exception:
        df = pd.read_sql_query("SELECT * FROM matriz_features ORDER BY fecha ASC", conn)
    
    conn.close()
    return df

def preparar_datos(df):
    mapeo_target = {'1': 0, 'X': 1, '2': 2, 'H': 0, 'D': 1, 'A': 2}
    df = df[df['resultado'].isin(mapeo_target.keys())].copy()
    df['target'] = df['resultado'].map(mapeo_target)

    posibles_features = [
        'home_roll_gf', 'home_roll_gc', 'home_roll_xg_f', 'home_roll_xg_c',
        'away_roll_gf', 'away_roll_gc', 'away_roll_xg_f', 'away_roll_xg_c',
        'diff_roll_xg', 'diff_roll_gf'
    ]

    feature_cols = [c for c in posibles_features if c in df.columns and df[c].notnull().sum() > 0]

    X = df[feature_cols].fillna(0)
    y = df['target'].astype(int)

    return df, X, y, feature_cols

def entrenar_modelo():
    df = cargar_datos_entrenamiento()
    if len(df) == 0:
        print("[ERROR] No se encontraron registros.")
        return

    df, X, y, feature_cols = preparar_datos(df)

    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # XGBoost directo para mantener variabilidad real en probabilidades
    model = XGBClassifier(
        n_estimators=100,
        learning_rate=0.03,
        max_depth=3,
        subsample=0.8,
        colsample_bytree=0.8,
        objective='multi:softprob',
        num_class=3,
        random_state=42
    )

    model.fit(X_train, y_train)

    y_pred_prob = model.predict_proba(X_test)
    y_pred = model.predict(X_test)

    print("\n--- Resultados del Modelo ---")
    print(f"Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%")
    print(f"Log Loss: {log_loss(y_test, y_pred_prob):.4f}")

    with open("modelo_xgboost.pkl", "wb") as f:
        pickle.dump({'model': model, 'features': feature_cols}, f)
        
    print("[OK] Modelo exportado correctamente en 'modelo_xgboost.pkl'.")

if __name__ == "__main__":
    entrenar_modelo()
    