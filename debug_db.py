import sqlite3

DB_PATH = "data/futbol_master.db"

def inspeccionar_base_datos():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("=" * 60)
        print("1. LIGAS REGISTRADAS EN LA TABLA 'equipos'")
        print("=" * 60)
        cursor.execute("SELECT DISTINCT id_liga FROM equipos")
        ligas = cursor.fetchall()
        if ligas:
            for l in ligas:
                print(f"- id_liga: '{l[0]}'")
        else:
            print("[ALERTA] La tabla 'equipos' está vacía o no tiene ligas.")

        print("\n" + "=" * 60)
        print("2. MUESTRA DE EQUIPOS EN LA TABLA 'equipos' (Máximo 10)")
        print("=" * 60)
        cursor.execute("SELECT id_equipo, id_liga, nombre_oficial FROM equipos LIMIT 10")
        equipos = cursor.fetchall()
        if equipos:
            for eq in equipos:
                print(f"ID: {eq[0]} | Liga: '{eq[1]}' | Nombre: '{eq[2]}'")
        else:
            print("[ALERTA] No se encontraron registros en la tabla 'equipos'.")

        print("\n" + "=" * 60)
        print("3. ALIAS REGISTRADOS EN LA TABLA 'alias_equipos' (Máximo 10)")
        print("=" * 60)
        try:
            cursor.execute("SELECT id_equipo, fuente, nombre_fuente FROM alias_equipos LIMIT 10")
            alias = cursor.fetchall()
            if alias:
                for a in alias:
                    print(f"ID Equipo: {a[0]} | Fuente: '{a[1]}' | Nombre Fuente: '{a[2]}'")
            else:
                print("La tabla 'alias_equipos' existe pero está vacía.")
        except sqlite3.OperationalError:
            print("[ALERTA] La tabla 'alias_equipos' no existe aún en la base de datos.")

        conn.close()

    except Exception as e:
        print(f"[ERROR] No se pudo acceder a la base de datos: {e}")

if __name__ == "__main__":
    inspeccionar_base_datos()
    