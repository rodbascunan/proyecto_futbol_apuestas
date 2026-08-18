import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import TimeSeriesSplit

def entrenar_modelo_avanzado():
    print("[1/3] Cargando dataset de variables...")
    df = pd.read_csv("dataset_xg_features.csv")
    df['fecha'] = pd.to_datetime(df['fecha'])
    df = df.sort_values('fecha').reset_index(drop=True)

    # 1. Crear Targets
    df['target_1x2'] = np.where(
        df['goles_favor_home'] > df['goles_favor_away'], 1,
        np.where(df['goles_favor_home'] < df['goles_favor_away'], 2, 0)
    )
    df['total_goles'] = df['goles_favor_home'] + df['goles_favor_away']
    df['target_over25'] = (df['total_goles'] > 2.5).astype(int)

    # 2. Variable de Tendencia (Comparación racha corta 5 vs racha larga 10)
    df['tendencia_xg_home'] = df['xg_diff_roll_5_home'] - df['xg_diff_roll_10_home']
    df['tendencia_xg_away'] = df['xg_diff_roll_5_away'] - df['xg_diff_roll_10_away']

    # 3. Diferencia directa entre Local y Visitante
    df['diff_xg_5_h_vs_a'] = df['xg_favor_roll_5_home'] - df['xg_favor_roll_5_away']
    df['diff_xg_10_h_vs_a'] = df['xg_favor_roll_10_home'] - df['xg_favor_roll_10_away']

    features = [
        'xg_favor_roll_5_home', 'xg_contra_roll_5_home', 'xg_diff_roll_5_home',
        'xg_favor_roll_10_home', 'xg_contra_roll_10_home', 'xg_diff_roll_10_home',
        'conversion_ratio_10_home', 'tendencia_xg_home',
        'xg_favor_roll_5_away', 'xg_contra_roll_5_away', 'xg_diff_roll_5_away',
        'xg_favor_roll_10_away', 'xg_contra_roll_10_away', 'xg_diff_roll_10_away',
        'conversion_ratio_10_away', 'tendencia_xg_away',
        'diff_xg_5_h_vs_a', 'diff_xg_10_h_vs_a'
    ]

    df_model = df.dropna(subset=features).copy()
    
    # Separación Train/Test temporal (80/20)
    split_idx = int(len(df_model) * 0.8)
    train = df_model.iloc[:split_idx]
    test = df_model.iloc[split_idx:].copy()

    X_train, y_train_1x2, y_train_over = train[features], train['target_1x2'], train['target_over25']
    X_test, y_test_1x2, y_test_over = test[features], test['target_1x2'], test['target_over25']

    print(f"[2/3] Entrenando modelo hiperparametrizado con {len(X_train)} partidos...")

    # XGBoost calibrado con reg_alpha/reg_lambda para evitar sobreajuste
    model_1x2 = XGBClassifier(
        n_estimators=150,
        learning_rate=0.03,
        max_depth=3,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=1.0,
        reg_lambda=1.0,
        random_state=42
    )
    model_1x2.fit(X_train, y_train_1x2)

    # Predicción de probabilidades para Value Betting
    probs_1x2 = model_1x2.predict_proba(X_test)
    preds_1x2 = model_1x2.predict(X_test)

    print("\n" + "="*60)
    print(f"EVALUACIÓN MODELO 1X2 - Accuracy: {accuracy_score(y_test_1x2, preds_1x2):.2%}")
    print("="*60)
    print(classification_report(y_test_1x2, preds_1x2, target_names=['Empate', 'Local', 'Visitante']))

    # Adjuntar probabilidades al dataset de prueba
    test['prob_empate'] = probs_1x2[:, 0]
    test['prob_local'] = probs_1x2[:, 1]
    test['prob_visita'] = probs_1x2[:, 2]

    # Guardar predicciones probables para simulación de apuestas
    test.to_csv("predicciones_con_probabilidades.csv", index=False)
    print("[3/3] Archivo 'predicciones_con_probabilidades.csv' generado con éxito.")

if __name__ == "__main__":
    entrenar_modelo_avanzado()
    