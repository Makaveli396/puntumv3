# db.py
import sqlite3
from datetime import datetime
import logging # Añadido para logging
import os      # Añadido para usar variables de entorno para la DB

logger = logging.getLogger(__name__) # Inicializa el logger

# Cambiado a DATABASE_URL para consistencia con despliegues en Render
# Render a menudo usa una variable de entorno como DATABASE_URL para la URL de la DB.
# Si usas una DB externa, deberías configurar esta variable en Render.
# Para SQLite, 'bot_database.db' es un buen valor por defecto.
DATABASE_URL = os.environ.get('DATABASE_URL', 'bot_database.db')

def get_connection():
    """Obtiene una conexión a la base de datos SQLite."""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row # Opcional: permite acceder a columnas por nombre
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error al conectar con la base de datos: {e}")
        raise # Vuelve a lanzar la excepción para que el problema sea visible

# RENOMBRADA create_tables a initialize_db
def initialize_db():
    """Inicializa la base de datos y crea las tablas si no existen."""
    conn = None # Inicializar conn para el bloque finally
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """CREATE TABLE IF NOT EXISTS points (
                user_id INTEGER,
                username TEXT,
                points INTEGER,
                hashtag TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                chat_id INTEGER,
                message_id INTEGER,
                is_challenge_bonus INTEGER DEFAULT 0
            )"""
        )

        cursor.execute(
            """CREATE TABLE IF NOT EXISTS user_achievements (
                user_id INTEGER,
                achievement_id INTEGER,
                date TEXT DEFAULT CURRENT_DATE,
                PRIMARY KEY (user_id, achievement_id)
            )"""
        )

        cursor.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                points INTEGER DEFAULT 0,
                count INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )

        cursor.execute(
            """CREATE TABLE IF NOT EXISTS chat_config (
                chat_id INTEGER PRIMARY KEY,
                chat_name TEXT,
                rankings_enabled BOOLEAN DEFAULT 1,
                challenges_enabled BOOLEAN DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )

        conn.commit()
        logger.info("Base de datos inicializada y tablas verificadas/creadas correctamente.")
    except sqlite3.Error as e:
        logger.error(f"Error al inicializar la base de datos: {e}")
        # Aquí puedes decidir si relanzar la excepción o manejarla de otra forma
        raise # Relanza para que el error de inicialización detenga el bot si es crítico
    finally:
        if conn: # Asegura que la conexión se cierre solo si se abrió
            conn.close()

def add_points(user_id, username, points, hashtag=None, message_text=None, chat_id=None, message_id=None, is_challenge_bonus=False, context=None):
    """Añade puntos a un usuario y actualiza sus estadísticas."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """INSERT INTO points (user_id, username, points, hashtag, chat_id, message_id, is_challenge_bonus)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, username, points, hashtag, chat_id, message_id, int(is_challenge_bonus))
    )

    # Update or create user record
    cursor.execute(
        """INSERT OR REPLACE INTO users (id, username, points, count, level, created_at)
           VALUES (?, ?,
                   COALESCE((SELECT points FROM users WHERE id = ?), 0) + ?,
                   COALESCE((SELECT count FROM users WHERE id = ?), 0) + 1,
                   ?,
                   COALESCE((SELECT created_at FROM users WHERE id = ?), CURRENT_TIMESTAMP))""",
        (user_id, username, user_id, points, user_id, calculate_level(get_user_total_points(user_id) + points), user_id)
    )

    conn.commit()
    conn.close()

    if context and chat_id:
        try:
            # Asegúrate de que esta importación se maneje correctamente si 'handlers' no existe
            # o si no quieres el módulo de achievements.
            # En tu bot.py se importaba 'db' y no 'handlers.achievements' directamente aquí.
            # Si 'check_achievements' es una función que quieres importar en bot.py,
            # asegúrate de que esté disponible desde un módulo importable.
            # Por ahora, mantengo el código tal cual estaba aquí en db.py.
            from handlers.achievements import check_achievements
            check_achievements(user_id, username, context, chat_id)
        except ImportError:
            logger.warning("Módulo 'handlers.achievements' no encontrado. Las comprobaciones de logros están deshabilitadas.")
        except Exception as e:
            logger.error(f"Error al comprobar logros para el usuario {user_id}: {e}")

    return {"ok": True}

def add_achievement(user_id: int, achievement_id: int):
    """Añade un logro a un usuario si no lo tiene ya."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT OR IGNORE INTO user_achievements (user_id, achievement_id)
           VALUES (?, ?)""",
        (user_id, achievement_id)
    )
    conn.commit()
    conn.close()
    logger.info(f"Logro {achievement_id} añadido (o ya existente) para el usuario {user_id}.")


def get_user_total_points(user_id: int) -> int:
    """Obtiene los puntos totales de un usuario."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT COALESCE(SUM(points), 0) FROM points WHERE user_id = ?""",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def calculate_level(points: int) -> int:
    """Calcula el nivel del usuario basado en los puntos."""
    if points >= 1000:
        return 5
    elif points >= 500:
        return 4
    elif points >= 250:
        return 3
    elif points >= 100:
        return 2
    else:
        return 1

def get_level_info(level: int) -> dict:
    """Obtiene información de nivel incluyendo nombre y requisitos."""
    level_data = {
        1: {"name": "Novato Cinéfilo", "min_points": 0, "next_points": 100},
        2: {"name": "Aficionado", "min_points": 100, "next_points": 250},
        3: {"name": "Crítico Amateur", "min_points": 250, "next_points": 500},
        4: {"name": "Experto Cinematográfico", "min_points": 500, "next_points": 1000},
        5: {"name": "Maestro del Séptimo Arte", "min_points": 1000, "next_points": None}
    }

    return level_data.get(level, level_data[1])

def get_user_stats(user_id: int):
    """Obtiene estadísticas completas de un usuario."""
    conn = get_connection()
    cursor = conn.cursor()

    # Get basic user info and totals
    cursor.execute(
        """SELECT COALESCE(SUM(points), 0) as total_points,
                  COUNT(*) as total_contributions,
                  username,
                  MIN(timestamp) as member_since
           FROM points
           WHERE user_id = ?""",
        (user_id,)
    )
    basic_stats = cursor.fetchone()

    if not basic_stats or basic_stats[0] == 0:
        conn.close()
        return None

    total_points, total_contributions, username, member_since = basic_stats
    current_level = calculate_level(total_points)
    level_info = get_level_info(current_level)

    # Calculate points to next level
    points_to_next = 0
    if level_info["next_points"]:
        points_to_next = level_info["next_points"] - total_points

    # Get recent contributions
    cursor.execute(
        """SELECT hashtag, points, timestamp
           FROM points
           WHERE user_id = ?
           ORDER BY timestamp DESC
           LIMIT 5""",
        (user_id,)
    )
    recent_contributions = cursor.fetchall()

    # Get hashtag counts
    cursor.execute(
        """SELECT hashtag, COUNT(*) FROM points
           WHERE user_id = ?
           GROUP BY hashtag
           ORDER BY COUNT(*) DESC""",
        (user_id,)
    )
    hashtag_counts = {row[0]: row[1] for row in cursor.fetchall()}

    # Get active days
    cursor.execute(
        """SELECT DISTINCT DATE(timestamp) FROM points
           WHERE user_id = ?""",
        (user_id,)
    )
    active_days = {row[0] for row in cursor.fetchall()}

    # Get daily challenges this week
    cursor.execute(
        """SELECT COUNT(*) FROM points
           WHERE user_id = ? AND is_challenge_bonus = 1
           AND hashtag = '(reto_diario)'
           AND strftime('%W', timestamp) = strftime('%W', 'now')""",
        (user_id,)
    )
    daily_challenges_week = cursor.fetchone()[0]

    # Check if weekly challenge is done
    cursor.execute(
        """SELECT 1 FROM points
           WHERE user_id = ? AND is_challenge_bonus = 1
           AND hashtag LIKE '#%' AND strftime('%W', timestamp) = strftime('%W', 'now')
           LIMIT 1""",
        (user_id,)
    )
    weekly_done = bool(cursor.fetchone())

    # Get achievements
    cursor.execute(
        """SELECT achievement_id FROM user_achievements
           WHERE user_id = ?""",
        (user_id,)
    )
    achievements = [row[0] for row in cursor.fetchall()]

    conn.close()

    return {
        "username": username,
        "points": total_points,
        "count": total_contributions,
        "level": current_level,
        "level_name": level_info["name"],
        "points_to_next": max(0, points_to_next),
        "recent_contributions": recent_contributions,
        "member_since": member_since,
        "hashtag_counts": hashtag_counts,
        "active_days": active_days,
        "daily_challenges_week": daily_challenges_week,
        "weekly_challenge_done": weekly_done,
        "achievements": achievements
    }

def get_top10():
    """Obtiene los 10 usuarios principales por puntos, incluyendo su nivel."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Obtener usuarios con sus puntos totales y calcular nivel
        cursor.execute("""
            SELECT
                username,
                SUM(points) as total_points,
                user_id
            FROM points
            GROUP BY user_id, username
            ORDER BY total_points DESC
            LIMIT 10
        """)

        results = cursor.fetchall()

        # Agregar nivel calculado a cada usuario
        top_users = []
        for username, total_points, user_id in results:
            level = calculate_level(total_points)
            top_users.append((username, total_points, level))

        return top_users

    except Exception as e:
        logger.error(f"Error en get_top10: {e}") # Usar logger en lugar de print
        return []
    finally:
        conn.close()

def set_chat_config(chat_id: int, chat_name: str, rankings_enabled: bool = True, challenges_enabled: bool = True):
    """Configura los ajustes de un chat."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT OR REPLACE INTO chat_config (chat_id, chat_name, rankings_enabled, challenges_enabled)
           VALUES (?, ?, ?, ?)""",
        (chat_id, chat_name, rankings_enabled, challenges_enabled)
    )
    conn.commit()
    conn.close()
    logger.info(f"Configuración de chat {chat_id} actualizada.")


def get_chat_config(chat_id: int):
    """Obtiene la configuración de un chat."""
    conn = get_connection()
    cursor = conn.cursor()
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
    """Obtiene todos los chats configurados."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT chat_id, chat_name, rankings_enabled, challenges_enabled
           FROM chat_config
           WHERE rankings_enabled = 1 OR challenges_enabled = 1"""
    )
    results = cursor.fetchall()
    conn.close()

    return [
        {
            "chat_id": row[0],
            "chat_name": row[1],
            "rankings_enabled": bool(row[2]),
            "challenges_enabled": bool(row[3])
        }
        for row in results
    ]

# Funciones adicionales que tu bot.py intenta importar (añadidas para completar)
# Si estas funciones no tienen un uso real o no quieres implementarlas,
# deberías eliminarlas de la importación en bot.py.
# Estas son solo funciones dummy para que el bot.py pueda importar.

async def add_user(user_id, username):
    logger.debug(f"Función dummy add_user llamada para {user_id}")
    # Aquí iría tu lógica real para añadir/actualizar un usuario
    pass

async def get_user_by_telegram_id(user_id):
    logger.debug(f"Función dummy get_user_by_telegram_id llamada para {user_id}")
    # Aquí iría tu lógica real para obtener un usuario
    return {"id": user_id, "username": "dummy_user"} # Ejemplo de retorno

async def add_chat(chat_id, title, chat_type):
    logger.debug(f"Función dummy add_chat llamada para {chat_id}")
    # Aquí iría tu lógica real para añadir/actualizar un chat
    pass

async def get_chat_by_telegram_id(chat_id):
    logger.debug(f"Función dummy get_chat_by_telegram_id llamada para {chat_id}")
    # Aquí iría tu lógica real para obtener un chat
    return {"id": chat_id, "title": "dummy_chat"} # Ejemplo de retorno

async def record_message(user_id, chat_id, message_text):
    logger.debug(f"Función dummy record_message llamada por {user_id} en {chat_id}")
    # Aquí iría tu lógica real para registrar mensajes
    pass

async def get_top_users():
    logger.debug("Función dummy get_top_users llamada.")
    # Aquí iría tu lógica real para obtener los top users
    return [] # Ejemplo de retorno

async def get_top_chats():
    logger.debug("Función dummy get_top_chats llamada.")
    # Aquí iría tu lógica real para obtener los top chats
    return [] # Ejemplo de retorno

async def get_bot_stats():
    logger.debug("Función dummy get_bot_stats llamada.")
    # Aquí iría tu lógica real para obtener estadísticas del bot
    return {"users": 0, "chats": 0, "messages": 0} # Ejemplo de retorno

async def update_user_activity(user_id):
    logger.debug(f"Función dummy update_user_activity llamada para {user_id}")
    # Aquí iría tu lógica real para actualizar la actividad del usuario
    pass

async def update_chat_activity(chat_id):
    logger.debug(f"Función dummy update_chat_activity llamada para {chat_id}")
    # Aquí iría tu lógica real para actualizar la actividad del chat
    pass
