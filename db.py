import sqlite3
from datetime import datetime

DB_PATH = "puntum.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def create_tables():
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

    # Create users table if it doesn't exist (for better user management)
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

    # Create chat_config table for chat management
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
    conn.close()

def add_points(user_id, username, points, hashtag=None, message_text=None, chat_id=None, message_id=None, is_challenge_bonus=False, context=None):
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
            from handlers.achievements import check_achievements
            check_achievements(user_id, username, context, chat_id)
        except ImportError:
            pass  # Achievements module is optional

    return {"ok": True}

def add_achievement(user_id: int, achievement_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT OR IGNORE INTO user_achievements (user_id, achievement_id)
           VALUES (?, ?)""",
        (user_id, achievement_id)
    )
    conn.commit()
    conn.close()

def get_user_total_points(user_id: int) -> int:
    """Get total points for a user"""
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
    """Calculate user level based on points"""
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
    """Get level information including name and requirements"""
    level_data = {
        1: {"name": "Novato Cinéfilo", "min_points": 0, "next_points": 100},
        2: {"name": "Aficionado", "min_points": 100, "next_points": 250},
        3: {"name": "Crítico Amateur", "min_points": 250, "next_points": 500},
        4: {"name": "Experto Cinematográfico", "min_points": 500, "next_points": 1000},
        5: {"name": "Maestro del Séptimo Arte", "min_points": 1000, "next_points": None}
    }
    
    return level_data.get(level, level_data[1])

def get_user_stats(user_id: int):
    """Get comprehensive user statistics"""
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
    """Get top 10 users by points including their level"""
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
        print(f"[ERROR] get_top10: {e}")
        return []
    finally:
        conn.close()

def set_chat_config(chat_id: int, chat_name: str, rankings_enabled: bool = True, challenges_enabled: bool = True):
    """Configure chat settings"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT OR REPLACE INTO chat_config (chat_id, chat_name, rankings_enabled, challenges_enabled)
           VALUES (?, ?, ?, ?)""",
        (chat_id, chat_name, rankings_enabled, challenges_enabled)
    )
    conn.commit()
    conn.close()

def get_chat_config(chat_id: int):
    """Get chat configuration"""
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
    """Get all configured chats"""
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
# Agregar estas funciones al final de tu db.py actual

def create_games_tables():
    """Crear tablas necesarias para el sistema de juegos"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Tabla para juegos activos (diccionario en memoria convertido a tabla)
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS active_games (
                chat_id INTEGER PRIMARY KEY,
                game_type TEXT,
                game_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        
        # Tabla para trivias activas
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS active_trivias (
                chat_id INTEGER PRIMARY KEY,
                question TEXT,
                correct_answer TEXT,
                options TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        
        # Tabla para estadísticas de juegos
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS game_stats (
                user_id INTEGER,
                username TEXT,
                game_type TEXT,
                wins INTEGER DEFAULT 0,
                total_games INTEGER DEFAULT 0,
                last_played TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, game_type)
            )"""
        )
        
        conn.commit()
        print("✅ Tablas de juegos creadas exitosamente")
        
    except Exception as e:
        print(f"❌ Error creando tablas de juegos: {e}")
    finally:
        conn.close()

# Modificar tu función create_tables() existente
# Agregar esta línea al final de create_tables():
# create_games_tables()

def create_tables():
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
    conn.close()
    
    # AGREGAR ESTA LÍNEA AL FINAL:
    create_games_tables()