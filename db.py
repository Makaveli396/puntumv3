# db.py
import sqlite3
from datetime import datetime
import os
import psycopg2 # Asegúrate de que psycopg2 esté instalado en tu entorno de Render

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    """Obtiene una conexión a la base de datos."""
    if DATABASE_URL:
        # Entorno de producción (Render)
        return psycopg2.connect(DATABASE_URL)
    else:
        # Entorno local
        return sqlite3.connect("puntum.db")

def create_games_tables(conn, cursor):
    """Crea las tablas necesarias para el sistema de juegos."""
    try:
        # Tabla para juegos activos
        if DATABASE_URL: # PostgreSQL
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS active_games (
                    chat_id BIGINT PRIMARY KEY,
                    juego TEXT,
                    respuesta TEXT, -- ¡Añadida esta columna!
                    pistas TEXT, -- Asumiendo que pistas se guarda como JSON string
                    intentos INTEGER,
                    started_by BIGINT,
                    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )"""
            )
        else: # SQLite
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS active_games (
                    chat_id INTEGER PRIMARY KEY,
                    juego TEXT,
                    respuesta TEXT, -- ¡Añadida esta columna!
                    pistas TEXT,
                    intentos INTEGER,
                    started_by INTEGER,
                    last_activity TEXT
                )"""
            )
        
        # Tabla para trivias activas (ya debería tener pregunta y respuesta)
        if DATABASE_URL: # PostgreSQL
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS active_trivias (
                    chat_id BIGINT PRIMARY KEY,
                    pregunta TEXT,
                    respuesta TEXT,
                    start_time DOUBLE PRECISION,
                    opciones TEXT,
                    message_id BIGINT,
                    inline_keyboard_message_id BIGINT
                )"""
            )
        else: # SQLite
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS active_trivias (
                    chat_id INTEGER PRIMARY KEY,
                    pregunta TEXT,
                    respuesta TEXT,
                    start_time REAL,
                    opciones TEXT,
                    message_id INTEGER,
                    inline_keyboard_message_id INTEGER
                )"""
            )
        conn.commit()
    except Exception as e:
        print(f"Error al crear tablas de juegos: {e}")
        conn.rollback()
    finally:
        conn.close()

def create_auth_tables(conn, cursor):
    """Crear tablas para el sistema de autorización"""
    try:
        if DATABASE_URL: # PostgreSQL
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS authorized_chats (
                    chat_id BIGINT PRIMARY KEY,
                    chat_title TEXT,
                    authorized_by BIGINT,
                    authorized_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auth_requests (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT,
                    chat_title TEXT,
                    requested_by BIGINT,
                    requester_username TEXT,
                    requested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                )
            """)
        else: # SQLite
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS authorized_chats (
                    chat_id INTEGER PRIMARY KEY,
                    chat_title TEXT,
                    authorized_by INTEGER,
                    authorized_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auth_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    chat_title TEXT,
                    requested_by INTEGER,
                    requester_username TEXT,
                    requested_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                )
            """)
        conn.commit()
    except Exception as e:
        print(f"Error al crear tablas de autorización: {e}")
        conn.rollback()
    finally:
        conn.close()


def create_user_tables(conn, cursor):
    """Crea las tablas necesarias para el seguimiento de puntos de usuario."""
    try:
        if DATABASE_URL: # PostgreSQL
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS user_points (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    username TEXT,
                    chat_name TEXT,
                    points_gained INTEGER NOT NULL,
                    reason TEXT,
                    message_id BIGINT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS user_ranking (
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    username TEXT,
                    chat_name TEXT,
                    total_points INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, chat_id)
                )"""
            )
            # Ejemplo: crear una tabla para hashtags si la necesitas
            # cursor.execute(
            #     """CREATE TABLE IF NOT EXISTS user_hashtags (
            #         id SERIAL PRIMARY KEY,
            #         user_id BIGINT NOT NULL,
            #         chat_id BIGINT NOT NULL,
            #         hashtag TEXT NOT NULL,
            #         created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            #     )"""
            # )
        else: # SQLite
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS user_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    username TEXT,
                    chat_name TEXT,
                    points_gained INTEGER NOT NULL,
                    reason TEXT,
                    message_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS user_ranking (
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    username TEXT,
                    chat_name TEXT,
                    total_points INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, chat_id)
                )"""
            )
            # Ejemplo: crear una tabla para hashtags si la necesitas
            # cursor.execute(
            #     """CREATE TABLE IF NOT EXISTS user_hashtags (
            #         id INTEGER PRIMARY KEY AUTOINCREMENT,
            #         user_id INTEGER NOT NULL,
            #         chat_id INTEGER NOT NULL,
            #         hashtag TEXT NOT NULL,
            #         created_at TEXT DEFAULT CURRENT_TIMESTAMP
            #     )"""
            # )
        conn.commit()
    except Exception as e:
        print(f"Error al crear tablas de usuario: {e}")
        conn.rollback()
    finally:
        conn.close()

def add_points(user_id: int, chat_id: int, points: int, username: str, chat_name: str, reason: str, message_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    if DATABASE_URL: # PostgreSQL
        cursor.execute(
            """INSERT INTO user_points (user_id, chat_id, username, chat_name, points_gained, reason, message_id, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, # NOW() para PostgreSQL
            (user_id, chat_id, username, chat_name, points, reason, message_id)
        )
        cursor.execute(
            """INSERT INTO user_ranking (user_id, chat_id, username, chat_name, total_points)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (user_id, chat_id) DO UPDATE SET
               username = EXCLUDED.username,
               chat_name = EXCLUDED.chat_name,
               total_points = user_ranking.total_points + EXCLUDED.total_points
            """,
            (user_id, chat_id, username, chat_name, points)
        )
    else: # SQLite
        cursor.execute(
            """INSERT INTO user_points (user_id, chat_id, username, chat_name, points_gained, reason, message_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, chat_id, username, chat_name, points, reason, message_id, datetime.now().isoformat())
        )
        cursor.execute(
            """INSERT OR REPLACE INTO user_ranking (user_id, chat_id, username, chat_name, total_points)
               VALUES (?, ?, ?, ?, COALESCE((SELECT total_points FROM user_ranking WHERE user_id = ? AND chat_id = ?), 0) + ?)
            """,
            (user_id, chat_id, username, chat_name, user_id, chat_id, points)
        )

    conn.commit()
    conn.close()

def get_top_users(chat_id: int, limit: int = 10):
    conn = get_connection()
    cursor = conn.cursor()
    if DATABASE_URL: # PostgreSQL
        cursor.execute(
            """SELECT username, total_points FROM user_ranking 
               WHERE chat_id = %s
               ORDER BY total_points DESC
               LIMIT %s
            """,
            (chat_id, limit)
        )
    else: # SQLite
        cursor.execute(
            """SELECT username, total_points FROM user_ranking 
               WHERE chat_id = ?
               ORDER BY total_points DESC
               LIMIT ?
            """,
            (chat_id, limit)
        )
    results = cursor.fetchall()
    conn.close()
    return results

def get_user_rank(user_id: int, chat_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    if DATABASE_URL: # PostgreSQL
        cursor.execute(
            """SELECT total_points FROM user_ranking 
               WHERE user_id = %s AND chat_id = %s
            """,
            (user_id, chat_id)
        )
    else: # SQLite
        cursor.execute(
            """SELECT total_points FROM user_ranking 
               WHERE user_id = ? AND chat_id = ?
            """,
            (user_id, chat_id)
        )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def update_user_ranking_points(user_id: int, chat_id: int, new_total_points: int, username: str, chat_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    if DATABASE_URL: # PostgreSQL
        cursor.execute(
            """INSERT INTO user_ranking (user_id, chat_id, username, chat_name, total_points)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (user_id, chat_id) DO UPDATE SET
               username = EXCLUDED.username,
               chat_name = EXCLUDED.chat_name,
               total_points = EXCLUDED.total_points
            """,
            (user_id, chat_id, username, chat_name, new_total_points)
        )
    else: # SQLite
        cursor.execute(
            """INSERT OR REPLACE INTO user_ranking (user_id, chat_id, username, chat_name, total_points)
               VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, chat_id, username, chat_name, new_total_points)
        )
    conn.commit()
    conn.close()

def add_challenge(challenge_data):
    conn = get_connection()
    cursor = conn.cursor()
    if DATABASE_URL: # PostgreSQL
        cursor.execute(
            """INSERT INTO challenges (challenger_id, challengee_id, chat_id, message_id, status, type, data, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            (challenge_data['challenger_id'], challenge_data['challengee_id'], 
             challenge_data['chat_id'], challenge_data['message_id'], 
             challenge_data['status'], challenge_data['type'], 
             challenge_data['data'])
        )
    else: # SQLite
        cursor.execute(
            """INSERT INTO challenges (challenger_id, challengee_id, chat_id, message_id, status, type, data, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (challenge_data['challenger_id'], challenge_data['challengee_id'], 
             challenge_data['chat_id'], challenge_data['message_id'], 
             challenge_data['status'], challenge_data['type'], 
             challenge_data['data'], datetime.now().isoformat())
        )
    conn.commit()
    conn.close()

def get_challenge(challenge_id):
    conn = get_connection()
    cursor = conn.cursor()
    if DATABASE_URL: # PostgreSQL
        cursor.execute(
            """SELECT challenger_id, challengee_id, chat_id, message_id, status, type, data 
               FROM challenges WHERE id = %s
            """,
            (challenge_id,)
        )
    else: # SQLite
        cursor.execute(
            """SELECT challenger_id, challengee_id, chat_id, message_id, status, type, data 
               FROM challenges WHERE id = ?
            """,
            (challenge_id,)
        )
    result = cursor.fetchone()
    conn.close()
    return dict(zip(['challenger_id', 'challengee_id', 'chat_id', 'message_id', 'status', 'type', 'data'], result)) if result else None

def update_challenge_status(challenge_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    if DATABASE_URL: # PostgreSQL
        cursor.execute(
            """UPDATE challenges SET status = %s WHERE id = %s""",
            (status, challenge_id)
        )
    else: # SQLite
        cursor.execute(
            """UPDATE challenges SET status = ? WHERE id = ?""",
            (status, challenge_id)
        )
    conn.commit()
    conn.close()

def delete_challenge(challenge_id):
    conn = get_connection()
    cursor = conn.cursor()
    if DATABASE_URL: # PostgreSQL
        cursor.execute(
            """DELETE FROM challenges WHERE id = %s""",
            (challenge_id,)
        )
    else: # SQLite
        cursor.execute(
            """DELETE FROM challenges WHERE id = ?""",
            (challenge_id,)
        )
    conn.commit()
    conn.close()

def save_chat_config(chat_id: int, chat_name: str, rankings_enabled: bool, challenges_enabled: bool):
    """Save chat configuration"""
    conn = get_connection()
    cursor = conn.cursor()
    if DATABASE_URL: # PostgreSQL
        cursor.execute(
            """INSERT INTO chat_config (chat_id, chat_name, rankings_enabled, challenges_enabled)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (chat_id) DO UPDATE SET
               chat_name = EXCLUDED.chat_name,
               rankings_enabled = EXCLUDED.rankings_enabled,
               challenges_enabled = EXCLUDED.challenges_enabled
            """,
            (chat_id, chat_name, rankings_enabled, challenges_enabled)
        )
    else: # SQLite
        cursor.execute(
            """INSERT OR REPLACE INTO chat_config (chat_id, chat_name, rankings_enabled, challenges_enabled)
               VALUES (?, ?, ?, ?)
            """,
            (chat_id, chat_name, rankings_enabled, challenges_enabled)
        )
    conn.commit()
    conn.close()

def get_chat_config(chat_id: int):
    """Get chat configuration"""
    conn = get_connection()
    cursor = conn.cursor()
    if DATABASE_URL: # PostgreSQL
        cursor.execute(
            """SELECT chat_name, rankings_enabled, challenges_enabled
               FROM chat_config 
               WHERE chat_id = %s""",
            (chat_id,)
        )
    else: # SQLite
        cursor.execute(
            """SELECT chat_name, rankings_enabled, challenges_enabled
               FROM chat_config 
               WHERE chat_id = ?""",
            (chat_id,)
        )
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "chat_name": result[0],
            "rankings_enabled": bool(result[1]),
            "challenges_enabled": bool(result[2])
        }
    return None

def get_configured_chats():
    """Get all configured chats"""
    conn = get_connection()
    cursor = conn.cursor()
    if DATABASE_URL: # PostgreSQL
        cursor.execute(
            """SELECT chat_id, chat_name, rankings_enabled, challenges_enabled
               FROM chat_config
               WHERE rankings_enabled = TRUE OR challenges_enabled = TRUE"""
        )
    else: # SQLite
        cursor.execute(
            """SELECT chat_id, chat_name, rankings_enabled, challenges_enabled
               FROM chat_config
               WHERE rankings_enabled = 1 OR challenges_enabled = 1"""
        )
    results = cursor.fetchall()
    conn.close()
    
    # Convertir a un formato más manejable
    configured_chats = []
    for row in results:
        configured_chats.append({
            "chat_id": row[0],
            "chat_name": row[1],
            "rankings_enabled": bool(row[2]),
            "challenges_enabled": bool(row[3])
        })
    return configured_chats

def get_user_stats(user_id: int, chat_id: int):
    """Obtiene las estadísticas de un usuario específico en un chat."""
    conn = get_connection()
    cursor = conn.cursor()
    
    total_points = 0
    hashtag_counts = {}

    try:
        if DATABASE_URL: # PostgreSQL
            # Obtener puntos totales
            cursor.execute(
                """SELECT total_points FROM user_ranking
                   WHERE user_id = %s AND chat_id = %s""",
                (user_id, chat_id)
            )
            result = cursor.fetchone()
            if result:
                total_points = result[0]
            
            # Si tienes una tabla 'user_hashtags' para conteo de hashtags, puedes añadir aquí la consulta:
            # cursor.execute(
            #     """SELECT hashtag, COUNT(*) as count FROM user_hashtags
            #        WHERE user_id = %s AND chat_id = %s
            #        GROUP BY hashtag
            #        ORDER BY count DESC
            #        LIMIT 10""",
            #     (user_id, chat_id)
            # )
            # hashtag_rows = cursor.fetchall()
            # for hashtag, count in hashtag_rows:
            #     hashtag_counts[hashtag] = count

        else: # SQLite
            # Obtener puntos totales
            cursor.execute(
                """SELECT total_points FROM user_ranking
                   WHERE user_id = ? AND chat_id = ?""",
                (user_id, chat_id)
            )
            result = cursor.fetchone()
            if result:
                total_points = result[0]
            
            # Si tienes una tabla 'user_hashtags' para conteo de hashtags, puedes añadir aquí la consulta:
            # cursor.execute(
            #     """SELECT hashtag, COUNT(*) as count FROM user_hashtags
            #        WHERE user_id = ? AND chat_id = ?
            #        GROUP BY hashtag
            #        ORDER BY count DESC
            #        LIMIT 10""",
            #     (user_id, chat_id)
            # )
            # hashtag_rows = cursor.fetchall()
            # for hashtag, count in hashtag_rows:
            #     hashtag_counts[hashtag] = count

    except Exception as e:
        print(f"Error al obtener estadísticas de usuario: {e}")
    finally:
        conn.close()
    
    return {'total_points': total_points, 'hashtag_counts': hashtag_counts}

def get_top10(chat_id: int):
    """Obtiene el top 10 de usuarios en un chat."""
    conn = get_connection()
    cursor = conn.cursor()
    if DATABASE_URL: # PostgreSQL
        cursor.execute(
            """SELECT username, total_points FROM user_ranking 
               WHERE chat_id = %s
               ORDER BY total_points DESC
               LIMIT 10
            """,
            (chat_id,)
        )
    else: # SQLite
        cursor.execute(
            """SELECT username, total_points FROM user_ranking 
               WHERE chat_id = ?
               ORDER BY total_points DESC
               LIMIT 10
            """,
            (chat_id,)
        )
    results = cursor.fetchall()
    conn.close()
    return results