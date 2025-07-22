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
