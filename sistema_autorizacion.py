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

[... todas las demás funciones existentes ...]

# Función para configurar administradores iniciales
def setup_admin_list(admin_ids: list[int] = None):
    """Configurar lista de administradores iniciales"""
    if admin_ids:
        for admin_id in admin_ids:
            ADMIN_IDS.add(admin_id)
        logger.info(f"Administradores configurados: {ADMIN_IDS}")

# Comando para solicitar autorización (NUEVA FUNCIÓN CORREGIDA)
async def cmd_solicitar_autorizacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Solicitar autorización para un grupo"""
    chat = update.effective_chat
    user = update.effective_user
    
    logger.info(f"Solicitud de autorización iniciada por {user.id} en chat {chat.id}")
    
    # Solo funciona en grupos
    if chat.type == 'private':
        try:
            await update.message.reply_text(
                "ℹ️ Los chats privados no necesitan autorización.\n"
                "Este comando solo funciona en grupos."
            )
        except Exception as e:
            logger.error(f"Error enviando mensaje de chat privado: {e}")
        return
    
    # Verificar si ya está autorizado
    if is_chat_authorized(chat.id):
        try:
            await update.message.reply_text("✅ Este grupo ya está autorizado.")
        except Exception as e:
            logger.error(f"Error enviando mensaje de ya autorizado: {e}")
        return
    
    try:
        # Verificar si ya hay una solicitud pendiente
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM auth_requests WHERE chat_id = ? AND status = 'pending'",
            (chat.id,)
        )
        
        if cursor.fetchone():
            conn.close()
            await update.message.reply_text(
                "⏳ Ya hay una solicitud pendiente para este grupo.\n"
                "Por favor espera a que sea revisada."
            )
            logger.info(f"Solicitud duplicada rechazada para chat {chat.id}")
            return
        
        # Crear nueva solicitud
        cursor.execute("""
            INSERT INTO auth_requests 
            (chat_id, chat_title, requested_by, requester_username)
            VALUES (?, ?, ?, ?)
        """, (chat.id, chat.title or "Sin título", user.id, user.username or user.first_name or "Sin nombre"))
        
        conn.commit()
        conn.close()
        
        # Enviar mensaje de confirmación
        mensaje_confirmacion = (
            "✅ Solicitud de autorización enviada.\n"
            f"📋 Grupo: {chat.title or 'Sin título'}\n"
            f"👤 Solicitado por: {user.mention_html()}\n"
            f"🆔 Chat ID: {chat.id}\n"
            "⏳ Espera a que un administrador la revise."
        )
        
        await update.message.reply_text(
            mensaje_confirmacion,
            parse_mode='HTML'
        )
        
        logger.info(f"Solicitud creada exitosamente para chat {chat.id}")
        
        # Notificar al administrador
        if ADMIN_IDS:
            try:
                mensaje_admin = (
                    "🔔 Nueva solicitud de autorización:\n"
                    f"📋 Grupo: {chat.title or 'Sin título'}\n"
                    f"👤 Solicitado por: @{user.username or user.first_name}\n"
                    f"🆔 Chat ID: {chat.id}\n"
                    f"▫️ Para aprobar: /aprobar {chat.id}"
                )
                
                for admin_id in ADMIN_IDS:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=mensaje_admin
                    )
                logger.info(f"Notificación enviada a los administradores")
            except Exception as e:
                logger.error(f"Error notificando al administrador: {e}")
        
    except Exception as e:
        logger.error(f"Error procesando solicitud de autorización: {e}")
        try:
            await update.message.reply_text(
                "❌ Error procesando la solicitud. Inténtalo de nuevo."
            )
        except Exception as e2:
            logger.error(f"Error enviando mensaje de error: {e2}")

# Comando para aprobar grupos (NUEVA FUNCIÓN)
async def cmd_aprobar_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aprobar un grupo (solo administradores)"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Solo administradores pueden usar este comando.")
        return
        
    if not context.args:
        await update.message.reply_text("📝 Uso: /aprobar <chat_id>")
        return
        
    try:
        chat_id_to_approve = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID de chat inválido.")
        return
    
    try:
        # Buscar la solicitud
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT chat_title, requester_username 
            FROM auth_requests 
            WHERE chat_id = ? AND status = 'pending'
        """, (chat_id_to_approve,))
        
        request = cursor.fetchone()
        if not request:
            conn.close()
            await update.message.reply_text("❌ No hay solicitud pendiente para ese chat.")
            return
        
        chat_title, requester = request
        
        # Aprobar el grupo
        authorize_chat(chat_id_to_approve, chat_title, user.id)
        conn.close()
        
        await update.message.reply_text(
            f"✅ Grupo aprobado exitosamente:\n"
            f"📋 {chat_title}\n"
            f"👤 Solicitado por: {requester}\n"
            f"🆔 Chat ID: {chat_id_to_approve}"
        )
        
        # Notificar al grupo
        try:
            await context.bot.send_message(
                chat_id=chat_id_to_approve,
                text="🎉 ¡Su grupo ha sido autorizado!\n"
                     "Ya pueden usar todos los comandos del bot."
            )
        except Exception as e:
            logger.warning(f"No se pudo notificar al grupo {chat_id_to_approve}: {e}")
            
    except Exception as e:
        logger.error(f"Error aprobando grupo: {e}")
        await update.message.reply_text("❌ Error procesando la aprobación.")
