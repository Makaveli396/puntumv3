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
            chat_title TEXT NOT NULL,
            authorized_by INTEGER NOT NULL,
            authorized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    """)
    
    # Tabla de solicitudes de autorización
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            chat_title TEXT NOT NULL,
            requested_by INTEGER NOT NULL,
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """)
    
    # Tabla de roles de usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER PRIMARY KEY,
            role TEXT DEFAULT 'user',
            assigned_by INTEGER,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insertar administradores iniciales
    for admin_id in ADMIN_IDS:
        cursor.execute("""
            INSERT OR IGNORE INTO user_roles (user_id, role, assigned_by)
            VALUES (?, 'admin', ?)
        """, (admin_id, admin_id))
    
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

def has_permission(user_id: int, required_role: str) -> bool:
    """Verificar si un usuario tiene el permiso necesario"""
    if required_role == "user":
        return True
        
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role FROM user_roles WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
            
        user_role = result[0]
        
        # Jerarquía de permisos
        role_hierarchy = {'user': 0, 'mod': 1, 'admin': 2}
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
        
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

# ========================================
# COMANDOS DE AUTORIZACIÓN
# ========================================

async def cmd_solicitar_autorizacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Solicitar autorización para un grupo"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("❌ Este comando solo funciona en grupos.")
        return
        
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title
    user_id = update.effective_user.id
    
    # Verificar si ya está autorizado
    if is_chat_authorized(chat_id):
        await update.message.reply_text("✅ Este grupo ya está autorizado.")
        return
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verificar si ya hay una solicitud pendiente
        cursor.execute(
            "SELECT 1 FROM auth_requests WHERE chat_id = ? AND status = 'pending'",
            (chat_id,)
        )
        
        if cursor.fetchone():
            await update.message.reply_text("⏳ Ya existe una solicitud pendiente para este grupo.")
            conn.close()
            return
        
        # Crear nueva solicitud
        cursor.execute("""
            INSERT INTO auth_requests (chat_id, chat_title, requested_by)
            VALUES (?, ?, ?)
        """, (chat_id, chat_title, user_id))
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            "📋 Solicitud de autorización enviada.\n"
            "⏳ Espera a que un administrador la apruebe."
        )
        
        # Notificar a administradores
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"🔔 Nueva solicitud de autorización:\n"
                    f"Grupo: {chat_title}\n"
                    f"ID: {chat_id}\n"
                    f"Solicitado por: @{update.effective_user.username or 'Usuario'}\n"
                    f"Usa /solicitudes para ver todas."
                )
            except:
                pass
        
    except Exception as e:
        logger.error(f"Error procesando solicitud: {e}")
        await update.message.reply_text("❌ Error procesando la solicitud.")

async def cmd_aprobar_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aprobar un grupo (solo admins)"""
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: /aprobar <chat_id>\n"
            "Usa /solicitudes para ver solicitudes pendientes."
        )
        return
    
    try:
        chat_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID de chat inválido.")
        return
    
    user_id = update.effective_user.id
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Obtener información de la solicitud
        cursor.execute(
            "SELECT chat_title FROM auth_requests WHERE chat_id = ? AND status = 'pending'",
            (chat_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            await update.message.reply_text("❌ No hay solicitud pendiente para ese chat.")
            conn.close()
            return
        
        chat_title = result[0]
        conn.close()
        
        # Autorizar el chat
        if authorize_chat(chat_id, chat_title, user_id):
            await update.message.reply_text(f"✅ Grupo '{chat_title}' autorizado exitosamente.")
            
            # Notificar al grupo autorizado
            try:
                await context.bot.send_message(
                    chat_id,
                    "🎉 ¡Grupo autorizado!\n"
                    "Ya puedes usar todos los comandos del bot."
                )
            except:
                pass
        else:
            await update.message.reply_text("❌ Error autorizando el grupo.")
            
    except Exception as e:
        logger.error(f"Error aprobando grupo: {e}")
        await update.message.reply_text("❌ Error procesando la autorización.")

async def cmd_ver_solicitudes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ver solicitudes pendientes (solo admins)"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT chat_id, chat_title, requested_by, requested_at 
            FROM auth_requests 
            WHERE status = 'pending'
            ORDER BY requested_at DESC
        """)
        
        solicitudes = cursor.fetchall()
        conn.close()
        
        if not solicitudes:
            await update.message.reply_text("✅ No hay solicitudes pendientes.")
            return
        
        mensaje = "📋 **Solicitudes pendientes:**\n\n"
        for chat_id, chat_title, requested_by, requested_at in solicitudes:
            mensaje += (
                f"**{chat_title}**\n"
                f"ID: `{chat_id}`\n"
                f"Solicitado por: {requested_by}\n"
                f"Fecha: {requested_at}\n"
                f"Aprobar: /aprobar {chat_id}\n\n"
            )
        
        await update.message.reply_text(mensaje, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error viendo solicitudes: {e}")
        await update.message.reply_text("❌ Error obteniendo solicitudes.")

# ========================================
# COMANDOS ADMINISTRATIVOS
# ========================================

async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Agregar nuevo administrador"""
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: /addadmin <user_id>\n"
            "Ejemplo: /addadmin 123456789"
        )
        return
    
    try:
        new_admin_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID de usuario inválido.")
        return
    
    current_user = update.effective_user.id
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_roles (user_id, role, assigned_by)
            VALUES (?, 'admin', ?)
        """, (new_admin_id, current_user))
        
        conn.commit()
        conn.close()
        
        ADMIN_IDS.add(new_admin_id)
        
        await update.message.reply_text(f"✅ Usuario {new_admin_id} agregado como administrador.")
        
    except Exception as e:
        logger.error(f"Error agregando admin: {e}")
        await update.message.reply_text("❌ Error agregando administrador.")

async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remover administrador"""
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: /removeadmin <user_id>\n"
            "Ejemplo: /removeadmin 123456789"
        )
        return
    
    try:
        admin_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID de usuario inválido.")
        return
    
    if admin_id == update.effective_user.id:
        await update.message.reply_text("❌ No puedes removerte a ti mismo como administrador.")
        return
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE user_roles SET role = 'user' WHERE user_id = ?",
            (admin_id,)
        )
        
        conn.commit()
        conn.close()
        
        ADMIN_IDS.discard(admin_id)
        
        await update.message.reply_text(f"✅ Usuario {admin_id} removido como administrador.")
        
    except Exception as e:
        logger.error(f"Error removiendo admin: {e}")
        await update.message.reply_text("❌ Error removiendo administrador.")

async def cmd_listadmins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listar administradores"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT user_id, assigned_at FROM user_roles WHERE role = 'admin'"
        )
        
        admins = cursor.fetchall()
        conn.close()
        
        if not admins:
            await update.message.reply_text("❌ No hay administradores registrados.")
            return
        
        mensaje = "👑 **Administradores:**\n\n"
        for user_id, assigned_at in admins:
            mensaje += f"• {user_id} (desde {assigned_at})\n"
        
        await update.message.reply_text(mensaje, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error listando admins: {e}")
        await update.message.reply_text("❌ Error obteniendo lista de administradores.")

async def cmd_revocar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Revocar autorización de grupo"""
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: /revocar <chat_id>\n"
            "Ejemplo: /revocar -123456789"
        )
        return
    
    try:
        chat_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID de chat inválido.")
        return
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE authorized_chats SET status = 'revoked' WHERE chat_id = ?",
            (chat_id,)
        )
        
        if cursor.rowcount == 0:
            await update.message.reply_text("❌ Ese chat no está autorizado.")
        else:
            conn.commit()
            await update.message.reply_text(f"✅ Autorización revocada para el chat {chat_id}.")
            
            # Notificar al grupo
            try:
                await context.bot.send_message(
                    chat_id,
                    "⚠️ La autorización de este grupo ha sido revocada.\n"
                    "El bot ya no funcionará aquí."
                )
            except:
                pass
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error revocando autorización: {e}")
        await update.message.reply_text("❌ Error revocando autorización.")

def setup_admin_list(admin_ids: list[int] = None):
    """Configurar lista de administradores iniciales"""
    if admin_ids:
        for admin_id in admin_ids:
            ADMIN_IDS.add(admin_id)
        logger.info(f"Administradores configurados: {ADMIN_IDS}")
