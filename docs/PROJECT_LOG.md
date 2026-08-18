# Bitácora de Experimentos y Rendimiento

## Registro de Versiones del Modelo

### [v1.0] - Modelo Base XGBoost (Probabilidades Directas)
* **Fecha**: 2026-08-17
* **Features**:
  * `home_roll_gf`, `home_roll_gc`, `home_roll_xg_f`, `home_roll_xg_c`
  * `away_roll_gf`, `away_roll_gc`, `away_roll_xg_f`, `away_roll_xg_c`
  * `diff_roll_xg`, `diff_roll_gf`
* **Métricas de Entrenamiento**:
  * Accuracy Test: 47.23%
  * Log Loss: 1.0293
* **Métricas de Backtesting**:
  * ROI / Yield: [Pendiente de simulación]
  * Win Rate: [Pendiente de simulación]
  * Max Drawdown: [Pendiente de simulación]
* **Notas**: Se removió la calibración sigmoide (`CalibratedClassifierCV`) para evitar el aplanamiento de probabilidades en cuotas descalibradas.
