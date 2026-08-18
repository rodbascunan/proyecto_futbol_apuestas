-- ============================================================
-- Consultas de ejemplo — validadas contra futbol_apuestas_con_ejemplo.db
-- ============================================================

-- 1. Partidos cargados con resultado
SELECT m.match_id, t1.name AS local, t2.name AS visitante,
       m.ft_home_goals || '-' || m.ft_away_goals AS marcador, m.ft_result
FROM matches m
JOIN teams t1 ON t1.team_id = m.home_team_id
JOIN teams t2 ON t2.team_id = m.away_team_id
ORDER BY m.match_date;

-- 2. Probabilidad implícita (1/cuota) de un partido específico, Pinnacle, apertura
SELECT t1.name AS local, t2.name AS visitante, o.bookmaker, o.selection, o.price,
       ROUND(1.0/o.price*100, 1) AS prob_implicita_pct
FROM odds o
JOIN matches m ON m.match_id = o.match_id
JOIN teams t1 ON t1.team_id = m.home_team_id
JOIN teams t2 ON t2.team_id = m.away_team_id
WHERE o.market_type='1x2' AND o.snapshot='open' AND o.bookmaker='Pinnacle'
  AND m.match_id = 1
ORDER BY o.selection;

-- 3. Overround (margen de la casa) por partido — sirve para identificar
--    qué casas son "duras" (bajo margen) vs "blandas" (alto margen)
SELECT m.match_id, t1.name AS local, t2.name AS visitante,
       ROUND(SUM(1.0/o.price)*100, 2) AS overround_pct
FROM odds o
JOIN matches m ON m.match_id = o.match_id
JOIN teams t1 ON t1.team_id = m.home_team_id
JOIN teams t2 ON t2.team_id = m.away_team_id
WHERE o.market_type='1x2' AND o.snapshot='open' AND o.bookmaker='Pinnacle'
GROUP BY m.match_id;

-- 4. Movimiento de línea (CLV): compara cuota de apertura vs cierre para
--    la misma casa/selección. Un movimiento fuerte indica que el mercado
--    corrigió su precio original — clave para el protocolo de validación.
SELECT t1.name AS local, t2.name AS visitante, o_open.selection,
       o_open.price AS cuota_apertura, o_close.price AS cuota_cierre,
       ROUND(o_close.price - o_open.price, 3) AS movimiento
FROM odds o_open
JOIN odds o_close
  ON o_open.match_id = o_close.match_id
  AND o_open.bookmaker = o_close.bookmaker
  AND o_open.market_type = o_close.market_type
  AND o_open.selection = o_close.selection
  AND o_open.snapshot='open' AND o_close.snapshot='close'
JOIN matches m ON m.match_id = o_open.match_id
JOIN teams t1 ON t1.team_id = m.home_team_id
JOIN teams t2 ON t2.team_id = m.away_team_id
WHERE o_open.market_type='1x2' AND o_open.bookmaker='Pinnacle' AND o_open.selection='home'
ORDER BY movimiento DESC;

-- 5. Comparación entre casas para el mismo partido/mercado/selección.
--    Diferencias grandes entre Pinnacle (referencia "sharp") y otras
--    casas son candidatas a EV positivo.
SELECT o.bookmaker, o.price, ROUND(1.0/o.price*100,1) AS prob_pct
FROM odds o
WHERE o.match_id = 3 AND o.market_type='1x2' AND o.snapshot='open' AND o.selection='home'
ORDER BY o.price;
