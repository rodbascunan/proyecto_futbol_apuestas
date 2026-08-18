import sqlite3
import os

def inicializar_db(db_path="data/futbol_master.db", schema_path="schema.sql"):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
        
    cursor.executescript(schema_sql)
    conn.commit()
    
    # Insertar ligas base de la Fase 1
    cursor.execute("INSERT OR IGNORE INTO ligas VALUES ('ENG1', 'Premier League', 'Inglaterra')")
    cursor.execute("INSERT OR IGNORE INTO ligas VALUES ('ESP1', 'LaLiga', 'España')")
    conn.commit()
    
    print(f"[OK] Base de datos SQLite creada e inicializada en: '{db_path}'")
    conn.close()

if __name__ == "__main__":
    # Guardar schema.sql primero y luego llamar la función
    inicializar_db()
    