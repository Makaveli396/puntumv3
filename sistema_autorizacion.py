import sqlite3
import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from db import get_connection

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración - Administradores
ADMIN_IDS = {5548909327}  # Cambiar por tus user_ids de Telegram

# Roles disponibles
ROLES = {
    'admin': 'Administrador completo',
    'mod': 'Moderador (gestionar chats)',
    'user': 'Usuario normal'
}

def create_auth_tables():
    """Crear tablas para el sistema de autorización"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # [El contenido de create_auth_tables permanece igual...]
    # ... [mantén todo el código existente de create_auth_tables] ...
    logger.info("✅ Tablas de autorización creadas")

def is_admin(user_id: int) -> bool:
    """Verificar si un usuario es administrador"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM user_roles WHERE user_id = ? AND role = 'admin'",
            (user_id,)
        )
        result = bool(cursor.fetchone())
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Error verificando admin: {e}")
        return False

def is_chat_authorized(chat_id: int) -> bool:
    """Verificar si un chat está autorizado"""
    # Permitir chats privados siempre
    if chat_id > 0:
        return True
        
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM authorized_chats WHERE chat_id = ? AND status = 'active'",
            (chat_id,)
        )
        result = cursor.fetchone()
        conn.close()
        return bool(result)
    except Exception as e:
        logger.error(f"Error verificando autorización: {e}")
        return False

def authorize_chat(chat_id: int, chat_title: str, authorized_by: int):
    """Autorizar un chat"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO authorized_chats 
            (chat_id, chat_title, authorized_by, authorized_at, status)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'active')
        """, (chat_id, chat_title, authorized_by))
        
        cursor.execute("""
            UPDATE auth_requests 
            SET status = 'approved' 
            WHERE chat_id = ? AND status = 'pending'
        """, (chat_id,))
        
        conn.commit()
        conn.close()
        logger.info(f"Chat {chat_id} autorizado exitosamente")
        return True
    except Exception as e:
        logger.error(f"Error autorizando chat: {e}")
        return False

def auth_required(role: str = "user"):
    """Decorador para requerir autorización"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.effective_chat or not update.effective_user:
                return
                
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id
            
            if chat_id < 0 and not is_chat_authorized(chat_id):
                try:
                    await update.message.reply_text(
                        "❌ Este grupo no está autorizado.\n"
                        "📝 Usa /solicitar para pedir autorización."
                    )
                except Exception as e:
                    logger.error(f"Error enviando mensaje de no autorización: {e}")
                return
                
            if not has_permission(user_id, role):
                try:
                    await update.message.reply_text(
                        f"❌ No tienes permiso para este comando.\n"
                        f"Se requiere rol: {ROLES.get(role, role)}"
                    )
                except Exception as e:
                    logger.error(f"Error enviando mensaje de permiso denegado: {e}")
                return
                
            return await func(update, context)
        return wrapper
    return decorator

# [Resto de las funciones (cmd_solicitar_autorizacion, cmd_aprobar_grupo, etc.)...]
# ... [mantén todas las demás funciones que ya tenías] ...

def setup_admin_list(admin_ids: list[int] = None):
    """Configurar lista de administradores iniciales"""
    if admin_ids:
        for admin_id in admin_ids:
            ADMIN_IDS.add(admin_id)
        logger.info(f"Administradores configurados: {ADMIN_IDS}")
