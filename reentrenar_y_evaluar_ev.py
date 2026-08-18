import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

def reentrenar_y_evaluar():
    archivo_entrada = "dataset_xg_con_cuotas.csv"
    archivo_salida = "predicciones_cuotas_reales.csv"

    print("=" * 70)
    print("[1/4] Cargando dataset con cuotas reales...")
    print("=" * 70)

    try:
        df = pd.read_csv(archivo_entrada)
    except FileNotFoundError:
        print(f"[ERROR] No se encontró el archivo '{archivo_entrada}'.")
        return

    # 1. Identificar columnas de cuotas disponibles en el CSV
    col_h = next((c for c in ["cuota_home", "cuota_home_real", "PSH", "B365H", "AvgH"] if c in df.columns), None)
    col_d = next((c for c in ["cuota_draw", "cuota_draw_real", "PSD", "B365D", "AvgD"] if c in df.columns), None)
    col_a = next((c for c in ["cuota_away", "cuota_away_real", "PSA", "B365A", "AvgA"] if c in df.columns), None)

    if not all([col_h, col_d, col_a]):
        print("[ERROR] No se encontraron columnas de cuotas válidas en el archivo.")
        print(f"Columnas presentes: {list(df.columns)}")
        return

    print(f"Columnas de cuota detectadas: Home='{col_h}', Draw='{col_d}', Away='{col_a}'")

    # Mapear y forzar conversión numérica estricta (SIN FALLBACKS ESTÁTICOS)
    df["cuota_home"] = pd.to_numeric(df[col_h], errors="coerce")
    df["cuota_draw"] = pd.to_numeric(df[col_d], errors="coerce")
    df["cuota_away"] = pd.to_numeric(df[col_a], errors="coerce")

    # Limpiar datos: eliminar filas sin cuotas válidas
    filas_iniciales = len(df)
    df = df.dropna(subset=["cuota_home", "cuota_draw", "cuota_away"]).copy()
    df = df[(df["cuota_home"] > 1.0) & (df["cuota_draw"] > 1.0) & (df["cuota_away"] > 1.0)]

    print(f"Registros con cuotas reales válidas: {len(df)} (Se descartaron {filas_iniciales - len(df)} filas nulas/inválidas)")

    if len(df) < 30:
        print("[ERROR] Muestra insuficiente para entrenar y evaluar el modelo.")
        return

    # 2. Definición de variables predictoras (Features) y Variable Objetivo (Target)
    col_target = next((c for c in ["target_1x2", "resultado_1x2", "target", "resultado"] if c in df.columns), None)
    
    if not col_target:
        print("[ERROR] No se encontró la columna target del resultado en el dataset.")
        return

    # Seleccionar solo columnas numéricas para las features (excluyendo targets y cuotas)
    columnas_excluidas = [
        col_target, "cuota_home", "cuota_draw", "cuota_away", "fecha", "date",
        "equipo_home", "equipo_away", "home_team", "away_team", col_h, col_d, col_a
    ]
    
    features = [c for c in df.columns if c not in columnas_excluidas and pd.api.types.is_numeric_dtype(df[c])]

    print(f"\n[2/4] Entrenando modelo con {len(features)} variables predictoras...")
    
    X = df[features].fillna(0)
    y = df[col_target]

    # Dividir Muestra de Entrenamiento (Train) y Muestra de Prueba Out-of-Sample (Test)
    X_train, X_test, y_train, y_test, df_train, df_test = train_test_split(
        X, y, df, test_size=0.25, random_state=42, shuffle=True
    )

    # Entrenar Random Forest
    model = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
    model.fit(X_train, y_train)

    print(f"\n[3/4] Generando probabilidades para la muestra de prueba ({len(X_test)} partidos)...")
    
    # Predecir probabilidades
    probs = model.predict_proba(X_test)

    # Asegurar mapeo correcto de clases (1: Local, 0: Empate, 2: Visita o según codificación)
    clases = list(model.classes_)
    
    # Asignación dinámica según el formato de las clases
    idx_home = clases.index(1) if 1 in clases else 0
    idx_draw = clases.index(0) if 0 in clases else (clases.index('D') if 'D' in clases else 1)
    idx_away = clases.index(2) if 2 in clases else (clases.index('A') if 'A' in clases else 2)

    df_test = df_test.copy()
    df_test["prob_local"] = probs[:, idx_home]
    df_test["prob_empate"] = probs[:, idx_draw]
    df_test["prob_visita"] = probs[:, idx_away]

    # 3. Guardar resultados preservando las cuotas dinámicas reales
    print(f"\n[4/4] Guardando muestra de prueba evaluada en '{archivo_salida}'...")
    df_test.to_csv(archivo_salida, index=False)

    print("\n" + "=" * 70)
    print(f"[ÉXITO] Entrenado con {len(X_train)} filas. Muestra de prueba en '{archivo_salida}' con {len(X_test)} registros.")
    print("=" * 70)

if __name__ == "__main__":
    reentrenar_y_evaluar()

    S