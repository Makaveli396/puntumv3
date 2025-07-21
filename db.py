# db.py
import sqlite3
from datetime import datetime
import logging
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Configuración para Render
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///tmp/bot_database.db')

@contextmanager
def db_session():
    """Manejador de contexto para conexiones a la base de datos"""
    conn = None
    try:
        if DATABASE_URL.startswith('sqlite:///'):
            db_path = DATABASE_URL.split('sqlite:///')[1]
            conn = sqlite3.connect(f'/tmp/{db_path}')
        else:
            conn = sqlite3.connect(DATABASE_URL)
        
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error en la sesión de DB: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def apply_migrations(conn):
    """Aplica migraciones necesarias a la base de datos"""
    cursor = conn.cursor()
    
    # Migración para la tabla de retos semanales
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='weekly_challenges'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE weekly_challenges (
                id INTEGER PRIMARY KEY,
                challenge_type TEXT NOT NULL,
                challenge_value TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        logger.info("Tabla weekly_challenges creada")

    # Migración para user_challenges
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_challenges'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE user_challenges (
                user_id INTEGER NOT NULL,
                challenge_id INTEGER NOT NULL,
                completed BOOLEAN DEFAULT 0,
                completion_date TEXT,
                PRIMARY KEY (user_id, challenge_id),
                FOREIGN KEY (challenge_id) REFERENCES weekly_challenges(id)
            )
        """)
        logger.info("Tabla user_challenges creada")

    # Verificar columnas faltantes en points
    cursor.execute("PRAGMA table_info(points)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'is_challenge_bonus' not in columns:
        cursor.execute("ALTER TABLE points ADD COLUMN is_challenge_bonus INTEGER DEFAULT 0")
        logger.info("Columna is_challenge_bonus añadida a points")

def initialize_db():
    """Inicializa la base de datos con todas las tablas necesarias"""
    with db_session() as conn:
        try:
            cursor = conn.cursor()

            # Tablas principales
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS points (
                    user_id INTEGER,
                    username TEXT,
                    points INTEGER,
                    hashtag TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    chat_id INTEGER,
                    message_id INTEGER,
                    is_challenge_bonus INTEGER DEFAULT 0
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id INTEGER,
                    achievement_id INTEGER,
                    date TEXT DEFAULT CURRENT_DATE,
                    PRIMARY KEY (user_id, achievement_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    points INTEGER DEFAULT 0,
                    count INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_config (
                    chat_id INTEGER PRIMARY KEY,
                    chat_name TEXT,
                    rankings_enabled BOOLEAN DEFAULT 1,
                    challenges_enabled BOOLEAN DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Aplicar migraciones
            apply_migrations(conn)

            # Índices para mejorar rendimiento
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_points_user ON points(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_points_hashtag ON points(hashtag)")
            
            logger.info("Base de datos inicializada correctamente")
        except sqlite3.Error as e:
            logger.error(f"Error al inicializar DB: {e}")
            raise

# Funciones principales con el nuevo manejador de contexto
def add_points(user_id, username, points, hashtag=None, message_text=None, chat_id=None, message_id=None, is_challenge_bonus=False, context=None):
    """Añade puntos a un usuario"""
    with db_session() as conn:
        cursor = conn.cursor()
        
        # Insertar puntos
        cursor.execute("""
            INSERT INTO points (user_id, username, points, hashtag, chat_id, message_id, is_challenge_bonus)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, points, hashtag, chat_id, message_id, int(is_challenge_bonus)))

        # Actualizar usuario
        cursor.execute("""
            INSERT OR REPLACE INTO users (id, username, points, count, level, created_at)
            VALUES (?, ?, 
                   COALESCE((SELECT points FROM users WHERE id = ?), 0) + ?,
                   COALESCE((SELECT count FROM users WHERE id = ?), 0) + 1,
                   ?,
                   COALESCE((SELECT created_at FROM users WHERE id = ?), CURRENT_TIMESTAMP))
        """, (user_id, username, user_id, points, user_id, calculate_level(get_user_total_points(user_id) + points), user_id))

        logger.info(f"Puntos añadidos: {user_id} +{points} por {hashtag}")

def add_achievement(user_id: int, achievement_id: int):
    """Añade un logro a un usuario"""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO user_achievements (user_id, achievement_id)
            VALUES (?, ?)
        """, (user_id, achievement_id))
        logger.info(f"Logro {achievement_id} añadido al usuario {user_id}")

def get_user_total_points(user_id: int) -> int:
    """Obtiene los puntos totales de un usuario"""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(points), 0) FROM points WHERE user_id = ?
        """, (user_id,))
        return cursor.fetchone()[0]

# Funciones de nivel (sin cambios)
def calculate_level(points: int) -> int:
    if points >= 1000: return 5
    elif points >= 500: return 4
    elif points >= 250: return 3
    elif points >= 100: return 2
    else: return 1

def get_level_info(level: int) -> dict:
    level_data = {
        1: {"name": "Novato Cinéfilo", "min_points": 0, "next_points": 100},
        2: {"name": "Aficionado", "min_points": 100, "next_points": 250},
        3: {"name": "Crítico Amateur", "min_points": 250, "next_points": 500},
        4: {"name": "Experto Cinematográfico", "min_points": 500, "next_points": 1000},
        5: {"name": "Maestro del Séptimo Arte", "min_points": 1000, "next_points": None}
    }
    return level_data.get(level, level_data[1])

# Funciones optimizadas con el nuevo manejador
def get_user_stats(user_id: int):
    """Obtiene estadísticas completas del usuario"""
    with db_session() as conn:
        cursor = conn.cursor()
        
        # Datos básicos
        cursor.execute("""
            SELECT COALESCE(SUM(points), 0) as total_points,
                  COUNT(*) as total_contributions,
                  username,
                  MIN(timestamp) as member_since
            FROM points WHERE user_id = ?
        """, (user_id,))
        result = cursor.fetchone()

        if not result or result[0] == 0:
            return None

        stats = {
            "username": result["username"],
            "points": result["total_points"],
            "count": result["total_contributions"],
            "member_since": result["member_since"],
            "level": calculate_level(result["total_points"]),
            "hashtag_counts": {},
            "active_days": set(),
            "achievements": []
        }

        # Información de nivel
        level_info = get_level_info(stats["level"])
        stats["level_name"] = level_info["name"]
        stats["points_to_next"] = max(0, level_info["next_points"] - stats["points"]) if level_info["next_points"] else 0

        # Hashtags más usados
        cursor.execute("""
            SELECT hashtag, COUNT(*) as count FROM points
            WHERE user_id = ? GROUP BY hashtag ORDER BY count DESC
        """, (user_id,))
        stats["hashtag_counts"] = {row["hashtag"]: row["count"] for row in cursor.fetchall()}

        # Días activos
        cursor.execute("SELECT DISTINCT DATE(timestamp) FROM points WHERE user_id = ?", (user_id,))
        stats["active_days"] = {row[0] for row in cursor.fetchall()}

        # Logros
        cursor.execute("SELECT achievement_id FROM user_achievements WHERE user_id = ?", (user_id,))
        stats["achievements"] = [row["achievement_id"] for row in cursor.fetchall()]

        return stats

def get_top10():
    """Obtiene el top 10 de usuarios"""
    with db_session() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT username, SUM(points) as total_points, user_id
                FROM points GROUP BY user_id ORDER BY total_points DESC LIMIT 10
            """)
            return [
                (row["username"], row["total_points"], calculate_level(row["total_points"]))
                for row in cursor.fetchall()
            ]
        except sqlite3.Error as e:
            logger.error(f"Error en get_top10: {e}")
            return []

# Funciones de configuración de chat
def set_chat_config(chat_id: int, chat_name: str, rankings_enabled: bool = True, challenges_enabled: bool = True):
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO chat_config 
            (chat_id, chat_name, rankings_enabled, challenges_enabled)
            VALUES (?, ?, ?, ?)
        """, (chat_id, chat_name, rankings_enabled, challenges_enabled))

def get_chat_config(chat_id: int):
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT chat_name, rankings_enabled, challenges_enabled
            FROM chat_config WHERE chat_id = ?
        """, (chat_id,))
        result = cursor.fetchone()
        return {
            "chat_name": result["chat_name"],
            "rankings_enabled": bool(result["rankings_enabled"]),
            "challenges_enabled": bool(result["challenges_enabled"])
        } if result else None

def get_configured_chats():
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT chat_id, chat_name, rankings_enabled, challenges_enabled
            FROM chat_config WHERE rankings_enabled = 1 OR challenges_enabled = 1
        """)
        return [{
            "chat_id": row["chat_id"],
            "chat_name": row["chat_name"],
            "rankings_enabled": bool(row["rankings_enabled"]),
            "challenges_enabled": bool(row["challenges_enabled"])
        } for row in cursor.fetchall()]
