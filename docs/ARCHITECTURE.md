# Arquitectura del Sistema de Apuestas Cuantitativas

## Pipeline de Datos y Scripts
## Definiciones de Métricas Financieras

* **Valor Esperado (EV)**:
  $$EV = (P_{\text{modelo}} \times \text{Cuota}) - 1$$
* **Criterio de Kelly Fraccionado**:
  $$\text{Kelly} = \frac{(b \times p) - q}{b}$$
  * *Donde:* $b = \text{Cuota} - 1$, $p = P_{\text{modelo}}$, $q = 1 - p$.
  * Se aplica una fracción conservadora del **10% de Kelly** con tope del **3% del bankroll** por apuesta.
  