-- Activar soporte de Claves Foráneas en SQLite
PRAGMA foreign_keys = ON;

-- 1. TABLA: LIGAS
CREATE TABLE IF NOT EXISTS ligas (
    id_liga TEXT PRIMARY KEY,             -- ej: 'ENG1' (Premier), 'ESP1' (LaLiga)
    nombre TEXT NOT NULL,                 -- ej: 'Premier League'
    pais TEXT NOT NULL                    -- ej: 'Inglaterra'
);

-- 2. TABLA: EQUIPOS
CREATE TABLE IF NOT EXISTS equipos (
    id_equipo INTEGER PRIMARY KEY AUTOINCREMENT,
    id_liga TEXT NOT NULL,
    nombre_oficial TEXT NOT NULL,         -- Nombre maestro canonizado (ej: 'Arsenal')
    FOREIGN KEY (id_liga) REFERENCES ligas(id_liga) ON DELETE CASCADE
);

-- 3. TABLA: ALIAS_EQUIPOS (Resuelve cruces entre Understat, Football-Data, FBref)
CREATE TABLE IF NOT EXISTS alias_equipos (
    id_alias INTEGER PRIMARY KEY AUTOINCREMENT,
    id_equipo INTEGER NOT NULL,
    fuente TEXT NOT NULL,                 -- 'understat', 'football_data', 'fbref'
    nombre_fuente TEXT NOT NULL,          -- ej: 'Arsenal FC', 'Arsenal London'
    FOREIGN KEY (id_equipo) REFERENCES equipos(id_equipo) ON DELETE CASCADE,
    UNIQUE(fuente, nombre_fuente)
);

-- 4. TABLA: PARTIDOS (Metadatos y Resultados para 1X2 y Over/Under)
CREATE TABLE IF NOT EXISTS partidos (
    id_partido TEXT PRIMARY KEY,          -- Hash único o formato 'ENG1_20252026_ARS_CHE'
    id_liga TEXT NOT NULL,
    temporada TEXT NOT NULL,              -- ej: '2025-2026'
    fecha_iso TEXT NOT NULL,              -- Formato ISO: 'YYYY-MM-DD HH:MM:SS'
    id_equipo_home INTEGER NOT NULL,
    id_equipo_away INTEGER NOT NULL,
    goles_home INTEGER,
    goles_away INTEGER,
    resultado_1x2 TEXT CHECK(resultado_1x2 IN ('1', 'X', '2')),
    total_goles INTEGER GENERATED ALWAYS AS (goles_home + goles_away) VIRTUAL, -- Campo virtual para Over/Under
    FOREIGN KEY (id_liga) REFERENCES ligas(id_liga),
    FOREIGN KEY (id_equipo_home) REFERENCES equipos(id_equipo),
    FOREIGN KEY (id_equipo_away) REFERENCES equipos(id_equipo)
);

-- 5. TABLA: METRICAS_XG (Soporte avanzado para modelos de probabilidad y Poisson)
CREATE TABLE IF NOT EXISTS metricas_xg (
    id_metricas INTEGER PRIMARY KEY AUTOINCREMENT,
    id_partido TEXT NOT NULL UNIQUE,
    -- Métricas generales
    xg_home REAL NOT NULL,
    xg_away REAL NOT NULL,
    xga_home REAL NOT NULL,               -- Expected Goals Against (Concedidos)
    xga_away REAL NOT NULL,
    shots_home INTEGER,
    shots_away INTEGER,
    shots_target_home INTEGER,
    shots_target_away INTEGER,
    -- Métricas desglosadas (Útiles para modelos Over/Under finos)
    xg_open_play_home REAL,
    xg_open_play_away REAL,
    xg_set_piece_home REAL,
    xg_set_piece_away REAL,
    FOREIGN KEY (id_partido) REFERENCES partidos(id_partido) ON DELETE CASCADE
);

-- 6. TABLA: CUOTAS (1X2 + Mercado Over/Under)
CREATE TABLE IF NOT EXISTS cuotas (
    id_cuota INTEGER PRIMARY KEY AUTOINCREMENT,
    id_partido TEXT NOT NULL,
    casa_apuestas TEXT NOT NULL,          -- 'Pinnacle', 'Bet365', 'Avg'
    -- Mercado 1X2
    cuota_1 REAL,
    cuota_x REAL,
    cuota_2 REAL,
    -- Mercado Over/Under 2.5
    cuota_over_25 REAL,
    cuota_under_25 REAL,
    -- Mercado Over/Under 1.5 y 3.5 (Opcionales para líneas adicionales)
    cuota_over_15 REAL,
    cuota_under_15 REAL,
    FOREIGN KEY (id_partido) REFERENCES partidos(id_partido) ON DELETE CASCADE,
    UNIQUE(id_partido, casa_apuestas)
);

-- INDICES PARA CONSULTAS DE ALTA VELOCIDAD
CREATE INDEX IF NOT EXISTS idx_partidos_fecha ON partidos(fecha_iso);
CREATE INDEX IF NOT EXISTS idx_partidos_liga ON partidos(id_liga);
CREATE INDEX IF NOT EXISTS idx_partidos_equipos ON partidos(id_equipo_home, id_equipo_away);
