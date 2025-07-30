# db.py
import sqlite3
from datetime import datetime
import os
import psycopg2
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    """Obtiene una conexión a la base de datos."""
    if DATABASE_URL:
        # Entorno de producción (Render)
        return psycopg2.connect(DATABASE_URL)
    else:
        # Entorno local
        return sqlite3.connect("puntum.db")

def is_postgresql():
    """Detecta si estamos usando PostgreSQL"""
    return DATABASE_URL is not None

def create_all_tables():
    """Crea todas las tablas necesarias del sistema en una sola transacción."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        logger.info("🔄 Creando/verificando tablas de la base de datos...")
        
        if is_postgresql():
            # === TABLAS POSTGRESQL ===
            logger.info("📊 Usando PostgreSQL")
            
            # Tabla para juegos activos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_games (
                    chat_id BIGINT PRIMARY KEY,
                    juego TEXT,
                    respuesta TEXT,
                    pistas TEXT,
                    intentos INTEGER,
                    started_by BIGINT,
                    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla para trivias activas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_trivias (
                    chat_id BIGINT PRIMARY KEY,
                    pregunta TEXT,
                    respuesta TEXT,
                    start_time DOUBLE PRECISION,
                    opciones TEXT,
                    message_id BIGINT,
                    inline_keyboard_message_id BIGINT
                )
            """)
            
            # Tablas de autorización
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
            
            # Tablas de usuarios
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_points (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    username TEXT,
                    chat_name TEXT,
                    points_gained INTEGER NOT NULL,
                    reason TEXT,
                    message_id BIGINT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_ranking (
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    username TEXT,
                    chat_name TEXT,
                    total_points INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, chat_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_config (
                    chat_id BIGINT PRIMARY KEY,
                    chat_name TEXT,
                    rankings_enabled BOOLEAN DEFAULT TRUE,
                    challenges_enabled BOOLEAN DEFAULT TRUE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS challenges (
                    id SERIAL PRIMARY KEY,
                    challenger_id BIGINT NOT NULL,
                    challengee_id BIGINT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    message_id BIGINT,
                    status TEXT DEFAULT 'pending',
                    type TEXT,
                    data TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
        else:
            # === TABLAS SQLITE ===
            logger.info("📊 Usando SQLite")
            
            # Tabla para juegos activos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_games (
                    chat_id INTEGER PRIMARY KEY,
                    juego TEXT,
                    respuesta TEXT,
                    pistas TEXT,
                    intentos INTEGER,
                    started_by INTEGER,
                    last_activity TEXT
                )
            """)
            
            # Tabla para trivias activas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_trivias (
                    chat_id INTEGER PRIMARY KEY,
                    pregunta TEXT,
                    respuesta TEXT,
                    start_time REAL,
                    opciones TEXT,
                    message_id INTEGER,
                    inline_keyboard_message_id INTEGER
                )
            """)
            
            # Tablas de autorización
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
            
            # Tablas de usuarios
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    username TEXT,
                    chat_name TEXT,
                    points_gained INTEGER NOT NULL,
                    reason TEXT,
                    message_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_ranking (
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    username TEXT,
                    chat_name TEXT,
                    total_points INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, chat_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_config (
                    chat_id INTEGER PRIMARY KEY,
                    chat_name TEXT,
                    rankings_enabled INTEGER DEFAULT 1,
                    challenges_enabled INTEGER DEFAULT 1
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS challenges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    challenger_id INTEGER NOT NULL,
                    challengee_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER,
                    status TEXT DEFAULT 'pending',
                    type TEXT,
                    data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        conn.commit()
        logger.info("✅ Todas las tablas creadas/verificadas exitosamente")
        
    except Exception as e:
        logger.error(f"❌ Error al crear tablas: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

# FUNCIONES DE COMPATIBILIDAD (mantener para evitar romper imports)
def create_games_tables():
    """Crea las tablas necesarias para el sistema de juegos."""
    logger.info("⚠️ create_games_tables() deprecado, usando create_all_tables()")
    # No hacer nada, create_all_tables() ya se encarga de todo

def create_auth_tables():
    """Crear tablas para el sistema de autorización"""
    logger.info("⚠️ create_auth_tables() deprecado, usando create_all_tables()")
    # No hacer nada, create_all_tables() ya se encarga de todo

def create_user_tables():
    """Crea las tablas necesarias para el seguimiento de puntos de usuario."""
    logger.info("⚠️ create_user_tables() deprecado, usando create_all_tables()")
    # No hacer nada, create_all_tables() ya se encarga de todo

# === FUNCIONES DE PUNTOS Y RANKING ===

def add_points(user_id: int, chat_id: int, points: int, username: str, chat_name: str, reason: str, message_id: int):
    """Agregar puntos a un usuario"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if is_postgresql():
            cursor.execute(
                """INSERT INTO user_points (user_id, chat_id, username, chat_name, points_gained, reason, message_id, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """,
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
        else:
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
        logger.debug(f"✅ Puntos agregados: {points} a usuario {user_id} en chat {chat_id}")
    except Exception as e:
        logger.error(f"❌ Error añadiendo puntos: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def get_top_users(chat_id: int, limit: int = 10):
    """Obtener top usuarios por puntos"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute(
                """SELECT username, total_points FROM user_ranking 
                   WHERE chat_id = %s
                   ORDER BY total_points DESC
                   LIMIT %s
                """,
                (chat_id, limit)
            )
        else:
            cursor.execute(
                """SELECT username, total_points FROM user_ranking 
                   WHERE chat_id = ?
                   ORDER BY total_points DESC
                   LIMIT ?
                """,
                (chat_id, limit)
            )
        results = cursor.fetchall()
        return results
    except Exception as e:
        logger.error(f"❌ Error obteniendo top usuarios: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_user_rank(user_id: int, chat_id: int):
    """Obtener puntos totales de un usuario"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute(
                """SELECT total_points FROM user_ranking 
                   WHERE user_id = %s AND chat_id = %s
                """,
                (user_id, chat_id)
            )
        else:
            cursor.execute(
                """SELECT total_points FROM user_ranking 
                   WHERE user_id = ? AND chat_id = ?
                """,
                (user_id, chat_id)
            )
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception as e:
        logger.error(f"❌ Error obteniendo puntos de usuario: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()

# Función para compatibilidad con comandos_basicos.py
def get_top10(chat_id: int):
    """Obtener top 10 usuarios (alias para get_top_users)"""
    return get_top_users(chat_id, 10)

def update_user_ranking_points(user_id: int, chat_id: int, new_total_points: int, username: str, chat_name: str):
    """Actualizar puntos totales de un usuario"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
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
        else:
            cursor.execute(
                """INSERT OR REPLACE INTO user_ranking (user_id, chat_id, username, chat_name, total_points)
                   VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, chat_id, username, chat_name, new_total_points)
            )
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Error actualizando puntos de usuario: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

# === FUNCIONES DE CHALLENGES ===

def add_challenge(challenge_data):
    """Agregar un nuevo challenge"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute(
                """INSERT INTO challenges (challenger_id, challengee_id, chat_id, message_id, status, type, data, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (challenge_data['challenger_id'], challenge_data['challengee_id'], 
                 challenge_data['chat_id'], challenge_data['message_id'], 
                 challenge_data['status'], challenge_data['type'], 
                 challenge_data['data'])
            )
        else:
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
    except Exception as e:
        logger.error(f"❌ Error añadiendo challenge: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def get_challenge(challenge_id):
    """Obtener datos de un challenge"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute(
                """SELECT challenger_id, challengee_id, chat_id, message_id, status, type, data 
                   FROM challenges WHERE id = %s
                """,
                (challenge_id,)
            )
        else:
            cursor.execute(
                """SELECT challenger_id, challengee_id, chat_id, message_id, status, type, data 
                   FROM challenges WHERE id = ?
                """,
                (challenge_id,)
            )
        result = cursor.fetchone()
        if result:
            return dict(zip(['challenger_id', 'challengee_id', 'chat_id', 'message_id', 'status', 'type', 'data'], result))
        return None
    except Exception as e:
        logger.error(f"❌ Error obteniendo challenge: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def update_challenge_status(challenge_id, status):
    """Actualizar estado de un challenge"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute(
                """UPDATE challenges SET status = %s WHERE id = %s""",
                (status, challenge_id)
            )
        else:
            cursor.execute(
                """UPDATE challenges SET status = ? WHERE id = ?""",
                (status, challenge_id)
            )
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Error actualizando status de challenge: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def delete_challenge(challenge_id):
    """Eliminar un challenge"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute(
                """DELETE FROM challenges WHERE id = %s""",
                (challenge_id,)
            )
        else:
            cursor.execute(
                """DELETE FROM challenges WHERE id = ?""",
                (challenge_id,)
            )
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Error eliminando challenge: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

# === FUNCIONES DE CONFIGURACIÓN DE CHAT ===

def save_chat_config(chat_id: int, chat_name: str, rankings_enabled: bool, challenges_enabled: bool):
    """Guardar configuración de chat"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
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
        else:
            cursor.execute(
                """INSERT OR REPLACE INTO chat_config (chat_id, chat_name, rankings_enabled, challenges_enabled)
                   VALUES (?, ?, ?, ?)
                """,
                (chat_id, chat_name, rankings_enabled, challenges_enabled)
            )
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Error guardando configuración de chat: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def get_chat_config(chat_id: int):
    """Obtener configuración de chat"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute(
                """SELECT chat_name, rankings_enabled, challenges_enabled
                   FROM chat_config 
                   WHERE chat_id = %s""",
                (chat_id,)
            )
        else:
            cursor.execute(
                """SELECT chat_name, rankings_enabled, challenges_enabled
                   FROM chat_config 
                   WHERE chat_id = ?""",
                (chat_id,)
            )
        result = cursor.fetchone()
        
        if result:
            return {
                "chat_name": result[0],
                "rankings_enabled": bool(result[1]),
                "challenges_enabled": bool(result[2])
            }
        return None
    except Exception as e:
        logger.error(f"❌ Error obteniendo configuración de chat: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_configured_chats():
    """Obtener todos los chats configurados"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute(
                """SELECT chat_id, chat_name, rankings_enabled, challenges_enabled
                   FROM chat_config"""
            )
        else:
            cursor.execute(
                """SELECT chat_id, chat_name, rankings_enabled, challenges_enabled
                   FROM chat_config"""
            )
        results = cursor.fetchall()
        
        configured_chats = []
        for row in results:
            configured_chats.append({
                "chat_id": row[0],
                "chat_name": row[1],
                "rankings_enabled": bool(row[2]),
                "challenges_enabled": bool(row[3])
            })
        
        return configured_chats
    except Exception as e:
        logger.error(f"❌ Error obteniendo chats configurados: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

# === FUNCIONES ESPECÍFICAS PARA JUEGOS ===

def save_active_game(chat_id: int, juego: str, respuesta: str, pistas: str, intentos: int, started_by: int):
    """Guardar juego activo"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute(
                """INSERT INTO active_games (chat_id, juego, respuesta, pistas, intentos, started_by, last_activity)
                   VALUES (%s, %s, %s, %s, %s, %s, NOW())
                   ON CONFLICT (chat_id) DO UPDATE SET
                   juego = EXCLUDED.juego,
                   respuesta = EXCLUDED.respuesta,
                   pistas = EXCLUDED.pistas,
                   intentos = EXCLUDED.intentos,
                   started_by = EXCLUDED.started_by,
                   last_activity = NOW()
                """,
                (chat_id, juego, respuesta, pistas, intentos, started_by)
            )
        else:
            cursor.execute(
                """INSERT OR REPLACE INTO active_games (chat_id, juego, respuesta, pistas, intentos, started_by, last_activity)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (chat_id, juego, respuesta, pistas, intentos, started_by, datetime.now().isoformat())
            )
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Error guardando juego activo: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def get_active_game(chat_id: int):
    """Obtener juego activo"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute(
                """SELECT juego, respuesta, pistas, intentos, started_by, last_activity
                   FROM active_games WHERE chat_id = %s
                """,
                (chat_id,)
            )
        else:
            cursor.execute(
                """SELECT juego, respuesta, pistas, intentos, started_by, last_activity
                   FROM active_games WHERE chat_id = ?
                """,
                (chat_id,)
            )
        result = cursor.fetchone()
        if result:
            return {
                'juego': result[0],
                'respuesta': result[1],
                'pistas': result[2],
                'intentos': result[3],
                'started_by': result[4],
                'last_activity': result[5]
            }
        return None
    except Exception as e:
        logger.error(f"❌ Error obteniendo juego activo: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def delete_active_game(chat_id: int):
    """Eliminar juego activo"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute("DELETE FROM active_games WHERE chat_id = %s", (chat_id,))
        else:
            cursor.execute("DELETE FROM active_games WHERE chat_id = ?", (chat_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Error eliminando juego activo: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def save_active_trivia(chat_id: int, pregunta: str, respuesta: str, start_time: float, opciones: str, message_id: int, inline_keyboard_message_id: int):
    """Guardar trivia activa"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute(
                """INSERT INTO active_trivias (chat_id, pregunta, respuesta, start_time, opciones, message_id, inline_keyboard_message_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (chat_id) DO UPDATE SET
                   pregunta = EXCLUDED.pregunta,
                   respuesta = EXCLUDED.respuesta,
                   start_time = EXCLUDED.start_time,
                   opciones = EXCLUDED.opciones,
                   message_id = EXCLUDED.message_id,
                   inline_keyboard_message_id = EXCLUDED.inline_keyboard_message_id
                """,
                (chat_id, pregunta, respuesta, start_time, opciones, message_id, inline_keyboard_message_id)
            )
        else:
            cursor.execute(
                """INSERT OR REPLACE INTO active_trivias (chat_id, pregunta, respuesta, start_time, opciones, message_id, inline_keyboard_message_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (chat_id, pregunta, respuesta, start_time, opciones, message_id, inline_keyboard_message_id)
            )
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Error guardando trivia activa: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def get_active_trivia(chat_id: int):
    """Obtener trivia activa"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute(
                """SELECT pregunta, respuesta, start_time, opciones, message_id, inline_keyboard_message_id
                   FROM active_trivias WHERE chat_id = %s
                """,
                (chat_id,)
            )
        else:
            cursor.execute(
                """SELECT pregunta, respuesta, start_time, opciones, message_id, inline_keyboard_message_id
                   FROM active_trivias WHERE chat_id = ?
                """,
                (chat_id,)
            )
        result = cursor.fetchone()
        if result:
            return {
                'pregunta': result[0],
                'respuesta': result[1],
                'start_time': result[2],
                'opciones': result[3],
                'message_id': result[4],
                'inline_keyboard_message_id': result[5]
            }
        return None
    except Exception as e:
        logger.error(f"❌ Error obteniendo trivia activa: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def delete_active_trivia(chat_id: int):
    """Eliminar trivia activa"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute("DELETE FROM active_trivias WHERE chat_id = %s", (chat_id,))
        else:
            cursor.execute("DELETE FROM active_trivias WHERE chat_id = ?", (chat_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Error eliminando trivia activa: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def get_all_active_games():
    """Obtener todos los juegos activos (para limpieza automática)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute(
                """SELECT chat_id, juego, respuesta, pistas, intentos, started_by, last_activity
                   FROM active_games
                """)
        else:
            cursor.execute(
                """SELECT chat_id, juego, respuesta, pistas, intentos, started_by, last_activity
                   FROM active_games
                """)
        results = cursor.fetchall()
        
        games = []
        for row in results:
            games.append({
                'chat_id': row[0],
                'juego': row[1],
                'respuesta': row[2],
                'pistas': row[3],
                'intentos': row[4],
                'started_by': row[5],
                'last_activity': row[6]
            })
        
        return games
    except Exception as e:
        logger.error(f"❌ Error obteniendo todos los juegos activos: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_all_active_trivias():
    """Obtener todas las trivias activas (para limpieza automática)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute(
                """SELECT chat_id, pregunta, respuesta, start_time, opciones, message_id, inline_keyboard_message_id
                   FROM active_trivias
                """)
        else:
            cursor.execute(
                """SELECT chat_id, pregunta, respuesta, start_time, opciones, message_id, inline_keyboard_message_id
                   FROM active_trivias
                """)
        results = cursor.fetchall()
        
        trivias = []
        for row in results:
            trivias.append({
                'chat_id': row[0],
                'pregunta': row[1],
                'respuesta': row[2],
                'start_time': row[3],
                'opciones': row[4],
                'message_id': row[5],
                'inline_keyboard_message_id': row[6]
            })
        
        return trivias
    except Exception as e:
        logger.error(f"❌ Error obteniendo todas las trivias activas: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

# === FUNCIONES DE UTILIDAD ===

def cleanup_expired_games(timeout_minutes: int = 5):
    """Limpiar juegos expirados"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_postgresql():
            cursor.execute(
                """DELETE FROM active_games 
                   WHERE last_activity < NOW() - INTERVAL '%s minutes'
                """,
                (timeout_minutes,)
            )
            cursor.execute(
                """DELETE FROM active_trivias 
                   WHERE start_time < EXTRACT(EPOCH FROM NOW()) - %s
                """,
                (timeout_minutes * 60,)  # convertir a segundos
            )
        else:
            # Para SQLite, necesitamos una lógica diferente ya que maneja fechas como strings
            from datetime import datetime, timedelta
            cutoff_time = (datetime.now() - timedelta(minutes=timeout_minutes)).isoformat()
            cutoff_timestamp = (datetime.now() - timedelta(minutes=timeout_minutes)).timestamp()
            
            cursor.execute(
                """DELETE FROM active_games 
                   WHERE last_activity < ?
                """,
                (cutoff_time,)
            )
            cursor.execute(
                """DELETE FROM active_trivias 
                   WHERE start_time < ?
                """,
                (cutoff_timestamp,)
            )
        
        deleted_games = cursor.rowcount
        conn.commit()
        
        if deleted_games > 0:
            logger.info(f"🧹 Limpiados {deleted_games} juegos/trivias expirados")
            
        return deleted_games
    except Exception as e:
        logger.error(f"❌ Error limpiando juegos expirados: {e}")
        conn.rollback()
        return 0
    finally:
        cursor.close()
        conn.close()

def get_user_stats(user_id: int, chat_id: int):
    """Obtener estadísticas completas de un usuario"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        stats = {
            'total_points': 0,
            'total_entries': 0,
            'hashtag_points': 0,
            'game_points': 0,
            'challenge_points': 0,
            'rank_position': 0
        }
        
        if is_postgresql():
            # Puntos totales
            cursor.execute(
                """SELECT total_points FROM user_ranking 
                   WHERE user_id = %s AND chat_id = %s
                """,
                (user_id, chat_id)
            )
            result = cursor.fetchone()
            stats['total_points'] = result[0] if result else 0
            
            # Número total de entradas
            cursor.execute(
                """SELECT COUNT(*) FROM user_points 
                   WHERE user_id = %s AND chat_id = %s
                """,
                (user_id, chat_id)
            )
            result = cursor.fetchone()
            stats['total_entries'] = result[0] if result else 0
            
            # Puntos por categorías
            cursor.execute(
                """SELECT reason, SUM(points_gained) FROM user_points 
                   WHERE user_id = %s AND chat_id = %s
                   GROUP BY reason
                """,
                (user_id, chat_id)
            )
            results = cursor.fetchall()
            
            for reason, points in results:
                if 'hashtag' in reason.lower():
                    stats['hashtag_points'] += points
                elif 'juego' in reason.lower() or 'trivia' in reason.lower():
                    stats['game_points'] += points
                elif 'reto' in reason.lower() or 'challenge' in reason.lower():
                    stats['challenge_points'] += points
            
            # Posición en ranking
            cursor.execute(
                """SELECT COUNT(*) + 1 FROM user_ranking 
                   WHERE chat_id = %s AND total_points > (
                       SELECT total_points FROM user_ranking 
                       WHERE user_id = %s AND chat_id = %s
                   )
                """,
                (chat_id, user_id, chat_id)
            )
            result = cursor.fetchone()
            stats['rank_position'] = result[0] if result else 0
            
        else:
            # Mismas consultas pero con sintaxis SQLite
            cursor.execute(
                """SELECT total_points FROM user_ranking 
                   WHERE user_id = ? AND chat_id = ?
                """,
                (user_id, chat_id)
            )
            result = cursor.fetchone()
            stats['total_points'] = result[0] if result else 0
            
            cursor.execute(
                """SELECT COUNT(*) FROM user_points 
                   WHERE user_id = ? AND chat_id = ?
                """,
                (user_id, chat_id)
            )
            result = cursor.fetchone()
            stats['total_entries'] = result[0] if result else 0
            
            cursor.execute(
                """SELECT reason, SUM(points_gained) FROM user_points 
                   WHERE user_id = ? AND chat_id = ?
                   GROUP BY reason
                """,
                (user_id, chat_id)
            )
            results = cursor.fetchall()
            
            for reason, points in results:
                if 'hashtag' in reason.lower():
                    stats['hashtag_points'] += points
                elif 'juego' in reason.lower() or 'trivia' in reason.lower():
                    stats['game_points'] += points
                elif 'reto' in reason.lower() or 'challenge' in reason.lower():
                    stats['challenge_points'] += points
            
            cursor.execute(
                """SELECT COUNT(*) + 1 FROM user_ranking 
                   WHERE chat_id = ? AND total_points > (
                       SELECT total_points FROM user_ranking 
                       WHERE user_id = ? AND chat_id = ?
                   )
                """,
                (chat_id, user_id, chat_id)
            )
            result = cursor.fetchone()
            stats['rank_position'] = result[0] if result else 0
        
        return stats
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas de usuario: {e}")
        return {
            'total_points': 0,
            'total_entries': 0,
            'hashtag_points': 0,
            'game_points': 0,
            'challenge_points': 0,
            'rank_position': 0
        }
    finally:
        cursor.close()
        conn.close()

def get_chat_stats(chat_id: int):
    """Obtener estadísticas del chat"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        stats = {
            'total_users': 0,
            'total_points_distributed': 0,
            'active_games': 0,
            'active_trivias': 0,
            'top_user': None,
            'top_points': 0
        }
        
        if is_postgresql():
            # Total de usuarios únicos
            cursor.execute(
                """SELECT COUNT(DISTINCT user_id) FROM user_ranking 
                   WHERE chat_id = %s
                """,
                (chat_id,)
            )
            result = cursor.fetchone()
            stats['total_users'] = result[0] if result else 0
            
            # Total de puntos distribuidos
            cursor.execute(
                """SELECT SUM(points_gained) FROM user_points 
                   WHERE chat_id = %s
                """,
                (chat_id,)
            )
            result = cursor.fetchone()
            stats['total_points_distributed'] = result[0] if result else 0
            
            # Juegos activos
            cursor.execute("SELECT COUNT(*) FROM active_games WHERE chat_id = %s", (chat_id,))
            result = cursor.fetchone()
            stats['active_games'] = result[0] if result else 0
            
            # Trivias activas
            cursor.execute("SELECT COUNT(*) FROM active_trivias WHERE chat_id = %s", (chat_id,))
            result = cursor.fetchone()
            stats['active_trivias'] = result[0] if result else 0
            
            # Usuario con más puntos
            cursor.execute(
                """SELECT username, total_points FROM user_ranking 
                   WHERE chat_id = %s
                   ORDER BY total_points DESC
                   LIMIT 1
                """,
                (chat_id,)
            )
            result = cursor.fetchone()
            if result:
                stats['top_user'] = result[0]
                stats['top_points'] = result[1]
                
        else:
            # Mismas consultas para SQLite
            cursor.execute(
                """SELECT COUNT(DISTINCT user_id) FROM user_ranking 
                   WHERE chat_id = ?
                """,
                (chat_id,)
            )
            result = cursor.fetchone()
            stats['total_users'] = result[0] if result else 0
            
            cursor.execute(
                """SELECT SUM(points_gained) FROM user_points 
                   WHERE chat_id = ?
                """,
                (chat_id,)
            )
            result = cursor.fetchone()
            stats['total_points_distributed'] = result[0] if result else 0
            
            cursor.execute("SELECT COUNT(*) FROM active_games WHERE chat_id = ?", (chat_id,))
            result = cursor.fetchone()
            stats['active_games'] = result[0] if result else 0
            
            cursor.execute("SELECT COUNT(*) FROM active_trivias WHERE chat_id = ?", (chat_id,))
            result = cursor.fetchone()
            stats['active_trivias'] = result[0] if result else 0
            
            cursor.execute(
                """SELECT username, total_points FROM user_ranking 
                   WHERE chat_id = ?
                   ORDER BY total_points DESC
                   LIMIT 1
                """,
                (chat_id,)
            )
            result = cursor.fetchone()
            if result:
                stats['top_user'] = result[0]
                stats['top_points'] = result[1]
        
        return stats
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas del chat: {e}")
        return {
            'total_users': 0,
            'total_points_distributed': 0,
            'active_games': 0,
            'active_trivias': 0,
            'top_user': None,
            'top_points': 0
        }
    finally:
        cursor.close()
        conn.close()

# === FUNCIÓN DE INICIALIZACIÓN ===

def initialize_database():
    """Inicializar la base de datos completamente"""
    try:
        logger.info("🔄 Inicializando base de datos...")
        create_all_tables()
        logger.info("✅ Base de datos inicializada correctamente")
        return True
    except Exception as e:
        logger.error(f"❌ Error inicializando base de datos: {e}")
        return False

# Ejecutar inicialización si se importa el módulo directamente
if __name__ == "__main__":
    logger.info("🧪 Ejecutando db.py directamente - Inicializando base de datos...")
    if initialize_database():
        logger.info("🎉 Base de datos lista para usar!")
    else:
        logger.error("💥 Error en la inicialización de la base de datos")