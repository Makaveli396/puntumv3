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
    
    # Tabla de chats autorizados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authorized_chats (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT,
            authorized_by INTEGER,
            authorized_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    """)
    
    # Tabla de solicitudes
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
    
    # Tabla de roles de usuario
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER PRIMARY KEY,
            role TEXT NOT NULL DEFAULT 'user',
            granted_by INTEGER,
            granted_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla de logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insertar admin principal si no existe
    for admin_id in ADMIN_IDS:
        cursor.execute("""
            INSERT OR IGNORE INTO user_roles (user_id, role) 
            VALUES (?, 'admin')
        """, (admin_id,))
    
    conn.commit()
    conn.close()
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

def add_admin(user_id: int, added_by: int):
    """Agregar un nuevo administrador"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO user_roles (user_id, role, granted_by)
            VALUES (?, 'admin', ?)
        """, (user_id, added_by))
        conn.commit()
        conn.close()
        
        ADMIN_IDS.add(user_id)
        log_auth_action("add_admin", added_by, user_id)
        logger.info(f"Nuevo administrador agregado: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error agregando admin: {e}")
        return False

def remove_admin(user_id: int, removed_by: int):
    """Remover un administrador"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM user_roles 
            WHERE user_id = ? AND role = 'admin'
        """, (user_id,))
        conn.commit()
        conn.close()
        
        ADMIN_IDS.discard(user_id)
        log_auth_action("remove_admin", removed_by, user_id)
        logger.info(f"Administrador removido: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error removiendo admin: {e}")
        return False

def has_permission(user_id: int, required_role: str = "user") -> bool:
    """Verificar si usuario tiene el rol requerido"""
    if required_role == "user":
        return True
        
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Obtener rol del usuario
        cursor.execute(
            "SELECT role FROM user_roles WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
            
        user_role = result[0]
        
        # Jerarquía de roles
        role_hierarchy = ['admin', 'mod', 'user']
        return role_hierarchy.index(user_role) <= role_hierarchy.index(required_role)
        
    except Exception as e:
        logger.error(f"Error verificando permisos: {e}")
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
        
        # Marcar solicitud como aprobada
        cursor.execute("""
            UPDATE auth_requests 
            SET status = 'approved' 
            WHERE chat_id = ? AND status = 'pending'
        """, (chat_id,))
        
        conn.commit()
        conn.close()
        
        log_auth_action("authorize_chat", authorized_by, chat_id, f"Chat: {chat_title}")
        logger.info(f"Chat {chat_id} autorizado exitosamente")
        return True
    except Exception as e:
        logger.error(f"Error autorizando chat: {e}")
        return False

def revoke_chat_authorization(chat_id: int, revoked_by: int):
    """Revocar autorización de un chat"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE authorized_chats 
            SET status = 'revoked', authorized_by = ?
            WHERE chat_id = ?
        """, (revoked_by, chat_id))
        
        conn.commit()
        conn.close()
        
        log_auth_action("revoke_chat", revoked_by, chat_id)
        logger.info(f"Chat {chat_id} revocado exitosamente")
        return True
    except Exception as e:
        logger.error(f"Error revocando chat: {e}")
        return False

def log_auth_action(action: str, user_id: int, target_id: int, details: str = ""):
    """Registrar acción de autorización"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO auth_logs (action, user_id, target_id, details)
            VALUES (?, ?, ?, ?)
        """, (action, user_id, target_id, details))
        
        conn.commit()
        conn.close()
        logger.info(f"Auth action: {action} by {user_id} on {target_id}")
    except Exception as e:
        logger.error(f"Error registrando acción: {e}")

def auth_required(role: str = "user"):
    """Decorador para requerir autorización"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.effective_chat or not update.effective_user:
                return
                
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id
            
            # Verificar autorización del chat
            if chat_id < 0 and not is_chat_authorized(chat_id):
                try:
                    await update.message.reply_text(
                        "❌ Este grupo no está autorizado para usar el bot.\n"
                        "📝 Usa /solicitar para pedir autorización."
                    )
                except Exception as e:
                    logger.error(f"Error enviando mensaje de no autorización: {e}")
                return
                
            # Verificar rol del usuario
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

# ... (resto de las funciones existentes como cmd_solicitar_autorizacion, cmd_aprobar_grupo, etc.) ...

# Comandos administrativos adicionales
async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Agregar nuevo administrador"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Solo administradores pueden usar este comando.")
        return
        
    if not context.args:
        await update.message.reply_text("📝 Uso: /addadmin <user_id>")
        return
        
    try:
        new_admin_id = int(context.args[0])
        if add_admin(new_admin_id, user.id):
            await update.message.reply_text(f"✅ Usuario {new_admin_id} agregado como administrador.")
        else:
            await update.message.reply_text("❌ Error al agregar administrador.")
    except ValueError:
        await update.message.reply_text("❌ ID de usuario inválido.")

async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remover administrador"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Solo administradores pueden usar este comando.")
        return
        
    if not context.args:
        await update.message.reply_text("📝 Uso: /removeadmin <user_id>")
        return
        
    try:
        admin_id = int(context.args[0])
        if admin_id == user.id:
            await update.message.reply_text("❌ No puedes removerte a ti mismo.")
            return
            
        if remove_admin(admin_id, user.id):
            await update.message.reply_text(f"✅ Usuario {admin_id} removido como administrador.")
        else:
            await update.message.reply_text("❌ Error al remover administrador.")
    except ValueError:
        await update.message.reply_text("❌ ID de usuario inválido.")

async def cmd_listadmins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listar administradores"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, role, granted_by, granted_at 
            FROM user_roles 
            WHERE role IN ('admin', 'mod')
            ORDER BY role, granted_at
        """)
        
        admins = cursor.fetchall()
        conn.close()
        
        if not admins:
            await update.message.reply_text("❌ No hay administradores registrados.")
            return
            
        message = "👥 **Lista de Administradores**\n\n"
        for user_id, role, granted_by, granted_at in admins:
            message += (
                f"🆔 `{user_id}`\n"
                f"🎖️ {ROLES.get(role, role)}\n"
                f"👤 Otorgado por: {granted_by}\n"
                f"📅 {granted_at}\n\n"
            )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error listando admins: {e}")
        await update.message.reply_text("❌ Error obteniendo lista de administradores.")

async def cmd_revocar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Revocar autorización de un grupo"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Solo administradores pueden usar este comando.")
        return
        
    if not context.args:
        await update.message.reply_text("📝 Uso: /revocar <chat_id>")
        return
        
    try:
        chat_id = int(context.args[0])
        if revoke_chat_authorization(chat_id, user.id):
            await update.message.reply_text(f"✅ Chat {chat_id} revocado exitosamente.")
        else:
            await update.message.reply_text("❌ Error al revocar chat.")
    except ValueError:
        await update.message.reply_text("❌ ID de chat inválido.")

# Función para configurar administradores iniciales
def setup_admin_list(admin_ids: list[int] = None):
    """Configurar lista de administradores iniciales"""
    if admin_ids:
        for admin_id in admin_ids:
            ADMIN_IDS.add(admin_id)
        logger.info(f"Administradores configurados: {ADMIN_IDS}")
