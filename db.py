import sqlite3
from datetime import datetime
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)
DB_PATH = "puntum.db"

def get_connection() -> sqlite3.Connection:
    """Obtener conexión a la base de datos con manejo de errores
    
    Returns:
        sqlite3.Connection: Conexión a la base de datos
        
    Raises:
        sqlite3.Error: Si hay un error al conectar
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")  # Habilitar claves foráneas
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error conectando a la base de datos: {e}")
        raise

def calculate_level(points: int) -> int:
    """Calcula el nivel basado en los puntos acumulados
    
    Args:
        points: Puntos totales acumulados
        
    Returns:
        Nivel calculado
    """
    # Implementación básica - ajusta según tus necesidades
    return points // 100 if points > 0 else 0

def add_points_safe(user_id: int, username: str, points: int, hashtag: Optional[str] = None, 
                   message_text: Optional[str] = None, chat_id: Optional[int] = None, 
                   message_id: Optional[int] = None, is_challenge_bonus: bool = False, 
                   context: Optional[Any] = None) -> Dict[str, Any]:
    """Versión segura de add_points con mejor manejo de errores
    
    Args:
        user_id: ID del usuario
        username: Nombre del usuario
        points: Puntos a añadir
        hashtag: Hashtag asociado (opcional)
        message_text: Texto del mensaje (opcional)
        chat_id: ID del chat (opcional)
        message_id: ID del mensaje (opcional)
        is_challenge_bonus: Si es un bono de desafío
        context: Contexto del bot (opcional)
        
    Returns:
        Dict con resultado de la operación:
        {
            "ok": bool, 
            "new_total": int, 
            "level": int,
            "error": str (solo si ok=False)
        }
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Iniciar transacción
        cursor.execute("BEGIN TRANSACTION")
        
        # Insertar puntos
        cursor.execute(
            """INSERT INTO points (user_id, username, points, hashtag, chat_id, message_id, is_challenge_bonus)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, username, points, hashtag, chat_id, message_id, int(is_challenge_bonus))
        )

        # Obtener puntos actuales del usuario
        current_points = get_user_total_points_internal(cursor, user_id)
        new_total = current_points + points
        new_level = calculate_level(new_total)

        # Actualizar tabla de usuarios
        cursor.execute(
            """INSERT OR REPLACE INTO users (id, username, points, count, level, created_at)
               VALUES (?, ?, ?, 
                       COALESCE((SELECT count FROM users WHERE id = ?), 0) + 1,
                       ?, 
                       COALESCE((SELECT created_at FROM users WHERE id = ?), CURRENT_TIMESTAMP))""",
            (user_id, username, new_total, user_id, new_level, user_id)
        )

        # Confirmar transacción
        conn.commit()
        
        logger.info(f"Puntos agregados: {username} (+{points}) = {new_total} puntos")
        
        # Verificar logros después de la transacción exitosa
        if context and chat_id:
            try:
                from handlers.achievements import check_achievements
                check_achievements(user_id, username, context, chat_id)
            except ImportError:
                logger.warning("Módulo de logros no encontrado")
            except Exception as e:
                logger.error(f"Error verificando logros: {e}")
        
        return {"ok": True, "new_total": new_total, "level": new_level}

    except sqlite3.Error as e:
        logger.error(f"Error en base de datos al agregar puntos: {e}")
        if conn:
            conn.rollback()
        return {"ok": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error inesperado al agregar puntos: {e}")
        if conn:
            conn.rollback()
        return {"ok": False, "error": "Error interno"}
    finally:
        if conn:
            conn.close()

def get_user_total_points_internal(cursor: sqlite3.Cursor, user_id: int) -> int:
    """Obtener puntos totales usando cursor existente
    
    Args:
        cursor: Cursor activo de la base de datos
        user_id: ID del usuario
        
    Returns:
        Puntos totales acumulados por el usuario
    """
    cursor.execute(
        """SELECT COALESCE(SUM(points), 0) FROM points WHERE user_id = ?""",
        (user_id,)
    )
    result = cursor.fetchone()
    return result[0] if result else 0

def backup_database() -> Optional[str]:
    """Crear respaldo de la base de datos
    
    Returns:
        str: Ruta del archivo de respaldo o None si falla
    """
    try:
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"puntum_backup_{timestamp}.db"
        
        shutil.copy2(DB_PATH, backup_path)
        logger.info(f"Respaldo creado: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Error creando respaldo: {e}")
        return None

def verify_database_integrity() -> bool:
    """Verificar integridad de la base de datos
    
    Returns:
        bool: True si la base de datos está íntegra, False si no
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verificar integridad
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        
        if result and result[0] == "ok":
            logger.info("Base de datos íntegra")
            return True
        else:
            logger.error(f"Problema de integridad: {result[0] if result else 'No result'}")
            return False
            
    except Exception as e:
        logger.error(f"Error verificando integridad: {e}")
        return False
    finally:
        if conn:
            conn.close()
# Agregar estas funciones a tu archivo db.py

def create_tables():
    """Crear las tablas necesarias para el bot"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Tabla de usuarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                points INTEGER DEFAULT 0,
                count INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de puntos (historial)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                points INTEGER NOT NULL,
                hashtag TEXT,
                chat_id INTEGER,
                message_id INTEGER,
                is_challenge_bonus BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Tabla de juegos (si la necesitas)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                game_type TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                data TEXT,  -- JSON data para el estado del juego
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        logger.info("✅ Tablas creadas correctamente")
        
    except sqlite3.Error as e:
        logger.error(f"Error creando tablas: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def add_points(user_id: int, username: str, points: int, hashtag: Optional[str] = None, 
               message_text: Optional[str] = None, chat_id: Optional[int] = None, 
               message_id: Optional[int] = None, is_challenge_bonus: bool = False, 
               context: Optional[Any] = None) -> Dict[str, Any]:
    """Wrapper para add_points_safe para mantener compatibilidad"""
    return add_points_safe(
        user_id=user_id,
        username=username,
        points=points,
        hashtag=hashtag,
        message_text=message_text,
        chat_id=chat_id,
        message_id=message_id,
        is_challenge_bonus=is_challenge_bonus,
        context=context
    )

def get_user_stats(user_id: int) -> Optional[Dict[str, Any]]:
    """Obtener estadísticas de un usuario
    
    Args:
        user_id: ID del usuario
        
    Returns:
        Dict con estadísticas del usuario o None si no existe
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Obtener datos del usuario
        cursor.execute(
            """SELECT id, username, points, count, level, created_at 
               FROM users WHERE id = ?""",
            (user_id,)
        )
        user_data = cursor.fetchone()
        
        if not user_data:
            return None
        
        # Obtener estadísticas adicionales
        cursor.execute(
            """SELECT COUNT(*) as total_activities,
                      MAX(points) as max_points_single,
                      COUNT(DISTINCT hashtag) as unique_hashtags
               FROM points WHERE user_id = ? AND hashtag IS NOT NULL""",
            (user_id,)
        )
        stats = cursor.fetchone()
        
        return {
            "id": user_data[0],
            "username": user_data[1],
            "total_points": user_data[2],
            "activity_count": user_data[3],
            "level": user_data[4],
            "created_at": user_data[5],
            "total_activities": stats[0] if stats else 0,
            "max_points_single": stats[1] if stats else 0,
            "unique_hashtags": stats[2] if stats else 0
        }
        
    except sqlite3.Error as e:
        logger.error(f"Error obteniendo estadísticas del usuario {user_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_top10() -> list:
    """Obtener top 10 usuarios por puntos
    
    Returns:
        Lista de usuarios ordenados por puntos (descendente)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT username, points, level, count
               FROM users 
               ORDER BY points DESC, level DESC 
               LIMIT 10"""
        )
        
        results = cursor.fetchall()
        
        return [
            {
                "username": row[0],
                "points": row[1],
                "level": row[2],
                "count": row[3],
                "rank": i + 1
            }
            for i, row in enumerate(results)
        ]
        
    except sqlite3.Error as e:
        logger.error(f"Error obteniendo top 10: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_user_total_points(user_id: int) -> int:
    """Obtener puntos totales de un usuario (versión pública)
    
    Args:
        user_id: ID del usuario
        
    Returns:
        Puntos totales del usuario
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        return get_user_total_points_internal(cursor, user_id)
    except sqlite3.Error as e:
        logger.error(f"Error obteniendo puntos del usuario {user_id}: {e}")
        return 0
    finally:
        if conn:
            conn.close()
