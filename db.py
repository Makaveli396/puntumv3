import sqlite3
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
DB_PATH = "puntum.db"

def get_connection():
    """Obtener conexión a la base de datos con manejo de errores"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")  # Habilitar claves foráneas
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error conectando a la base de datos: {e}")
        raise

def add_points_safe(user_id, username, points, hashtag=None, message_text=None, 
                   chat_id=None, message_id=None, is_challenge_bonus=False, context=None):
    """Versión segura de add_points con mejor manejo de errores"""
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
        cursor.execute("COMMIT")
        
        logger.info(f"Puntos agregados: {username} (+{points}) = {new_total} puntos")
        
        # Verificar logros después de la transacción exitosa
        if context and chat_id:
            try:
                from handlers.achievements import check_achievements
                check_achievements(user_id, username, context, chat_id)
            except ImportError:
                logger.warning("Módulo de logros no encontrado")
        
        return {"ok": True, "new_total": new_total, "level": new_level}

    except sqlite3.Error as e:
        logger.error(f"Error en base de datos al agregar puntos: {e}")
        if conn:
            cursor.execute("ROLLBACK")
        return {"ok": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error inesperado al agregar puntos: {e}")
        if conn:
            cursor.execute("ROLLBACK")
        return {"ok": False, "error": "Error interno"}
    finally:
        if conn:
            conn.close()

def get_user_total_points_internal(cursor, user_id: int) -> int:
    """Obtener puntos totales usando cursor existente"""
    cursor.execute(
        """SELECT COALESCE(SUM(points), 0) FROM points WHERE user_id = ?""",
        (user_id,)
    )
    result = cursor.fetchone()
    return result[0] if result else 0

def backup_database():
    """Crear respaldo de la base de datos"""
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

def verify_database_integrity():
    """Verificar integridad de la base de datos"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verificar integridad
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        
        if result[0] == "ok":
            logger.info("Base de datos íntegra")
            return True
        else:
            logger.error(f"Problema de integridad: {result[0]}")
            return False
            
    except Exception as e:
        logger.error(f"Error verificando integridad: {e}")
        return False
    finally:
        if conn:
            conn.close()
