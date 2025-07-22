# ====================================
# SISTEMA DE AUTORIZACIÓN COMPLETO
# ====================================

# IMPORTACIONES CORREGIDAS - TODAS AL INICIO
import sqlite3
import logging
from typing import List, Callable, Any
from functools import wraps
from datetime import datetime

# IMPORTACIONES DE TELEGRAM (MOVIDAS AL INICIO)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====================================
# CONFIGURACIÓN
# ====================================

class Config:
    DB_PATH = "cinebot.db"
    # Lista de administradores iniciales (IDs de Telegram)
    INITIAL_ADMINS = [123456789]  # Reemplaza con tu ID real

# ====================================
# BASE DE DATOS
# ====================================

def create_auth_tables():
    """Crear tablas necesarias para el sistema de autorización"""
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        # Tabla de chats autorizados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authorized_chats (
                chat_id INTEGER PRIMARY KEY,
                chat_name TEXT NOT NULL,
                chat_type TEXT NOT NULL,
                authorized_by INTEGER NOT NULL,
                authorized_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Tabla de administradores
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                added_by INTEGER NOT NULL,
                added_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Tabla de solicitudes de autorización
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authorization_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                chat_name TEXT NOT NULL,
                chat_type TEXT NOT NULL,
                requested_by INTEGER NOT NULL,
                requester_username TEXT,
                requested_at TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                processed_by INTEGER,
                processed_at TEXT
            )
        """)
        
        # Tabla de logs de autorización
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                chat_id INTEGER,
                user_id INTEGER,
                admin_id INTEGER,
                details TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        
        # Insertar administradores iniciales
        for admin_id in Config.INITIAL_ADMINS:
            cursor.execute("""
                INSERT OR IGNORE INTO bot_admins (user_id, username, added_by, added_at)
                VALUES (?, ?, ?, ?)
            """, (admin_id, "system", 0, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        logger.info("✅ Tablas de autorización creadas/actualizadas")
        
    except Exception as e:
        logger.error(f"❌ Error creando tablas: {e}")

def log_auth_action(cursor, action, chat_id=None, user_id=None, admin_id=None, details=None):
    """Registrar acciones del sistema de autorización"""
    cursor.execute("""
        INSERT INTO auth_logs (action, chat_id, user_id, admin_id, details, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (action, chat_id, user_id, admin_id, details, datetime.now().isoformat()))

# ====================================
# FUNCIONES DE VERIFICACIÓN
# ====================================

def is_admin(user_id: int) -> bool:
    """Verificar si un usuario es administrador del bot"""
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM bot_admins 
            WHERE user_id = ? AND is_active = 1
        """, (user_id,))
        
        result = cursor.fetchone()[0] > 0
        conn.close()
        return result
        
    except Exception as e:
        logger.error(f"Error verificando admin: {e}")
        return False

def is_chat_authorized(chat_id: int) -> bool:
    """Verificar si un chat está autorizado"""
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM authorized_chats 
            WHERE chat_id = ? AND is_active = 1
        """, (chat_id,))
        
        result = cursor.fetchone()[0] > 0
        conn.close()
        return result
        
    except Exception as e:
        logger.error(f"Error verificando autorización: {e}")
        return False

def authorize_chat(chat_id: int, chat_name: str, chat_type: str, admin_id: int) -> bool:
    """Autorizar un chat"""
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO authorized_chats 
            (chat_id, chat_name, chat_type, authorized_by, authorized_at, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (chat_id, chat_name, chat_type, admin_id, datetime.now().isoformat()))
        
        log_auth_action(cursor, "CHAT_AUTHORIZED", chat_id, None, admin_id, 
                       f"Chat '{chat_name}' autorizado")
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Chat autorizado: {chat_name} ({chat_id})")
        return True
        
    except Exception as e:
        logger.error(f"Error autorizando chat: {e}")
        return False

def revoke_chat(chat_id: int, admin_id: int) -> bool:
    """Revocar autorización de un chat"""
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE authorized_chats 
            SET is_active = 0
            WHERE chat_id = ?
        """, (chat_id,))
        
        log_auth_action(cursor, "CHAT_REVOKED", chat_id, None, admin_id, 
                       "Autorización revocada")
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Autorización revocada: {chat_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error revocando autorización: {e}")
        return False

# ====================================
# DECORADORES
# ====================================

def require_authorization(func):
    """Decorador para requerir autorización del chat"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_chat.type == 'private':
            return await func(update, context, *args, **kwargs)
        
        if not is_chat_authorized(update.effective_chat.id):
            await update.message.reply_text(
                "🚫 **Este grupo no está autorizado**\n\n"
                "Para usar el bot, un administrador debe autorizar este grupo.\n"
                "Usa `/solicitar` para enviar una solicitud.",
                parse_mode='Markdown'
            )
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper

def require_admin(func):
    """Decorador para requerir permisos de administrador"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not is_admin(update.effective_user.id):
            await update.message.reply_text("❌ No tienes permisos de administrador.")
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper

# ====================================
# COMANDOS DE USUARIO
# ====================================

async def cmd_solicitar_autorizacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para solicitar autorización de un grupo"""
    user = update.effective_user
    chat = update.effective_chat
    
    # Solo funciona en grupos
    if chat.type == 'private':
        await update.message.reply_text(
            "❌ Este comando solo funciona en grupos.\n\n"
            "Agrégame a tu grupo y usa `/solicitar` allí."
        )
        return
    
    # Verificar si ya está autorizado
    if is_chat_authorized(chat.id):
        await update.message.reply_text("✅ Este grupo ya está autorizado.")
        return
    
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        # Verificar si ya hay una solicitud pendiente
        cursor.execute("""
            SELECT COUNT(*) FROM authorization_requests 
            WHERE chat_id = ? AND status = 'pending'
        """, (chat.id,))
        
        if cursor.fetchone()[0] > 0:
            await update.message.reply_text(
                "⏳ Ya hay una solicitud pendiente para este grupo.\n"
                "Espera a que sea procesada por los administradores."
            )
            conn.close()
            return
        
        # Crear nueva solicitud
        cursor.execute("""
            INSERT INTO authorization_requests 
            (chat_id, chat_name, chat_type, requested_by, requester_username, requested_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (chat.id, chat.title or chat.first_name, chat.type, 
              user.id, user.username, datetime.now().isoformat()))
        
        log_auth_action(cursor, "REQUEST_CREATED", chat.id, user.id, None,
                       f"Solicitud creada por @{user.username}")
        
        conn.commit()
        conn.close()
        
        # Notificar a administradores
        await notificar_admins_nueva_solicitud(context, chat, user)
        
        await update.message.reply_text(
            "📝 **Solicitud enviada**\n\n"
            "Tu solicitud de autorización ha sido enviada a los administradores.\n"
            "Te notificaremos cuando sea procesada.\n\n"
            "**Grupo:** " + (chat.title or chat.first_name) + "\n"
            f"**Solicitado por:** @{user.username or user.first_name}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error en solicitar_autorizacion: {e}")
        await update.message.reply_text("❌ Error procesando la solicitud.")

# ====================================
# COMANDOS DE ADMINISTRADOR
# ====================================

@require_admin
async def cmd_aprobar_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aprobar un grupo manualmente"""
    if not context.args:
        await update.message.reply_text(
            "❌ **Uso incorrecto**\n\n"
            "Formato: `/aprobar <chat_id> [nombre_opcional]`\n\n"
            "Ejemplo: `/aprobar -123456789 Mi Grupo de Cine`",
            parse_mode='Markdown'
        )
        return
    
    try:
        chat_id = int(context.args[0])
        chat_name = " ".join(context.args[1:]) if len(context.args) > 1 else f"Grupo {chat_id}"
        
        if authorize_chat(chat_id, chat_name, "group", update.effective_user.id):
            await update.message.reply_text(
                f"✅ **Grupo autorizado exitosamente**\n\n"
                f"**ID:** `{chat_id}`\n"
                f"**Nombre:** {chat_name}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Error autorizando el grupo.")
            
    except ValueError:
        await update.message.reply_text("❌ ID de chat inválido.")
    except Exception as e:
        logger.error(f"Error en aprobar_grupo: {e}")
        await update.message.reply_text("❌ Error procesando el comando.")

@require_admin
async def cmd_revocar_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Revocar autorización de un grupo"""
    if not context.args:
        await update.message.reply_text(
            "❌ **Uso incorrecto**\n\n"
            "Formato: `/revocar <chat_id>`\n\n"
            "Ejemplo: `/revocar -123456789`",
            parse_mode='Markdown'
        )
        return
    
    try:
        chat_id = int(context.args[0])
        
        if revoke_chat(chat_id, update.effective_user.id):
            await update.message.reply_text(
                f"✅ **Autorización revocada**\n\n"
                f"**ID:** `{chat_id}`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Error revocando la autorización.")
            
    except ValueError:
        await update.message.reply_text("❌ ID de chat inválido.")
    except Exception as e:
        logger.error(f"Error en revocar_grupo: {e}")
        await update.message.reply_text("❌ Error procesando el comando.")

@require_admin
async def cmd_ver_solicitudes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ver solicitudes pendientes de autorización"""
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, chat_id, chat_name, chat_type, requested_by, 
                   requester_username, requested_at
            FROM authorization_requests 
            WHERE status = 'pending'
            ORDER BY requested_at DESC
        """)
        
        solicitudes = cursor.fetchall()
        conn.close()
        
        if not solicitudes:
            await update.message.reply_text("📭 No hay solicitudes pendientes.")
            return
        
        for solicitud in solicitudes:
            req_id, chat_id, chat_name, chat_type, requested_by, requester_username, requested_at = solicitud
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Aprobar", callback_data=f"approve_{req_id}_{chat_id}"),
                    InlineKeyboardButton("❌ Rechazar", callback_data=f"reject_{req_id}_{chat_id}")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"📋 **Nueva Solicitud #{req_id}**\n\n"
                f"**Grupo:** {chat_name}\n"
                f"**ID:** `{chat_id}`\n"
                f"**Tipo:** {chat_type}\n"
                f"**Solicitado por:** @{requester_username or 'desconocido'}\n"
                f"**Fecha:** {requested_at[:16]}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        
    except Exception as e:
        logger.error(f"Error en ver_solicitudes: {e}")
        await update.message.reply_text("❌ Error obteniendo solicitudes.")

# ====================================
# COMANDOS ADMINISTRATIVOS
# ====================================

@require_admin
async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Agregar un nuevo administrador"""
    if not context.args:
        await update.message.reply_text(
            "❌ **Uso incorrecto**\n\n"
            "Formato: `/addadmin <user_id> [username]`\n\n"
            "Ejemplo: `/addadmin 123456789 usuario123`",
            parse_mode='Markdown'
        )
        return
    
    try:
        new_admin_id = int(context.args[0])
        username = context.args[1] if len(context.args) > 1 else None
        
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO bot_admins 
            (user_id, username, added_by, added_at, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, (new_admin_id, username, update.effective_user.id, datetime.now().isoformat()))
        
        log_auth_action(cursor, "ADMIN_ADDED", None, new_admin_id, 
                       update.effective_user.id, f"Admin agregado: @{username}")
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ **Administrador agregado**\n\n"
            f"**ID:** `{new_admin_id}`\n"
            f"**Username:** @{username or 'N/A'}",
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text("❌ ID de usuario inválido.")
    except Exception as e:
        logger.error(f"Error en addadmin: {e}")
        await update.message.reply_text("❌ Error agregando administrador.")

@require_admin
async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remover un administrador"""
    if not context.args:
        await update.message.reply_text(
            "❌ **Uso incorrecto**\n\n"
            "Formato: `/removeadmin <user_id>`",
            parse_mode='Markdown'
        )
        return
    
    try:
        admin_id = int(context.args[0])
        
        # No permitir auto-eliminación
        if admin_id == update.effective_user.id:
            await update.message.reply_text("❌ No puedes removerte a ti mismo como admin.")
            return
        
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE bot_admins 
            SET is_active = 0
            WHERE user_id = ?
        """, (admin_id,))
        
        if cursor.rowcount > 0:
            log_auth_action(cursor, "ADMIN_REMOVED", None, admin_id,
                           update.effective_user.id, "Admin removido")
            
            conn.commit()
            await update.message.reply_text(f"✅ Administrador `{admin_id}` removido.", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Administrador no encontrado.")
        
        conn.close()
        
    except ValueError:
        await update.message.reply_text("❌ ID de usuario inválido.")
    except Exception as e:
        logger.error(f"Error en removeadmin: {e}")
        await update.message.reply_text("❌ Error removiendo administrador.")

@require_admin
async def cmd_listadmins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listar todos los administradores"""
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, username, added_at
            FROM bot_admins 
            WHERE is_active = 1
            ORDER BY added_at ASC
        """)
        
        admins = cursor.fetchall()
        conn.close()
        
        if not admins:
            await update.message.reply_text("📭 No hay administradores.")
            return
        
        response = "👥 **Administradores del Bot:**\n\n"
        for user_id, username, added_at in admins:
            response += f"• **ID:** `{user_id}`\n"
            response += f"  **Username:** @{username or 'N/A'}\n"
            response += f"  **Desde:** {added_at[:10]}\n\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error en listadmins: {e}")
        await update.message.reply_text("❌ Error obteniendo lista de administradores.")

@require_admin
async def cmd_chats_autorizados(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listar chats autorizados"""
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT chat_id, chat_name, chat_type, authorized_at
            FROM authorized_chats 
            WHERE is_active = 1
            ORDER BY authorized_at DESC
            LIMIT 20
        """)
        
        chats = cursor.fetchall()
        conn.close()
        
        if not chats:
            await update.message.reply_text("📭 No hay chats autorizados.")
            return
        
        response = "🔐 **Chats Autorizados:**\n\n"
        for chat_id, chat_name, chat_type, authorized_at in chats:
            response += f"• **{chat_name}**\n"
            response += f"  **ID:** `{chat_id}`\n"
            response += f"  **Tipo:** {chat_type}\n"
            response += f"  **Autorizado:** {authorized_at[:10]}\n\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error en chats_autorizados: {e}")
        await update.message.reply_text("❌ Error obteniendo chats autorizados.")

@require_admin
async def cmd_stats_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar estadísticas del sistema de autorización"""
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        # Contar chats autorizados
        cursor.execute("SELECT COUNT(*) FROM authorized_chats WHERE is_active = 1")
        chats_activos = cursor.fetchone()[0]
        
        # Contar solicitudes pendientes
        cursor.execute("SELECT COUNT(*) FROM authorization_requests WHERE status = 'pending'")
        solicitudes_pendientes = cursor.fetchone()[0]
        
        # Contar administradores
        cursor.execute("SELECT COUNT(*) FROM bot_admins WHERE is_active = 1")
        total_admins = cursor.fetchone()[0]
        
        # Últimas acciones
        cursor.execute("""
            SELECT action, details, timestamp 
            FROM auth_logs 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        ultimas_acciones = cursor.fetchall()
        
        conn.close()
        
        response = "📊 **Estadísticas de Autorización:**\n\n"
        response += f"🔐 **Chats autorizados:** {chats_activos}\n"
        response += f"📋 **Solicitudes pendientes:** {solicitudes_pendientes}\n"
        response += f"👥 **Administradores:** {total_admins}\n\n"
        
        if ultimas_acciones:
            response += "📝 **Últimas acciones:**\n"
            for action, details, timestamp in ultimas_acciones:
                response += f"• {action}: {details or 'N/A'} ({timestamp[:16]})\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error en stats_auth: {e}")
        await update.message.reply_text("❌ Error obteniendo estadísticas.")

# ====================================
# FUNCIONES AUXILIARES
# ====================================

async def notificar_admins_nueva_solicitud(context, chat, user):
    """Notificar a todos los admins sobre una nueva solicitud"""
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id FROM bot_admins WHERE is_active = 1")
        admins = cursor.fetchall()
        conn.close()
        
        mensaje = (
            f"🔔 **Nueva solicitud de autorización**\n\n"
            f"**Grupo:** {chat.title or chat.first_name}\n"
            f"**ID:** `{chat.id}`\n"
            f"**Tipo:** {chat.type}\n"
            f"**Solicitado por:** @{user.username or user.first_name}\n\n"
            f"Usa `/solicitudes` para ver y procesar."
        )
        
        for (admin_id,) in admins:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=mensaje,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"No se pudo notificar al admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error notificando admins: {e}")

# ====================================
# HANDLERS DE CALLBACKS
# ====================================

async def handle_authorization_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar callbacks de botones de autorización"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.edit_message_text("❌ No tienes permisos para esta acción.")
        return
    
    data = query.data
    
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        if data.startswith("approve_"):
            parts = data.split("_")
            req_id = int(parts[1])
            chat_id = int(parts[2])
            
            # Obtener información de la solicitud
            cursor.execute("""
                SELECT chat_name, chat_type, requested_by, requester_username
                FROM authorization_requests 
                WHERE id = ?
            """, (req_id,))
            
            result = cursor.fetchone()
            if not result:
                await query.edit_message_text("❌ Solicitud no encontrada.")
                conn.close()
                return
            
            chat_name, chat_type, requested_by, requester_username = result
            
            # Autorizar chat
            if authorize_chat(chat_id, chat_name, chat_type, query.from_user.id):
                await query.edit_message_text(
                    f"✅ **Chat autorizado exitosamente**\n\n"
                    f"**Grupo:** {chat_name}\n"
                    f"**ID:** `{chat_id}`\n"
                    f"**Autorizado por:** @{query.from_user.username}",
                    parse_mode='Markdown'
                )
                
                # Notificar al solicitante si es posible
                try:
                    await context.bot.send_message(
                        chat_id=requested_by,
                        text=f"🎉 **¡Tu solicitud ha sido aprobada!**\n\n"
                             f"El grupo **{chat_name}** ahora está autorizado.\n"
                             f"¡Disfruta del bot! 🎬"
                    )
                except Exception as e:
                    logger.warning(f"No se pudo notificar al usuario {requested_by}: {e}")
                
            else:
                await query.edit_message_text("❌ Error autorizando el chat.")
                
        elif data.startswith("reject_"):
            parts = data.split("_")
            req_id = int(parts[1])
            chat_id = int(parts[2])
            
            # Obtener información de la solicitud
            cursor.execute("""
                SELECT chat_name, requested_by, requester_username
                FROM authorization_requests 
                WHERE id = ?
            """, (req_id,))
            
            result = cursor.fetchone()
            if not result:
                await query.edit_message_text("❌ Solicitud no encontrada.")
                conn.close()
                return
            
            chat_name, requested_by, requester_username = result
            
            # Marcar como rechazada
            cursor.execute("""
                UPDATE authorization_requests 
                SET status = 'rejected'
                WHERE id = ?
            """, (req_id,))
            
            # Log de la acción
            log_auth_action(cursor, "REQUEST_REJECTED", chat_id, query.from_user.id, 
                           f"Solicitud rechazada por {query.from_user.username}")
            
            conn.commit()
            
            await query.edit_message_text(
                f"❌ **Solicitud rechazada**\n\n"
                f"**Grupo:** {chat_name}\n"
                f"**ID:** `{chat_id}`\n"
                f"**Rechazado por:** @{query.from_user.username}",
                parse_mode='Markdown'
            )
            
            # Notificar al solicitante si es posible
            try:
                await context.bot.send_message(
                    chat_id=requested_by,
                    text=f"⚠️ **Tu solicitud ha sido rechazada**\n\n"
                         f"El grupo **{chat_name}** no fue autorizado.\n"
                         f"Contacta a los administradores para más información."
