import sqlite3
import pandas as pd

DB_PATH = "data/futbol_master.db"

def inspeccionar():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Obtener tablas de la base de datos
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tablas = [t[0] for t in cursor.fetchall()]
    print("=== TABLAS ENCONTRADAS EN LA BASE DE DATOS ===")
    print(tablas)
    print("=" * 50)
    
    # 2. Inspeccionar columnas de matriz_features
    if 'matriz_features' in tablas:
        df_mf = pd.read_sql_query("SELECT * FROM matriz_features LIMIT 3", conn)
        print("\n--- Columnas de 'matriz_features' ---")
        print(list(df_mf.columns))
    
    # 3. Inspeccionar columnas de partidos
    if 'partidos' in tablas:
        df_p = pd.read_sql_query("SELECT * FROM partidos LIMIT 3", conn)
        print("\n--- Columnas de 'partidos' ---")
        print(list(df_p.columns))
        print("\nMuestra de datos de 'partidos':")
        print(df_p.head())

    conn.close()

if __name__ == "__main__":
    inspeccionar()
    