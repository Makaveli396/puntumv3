# db.py
import os
import logging
from datetime import datetime
from contextlib import contextmanager
import psycopg2-binary as psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Configuración para Render con PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Crea una conexión a la base de datos"""
    if DATABASE_URL:
        # Parsear URL de PostgreSQL
        result = urlparse(DATABASE_URL)
        return psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
    else:
        # Fallback para desarrollo local
        import sqlite3
        conn = sqlite3.connect('/tmp/bot_database.db')
        conn.row_factory = sqlite3.Row
        return conn

@contextmanager
def db_session():
    """Manejador de contexto para conexiones a la base de datos"""
    conn = None
    try:
        conn = get_db_connection()
        if DATABASE_URL:  # PostgreSQL
            conn.cursor_factory = RealDictCursor
            cursor = conn.cursor()
        else:  # SQLite
            cursor = conn.cursor()
        
        yield conn
        conn.commit()
    except Exception as e:
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
    
    # Determinar si es PostgreSQL o SQLite
    is_postgresql = DATABASE_URL is not None
    
    if is_postgresql:
        # Migración para PostgreSQL
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_challenges (
                id SERIAL PRIMARY KEY,
                challenge_type VARCHAR(50) NOT NULL,
                challenge_value TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_challenges (
                user_id BIGINT NOT NULL,
                challenge_id INTEGER NOT NULL,
                completed BOOLEAN DEFAULT FALSE,
                completion_date TIMESTAMP,
                PRIMARY KEY (user_id, challenge_id),
                FOREIGN KEY (challenge_id) REFERENCES weekly_challenges(id)
            )
        """)
    else:
        # Migración para SQLite (desarrollo)
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

    logger.info("Migraciones aplicadas correctamente")

def initialize_db():
    """Inicializa la base de datos con todas las tablas necesarias"""
    with db_session() as conn:
        try:
            cursor = conn.cursor()
            is_postgresql = DATABASE_URL is not None

            if is_postgresql:
                # Tablas para PostgreSQL
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS points (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        username VARCHAR(255),
                        points INTEGER NOT NULL,
                        hashtag VARCHAR(100),
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        chat_id BIGINT,
                        message_id INTEGER,
                        is_challenge_bonus BOOLEAN DEFAULT FALSE
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_achievements (
                        user_id BIGINT NOT NULL,
                        achievement_id INTEGER NOT NULL,
                        date DATE DEFAULT CURRENT_DATE,
                        PRIMARY KEY (user_id, achievement_id)
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id BIGINT PRIMARY KEY,
                        username VARCHAR(255),
                        points INTEGER DEFAULT 0,
                        count INTEGER DEFAULT 0,
                        level INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_config (
                        chat_id BIGINT PRIMARY KEY,
                        chat_name VARCHAR(255),
                        rankings_enabled BOOLEAN DEFAULT TRUE,
                        challenges_enabled BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Índices para PostgreSQL
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_points_user ON points(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_points_hashtag ON points(hashtag)")
                
            else:
                # Tablas para SQLite (desarrollo local)
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

                # Índices para SQLite
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_points_user ON points(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_points_hashtag ON points(hashtag)")

            # Aplicar migraciones
            apply_migrations(conn)
            
            logger.info("Base de datos inicializada correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar DB: {e}")
            raise

# Funciones principales (adaptadas para ambas DB)
def add_points(user_id, username, points, hashtag=None, message_text=None, chat_id=None, message_id=None, is_challenge_bonus=False, context=None):
    """Añade puntos a un usuario"""
    with db_session() as conn:
        cursor = conn.cursor()
        is_postgresql = DATABASE_URL is not None
        
        # Insertar puntos
        if is_postgresql:
            cursor.execute("""
                INSERT INTO points (user_id, username, points, hashtag, chat_id, message_id, is_challenge_bonus)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, username, points, hashtag, chat_id, message_id, is_challenge_bonus))
            
            # Actualizar usuario en PostgreSQL
            cursor.execute("""
                INSERT INTO users (id, username, points, count, level)
                VALUES (%s, %s, %s, 1, %s)
                ON CONFLICT (id) DO UPDATE SET
                    username = EXCLUDED.username,
                    points = users.points + %s,
                    count = users.count + 1,
                    level = %s
            """, (user_id, username, points, calculate_level(get_user_total_points(user_id) + points), points, calculate_level(get_user_total_points(user_id) + points)))
        else:
            cursor.execute("""
                INSERT INTO points (user_id, username, points, hashtag, chat_id, message_id, is_challenge_bonus)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, points, hashtag, chat_id, message_id, int(is_challenge_bonus)))

            # Actualizar usuario en SQLite
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
        is_postgresql = DATABASE_URL is not None
        
        if is_postgresql:
            cursor.execute("""
                INSERT INTO user_achievements (user_id, achievement_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, achievement_id) DO NOTHING
            """, (user_id, achievement_id))
        else:
            cursor.execute("""
                INSERT OR IGNORE INTO user_achievements (user_id, achievement_id)
                VALUES (?, ?)
            """, (user_id, achievement_id))
        
        logger.info(f"Logro {achievement_id} añadido al usuario {user_id}")

def get_user_total_points(user_id: int) -> int:
    """Obtiene los puntos totales de un usuario"""
    with db_session() as conn:
        cursor = conn.cursor()
        is_postgresql = DATABASE_URL is not None
        
        if is_postgresql:
            cursor.execute("""
                SELECT COALESCE(SUM(points), 0) FROM points WHERE user_id = %s
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT COALESCE(SUM(points), 0) FROM points WHERE user_id = ?
            """, (user_id,))
        
        result = cursor.fetchone()
        return result[0] if result else 0

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

def get_user_stats(user_id: int):
    """Obtiene estadísticas completas del usuario"""
    with db_session() as conn:
        cursor = conn.cursor()
        is_postgresql = DATABASE_URL is not None
        
        # Datos básicos
        if is_postgresql:
            cursor.execute("""
                SELECT COALESCE(SUM(points), 0) as total_points,
                      COUNT(*) as total_contributions,
                      username,
                      MIN(timestamp) as member_since
                FROM points WHERE user_id = %s
            """, (user_id,))
        else:
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
            "username": result[2] if is_postgresql else result["username"],
            "points": result[0] if is_postgresql else result["total_points"],
            "count": result[1] if is_postgresql else result["total_contributions"],
            "member_since": str(result[3] if is_postgresql else result["member_since"]),
            "level": calculate_level(result[0] if is_postgresql else result["total_points"]),
            "hashtag_counts": {},
            "active_days": set(),
            "achievements": []
        }

        # Información de nivel
        level_info = get_level_info(stats["level"])
        stats["level_name"] = level_info["name"]
        stats["points_to_next"] = max(0, level_info["next_points"] - stats["points"]) if level_info["next_points"] else 0

        # Hashtags más usados
        if is_postgresql:
            cursor.execute("""
                SELECT hashtag, COUNT(*) as count FROM points
                WHERE user_id = %s GROUP BY hashtag ORDER BY count DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT hashtag, COUNT(*) as count FROM points
                WHERE user_id = ? GROUP BY hashtag ORDER BY count DESC
            """, (user_id,))
        
        stats["hashtag_counts"] = {row[0]: row[1] for row in cursor.fetchall()}

        # Días activos
        if is_postgresql:
            cursor.execute("SELECT DISTINCT DATE(timestamp) FROM points WHERE user_id = %s", (user_id,))
        else:
            cursor.execute("SELECT DISTINCT DATE(timestamp) FROM points WHERE user_id = ?", (user_id,))
        
        stats["active_days"] = {str(row[0]) for row in cursor.fetchall()}

        # Logros
        if is_postgresql:
            cursor.execute("SELECT achievement_id FROM user_achievements WHERE user_id = %s", (user_id,))
        else:
            cursor.execute("SELECT achievement_id FROM user_achievements WHERE user_id = ?", (user_id,))
        
        stats["achievements"] = [row[0] for row in cursor.fetchall()]

        return stats

def get_top10():
    """Obtiene el top 10 de usuarios"""
    with db_session() as conn:
        cursor = conn.cursor()
        is_postgresql = DATABASE_URL is not None
        
        try:
            if is_postgresql:
                cursor.execute("""
                    SELECT username, SUM(points) as total_points, user_id
                    FROM points GROUP BY user_id, username ORDER BY total_points DESC LIMIT 10
                """)
            else:
                cursor.execute("""
                    SELECT username, SUM(points) as total_points, user_id
                    FROM points GROUP BY user_id ORDER BY total_points DESC LIMIT 10
                """)
            
            results = cursor.fetchall()
            return [
                (row[0], row[1], calculate_level(row[1]))
                for row in results
            ]
        except Exception as e:
            logger.error(f"Error en get_top10: {e}")
            return []

def get_configured_chats():
    """Obtiene chats configurados"""
    with db_session() as conn:
        cursor = conn.cursor()
        is_postgresql = DATABASE_URL is not None
        
        if is_postgresql:
            cursor.execute("""
                SELECT chat_id, chat_name, rankings_enabled, challenges_enabled
                FROM chat_config WHERE rankings_enabled = TRUE OR challenges_enabled = TRUE
            """)
        else:
            cursor.execute("""
                SELECT chat_id, chat_name, rankings_enabled, challenges_enabled
                FROM chat_config WHERE rankings_enabled = 1 OR challenges_enabled = 1
            """)
        
        return [{
            "chat_id": row[0],
            "chat_name": row[1],
            "rankings_enabled": bool(row[2]),
            "challenges_enabled": bool(row[3])
        } for row in cursor.fetchall()]
