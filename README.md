# ⚽ Sistema de Predicción y Backtesting de Apuestas de Fútbol

Un sistema integral basado en **Machine Learning (XGBoost)** y análisis estadístico avanzado para la predicción de resultados de partidos de fútbol y la identificación de apuestas con **Valor Esperado Positivo (EV+)**.

---

## 📌 Tabla de Contenidos
- [Descripción General](#-descripción-general)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Arquitectura de Datos](#-arquitectura-de-datos)
- [Estrategia de Apuestas y Gestión de Capital](#-estrategia-de-apuestas-y-gestión-de-capital)
- [Resultados del Backtesting](#-resultados-del-backtesting)
- [Instalación y Configuración](#-instalación-y-configuración)
- [Guía de Uso](#-guía-de-uso)

---

## 🏈 Descripción General

El proyecto recolecta, procesa y analiza datos históricos de ligas de fútbol (incluyendo métricas de goles, datos xG y cuotas del mercado 1X2). Utiliza un algoritmo de clasificación impulsado por **XGBoost** para calcular las probabilidades reales de cada resultado (`1`, `X`, `2`). 

Al comparar las probabilidades del modelo con las cuotas del mercado, el sistema identifica desajustes (*Expected Value* positivo) y aplica un criterio de **Kelly Fraccionado** para determinar el valor exacto del stake y proteger el bankroll.

---

## 📁 Estructura del Proyecto

```text
proyecto_futbol_apuestas/
├── data/
│   └── futbol_master.db         # Base de datos SQLite unificada
├── models/
│   └── modelo_xgboost.pkl       # Modelo entrenado y lista de features
├── check_db.py                  # Inspector de estructura y esquema de la BD
├── backtest_simulation.py       # Simulación histórica y evaluación financiera
├── predict_upcoming.py          # Generador de cartelera de apuestas en vivo
├── requirements.txt             # Dependencias del proyecto
└── README.md                    # Documentación del proyecto