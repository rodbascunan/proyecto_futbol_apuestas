import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, log_loss
from xgboost import XGBClassifier


def preparar_y_entrenar():
    print("[1/4] Cargando dataset de variables (features)...")
    df = pd.read_csv("dataset_xg_features.csv")

    # Convertir fecha
    df["fecha"] = pd.to_datetime(df["fecha"])

    print("[2/4] Definiendo Targets (Variables a predecir)...")

    # Target 1: Resultado 1X2 (0: Empate, 1: Gana Local, 2: Gana Visitante)
    conditions_1x2 = [
        df["goles_favor_home"] > df["goles_favor_away"],
        df["goles_favor_home"] < df["goles_favor_away"],
    ]
    choices_1x2 = [1, 2]  # 1: Local, 2: Visitante
    df["target_1x2"] = np.select(
        conditions_1x2, choices_1x2, default=0
    )  # 0: Empate

    # Target 2: Over / Under 2.5 goles (1 si la suma de goles > 2.5, 0 en otro caso)
    df["total_goles"] = df["goles_favor_home"] + df["goles_favor_away"]
    df["target_over25"] = (df["total_goles"] > 2.5).astype(int)

    # Seleccionar características (Features) numéricas pre-partido
    feature_cols = [
        "xg_favor_roll_5_home",
        "xg_contra_roll_5_home",
        "xg_diff_roll_5_home",
        "xg_favor_roll_10_home",
        "xg_contra_roll_10_home",
        "xg_diff_roll_10_home",
        "conversion_ratio_10_home",
        "xg_favor_roll_5_away",
        "xg_contra_roll_5_away",
        "xg_diff_roll_5_away",
        "xg_favor_roll_10_away",
        "xg_contra_roll_10_away",
        "xg_diff_roll_10_away",
        "conversion_ratio_10_away",
    ]

    # Eliminar filas con valores nulos (primeros partidos donde aún no se acumulaban 3+ partidos previos)
    df_model = df.dropna(subset=feature_cols).copy()

    # Ordenar por fecha antes de separar
    df_model = df_model.sort_values("fecha").reset_index(drop=True)

    print(
        f"Partidos válidos con métricas rodantes acumuladas: {len(df_model)}"
    )

    # [3/4] División Cronológica: Train (80%) vs Test (20%)
    split_idx = int(len(df_model) * 0.8)

    train_df = df_model.iloc[:split_idx]
    test_df = df_model.iloc[split_idx:]

    X_train = train_df[feature_cols]
    y_train_1x2 = train_df["target_1x2"]
    y_train_over = train_df["target_over25"]

    X_test = test_df[feature_cols]
    y_test_1x2 = test_df["target_1x2"]
    y_test_over = test_df["target_over25"]

    print(
        f"Conjunto de Entrenamiento: {len(X_train)} partidos | Conjunto de Prueba: {len(X_test)} partidos"
    )

    print("\n[4/4] Entrenando Modelos Predictivos...\n")

    # --- MODELO 1: Predicción de Resultado 1X2 (XGBoost) ---
    xgb_1x2 = XGBClassifier(
        n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42
    )
    xgb_1x2.fit(X_train, y_train_1x2)

    preds_1x2 = xgb_1x2.predict(X_test)
    acc_1x2 = accuracy_score(y_test_1x2, preds_1x2)

    print("=" * 60)
    print(f"MODELO 1X2 (XGBoost) - Exactitud (Accuracy): {acc_1x2:.2%}")
    print("=" * 60)
    print(
        classification_report(
            y_test_1x2,
            preds_1x2,
            target_names=["Empate (0)", "Gana Local (1)", "Gana Visita (2)"],
        )
    )

    # --- MODELO 2: Predicción Over / Under 2.5 Goles (Random Forest) ---
    rf_over = RandomForestClassifier(
        n_estimators=150, max_depth=6, random_state=42
    )
    rf_over.fit(X_train, y_train_over)

    preds_over = rf_over.predict(X_test)
    acc_over = accuracy_score(y_test_over, preds_over)

    print("=" * 60)
    print(
        f"MODELO OVER / UNDER 2.5 GOLES (Random Forest) - Accuracy: {acc_over:.2%}"
    )
    print("=" * 60)
    print(
        classification_report(
            y_test_over, preds_over, target_names=["Under 2.5", "Over 2.5"]
        )
    )

    # Importancia de las Variables más relevantes
    importances = pd.Series(
        xgb_1x2.feature_importances_, index=feature_cols
    ).sort_values(ascending=False)
    print("=" * 60)
    print("TOP 5 VARIABLES MÁS IMPORTANTES EN EL MODELO 1X2:")
    print("=" * 60)
    print(importances.head(5).to_string())


if __name__ == "__main__":
    preparar_y_entrenar()
    