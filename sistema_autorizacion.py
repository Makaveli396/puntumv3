import os
import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from db import get_connection, is_postgresql

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración - ID del administrador principal
ADMIN_USER_ID = 5548909327  # Cambiar por tu user_id de Telegram

def is_chat_authorized(chat_id: int) -> bool:
    """Verificar si un chat está autorizado"""
    # Permitir chats privados siempre
    if chat_id > 0:
        return True
        
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if is_postgresql():
            cursor.execute(
                "SELECT 1 FROM authorized_chats WHERE chat_id = %s AND status = 'active'",
                (chat_id,)
            )
        else:
            cursor.execute(
                "SELECT 1 FROM authorized_chats WHERE chat_id = ? AND status = 'active'",
                (chat_id,)
            )
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return bool(result)
    except Exception as e:
        logger.error(f"❌ Error verificando autorización: {e}")
        return False

def authorize_chat(chat_id: int, chat_title: str, authorized_by: int):
    """Autorizar un chat"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if is_postgresql():
            cursor.execute("""
                INSERT INTO authorized_chats 
                (chat_id, chat_title, authorized_by, authorized_at, status)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP, 'active')
                ON CONFLICT (chat_id) DO UPDATE SET
                    chat_title = EXCLUDED.chat_title,
                    authorized_by = EXCLUDED.authorized_by,
                    authorized_at = CURRENT_TIMESTAMP,
                    status = 'active'
            """, (chat_id, chat_title, authorized_by))
            
            # Marcar solicitud como aprobada
            cursor.execute("""
                UPDATE auth_requests 
                SET status = 'approved' 
                WHERE chat_id = %s AND status = 'pending'
            """, (chat_id,))
        else:
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
        cursor.close()
        conn.close()
        logger.info(f"✅ Chat {chat_id} autorizado exitosamente")
    except Exception as e:
        logger.error(f"❌ Error autorizando chat: {e}")
        raise

def auth_required(func):
    """Decorador para requerir autorización en comandos"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        
        if not is_chat_authorized(chat_id):
            if chat_id < 0:  # Es un grupo
                try:
                    await update.message.reply_text(
                        "❌ Este grupo no está autorizado para usar el bot.\n"
                        "📝 Usa /solicitar para pedir autorización.",
                        reply_to_message_id=update.message.message_id
                    )
                except Exception as e:
                    logger.error(f"❌ Error enviando mensaje de no autorización: {e}")
                return
            else:  # Chat privado - siempre permitido
                pass
        
        return await func(update, context)
    return wrapper

async def cmd_solicitar_autorizacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Solicitar autorización para un grupo"""
    chat = update.effective_chat
    user = update.effective_user
    
    logger.info(f"🔐 Solicitud de autorización iniciada por {user.id} en chat {chat.id}")
    
    # Solo funciona en grupos
    if chat.type == 'private':
        try:
            await update.message.reply_text(
                "ℹ️ Los chats privados no necesitan autorización.\n"
                "Este comando solo funciona en grupos.",
                reply_to_message_id=update.message.message_id
            )
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje de chat privado: {e}")
        return
    
    # Verificar si ya está autorizado
    if is_chat_authorized(chat.id):
        try:
            await update.message.reply_text(
                "✅ Este grupo ya está autorizado.",
                reply_to_message_id=update.message.message_id
            )
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje de ya autorizado: {e}")
        return
    
    try:
        # Verificar si ya hay una solicitud pendiente
        conn = get_connection()
        cursor = conn.cursor()
        
        if is_postgresql():
            cursor.execute(
                "SELECT 1 FROM auth_requests WHERE chat_id = %s AND status = 'pending'",
                (chat.id,)
            )
        else:
            cursor.execute(
                "SELECT 1 FROM auth_requests WHERE chat_id = ? AND status = 'pending'",
                (chat.id,)
            )
        
        if cursor.fetchone():
            cursor.close()
            conn.close()
            await update.message.reply_text(
                "⏳ Ya hay una solicitud pendiente para este grupo.\n"
                "Por favor espera a que sea revisada.",
                reply_to_message_id=update.message.message_id
            )
            logger.info(f"⚠️ Solicitud duplicada rechazada para chat {chat.id}")
            return
        
        # Crear nueva solicitud
        if is_postgresql():
            cursor.execute("""
                INSERT INTO auth_requests 
                (chat_id, chat_title, requested_by, requester_username)
                VALUES (%s, %s, %s, %s)
            """, (chat.id, chat.title or "Sin título", user.id, user.username or user.first_name or "Sin nombre"))
        else:
            cursor.execute("""
                INSERT INTO auth_requests 
                (chat_id, chat_title, requested_by, requester_username)
                VALUES (?, ?, ?, ?)
            """, (chat.id, chat.title or "Sin título", user.id, user.username or user.first_name or "Sin nombre"))
        
        conn.commit()
        cursor.close()
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
            parse_mode='HTML',
            reply_to_message_id=update.message.message_id
        )
        
        logger.info(f"✅ Solicitud creada exitosamente para chat {chat.id}")
        
        # Notificar al administrador si está configurado
        if ADMIN_USER_ID:
            try:
                mensaje_admin = (
                    "🔔 Nueva solicitud de autorización:\n"
                    f"📋 Grupo: {chat.title or 'Sin título'}\n"
                    f"👤 Solicitado por: @{user.username or user.first_name}\n"
                    f"🆔 Chat ID: {chat.id}\n"
                    f"▫️ Para aprobar: /aprobar {chat.id}"
                )
                
                await context.bot.send_message(
                    chat_id=ADMIN_USER_ID,
                    text=mensaje_admin
                )
                logger.info(f"📤 Notificación enviada al administrador {ADMIN_USER_ID}")
            except Exception as e:
                logger.error(f"❌ Error notificando al administrador: {e}")
        
    except Exception as e:
        logger.error(f"❌ Error procesando solicitud de autorización: {e}")
        try:
            await update.message.reply_text(
                "❌ Error procesando la solicitud. Inténtalo de nuevo.",
                reply_to_message_id=update.message.message_id
            )
        except Exception as e2:
            logger.error(f"❌ Error enviando mensaje de error: {e2}")

async def cmd_aprobar_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aprobar un grupo (solo administradores)"""
    user = update.effective_user
    
    # Verificar si es administrador
    if ADMIN_USER_ID is None:
        await update.message.reply_text(
            "⚠️ No hay administrador configurado.\n"
            "Configura ADMIN_USER_ID en sistema_autorizacion.py",
            reply_to_message_id=update.message.message_id
        )
        return
    
    if user.id != ADMIN_USER_ID:
        await update.message.reply_text(
            "❌ Solo los administradores pueden usar este comando.",
            reply_to_message_id=update.message.message_id
        )
        return
    
    # Obtener ID del grupo a aprobar
    if not context.args:
        await update.message.reply_text(
            "📝 Uso: /aprobar <chat_id>\n"
            "Usa /solicitudes para ver IDs pendientes.",
            reply_to_message_id=update.message.message_id
        )
        return
    
    try:
        chat_id_to_approve = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ ID de chat inválido.",
            reply_to_message_id=update.message.message_id
        )
        return
    
    try:
        # Buscar la solicitud
        conn = get_connection()
        cursor = conn.cursor()
        
        if is_postgresql():
            cursor.execute("""
                SELECT chat_title, requester_username 
                FROM auth_requests 
                WHERE chat_id = %s AND status = 'pending'
            """, (chat_id_to_approve,))
        else:
            cursor.execute("""
                SELECT chat_title, requester_username 
                FROM auth_requests 
                WHERE chat_id = ? AND status = 'pending'
            """, (chat_id_to_approve,))
        
        request = cursor.fetchone()
        if not request:
            cursor.close()
            conn.close()
            await update.message.reply_text(
                "❌ No hay solicitud pendiente para ese chat.",
                reply_to_message_id=update.message.message_id
            )
            return
        
        chat_title, requester = request
        cursor.close()
        conn.close()
        
        # Aprobar el grupo
        authorize_chat(chat_id_to_approve, chat_title, user.id)
        
        await update.message.reply_text(
            f"✅ Grupo aprobado exitosamente:\n"
            f"📋 {chat_title}\n"
            f"👤 Solicitado por: {requester}\n"
            f"🆔 Chat ID: {chat_id_to_approve}",
            reply_to_message_id=update.message.message_id
        )
        
        # Notificar al grupo
        try:
            await context.bot.send_message(
                chat_id=chat_id_to_approve,
                text="🎉 ¡Su grupo ha sido autorizado!\n"
                     "Ya pueden usar todos los comandos del bot."
            )
            logger.info(f"📤 Grupo {chat_id_to_approve} notificado de autorización")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo notificar al grupo {chat_id_to_approve}: {e}")
            
    except Exception as e:
        logger.error(f"❌ Error aprobando grupo: {e}")
        await update.message.reply_text(
            "❌ Error procesando la aprobación.",
            reply_to_message_id=update.message.message_id
        )

async def cmd_ver_solicitudes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ver solicitudes pendientes (solo administradores)"""
    user = update.effective_user
    
    if ADMIN_USER_ID is None or user.id != ADMIN_USER_ID:
        await update.message.reply_text(
            "❌ Solo los administradores pueden usar este comando.",
            reply_to_message_id=update.message.message_id
        )
        return
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if is_postgresql():
            cursor.execute("""
                SELECT chat_id, chat_title, requester_username, requested_at
                FROM auth_requests 
                WHERE status = 'pending'
                ORDER BY requested_at ASC
            """)
        else:
            cursor.execute("""
                SELECT chat_id, chat_title, requester_username, requested_at
                FROM auth_requests 
                WHERE status = 'pending'
                ORDER BY requested_at ASC
            """)
        
        requests = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not requests:
            await update.message.reply_text(
                "✅ No hay solicitudes pendientes.",
                reply_to_message_id=update.message.message_id
            )
            return
        
        message = "📋 **Solicitudes Pendientes:**\n\n"
        for chat_id, chat_title, requester, requested_at in requests:
            message += f"🆔 `{chat_id}`\n"
            message += f"📋 {chat_title or 'Sin título'}\n"
            message += f"👤 {requester or 'Sin nombre'}\n"
            message += f"📅 {requested_at}\n"
            message += f"▫️ Para aprobar: `/aprobar {chat_id}`\n\n"
        
        await update.message.reply_text(
            message, 
            parse_mode='Markdown',
            reply_to_message_id=update.message.message_id
        )
        
    except Exception as e:
        logger.error(f"❌ Error viendo solicitudes: {e}")
        await update.message.reply_text(
            "❌ Error obteniendo las solicitudes.",
            reply_to_message_id=update.message.message_id
        )

async def cmd_status_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verificar estado del sistema de autorización (solo administradores)"""
    user = update.effective_user
    
    if ADMIN_USER_ID is None or user.id != ADMIN_USER_ID:
        await update.message.reply_text(
            "❌ Solo los administradores pueden usar este comando.",
            reply_to_message_id=update.message.message_id
        )
        return
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if is_postgresql():
            # Contar grupos autorizados
            cursor.execute("SELECT COUNT(*) FROM authorized_chats WHERE status = 'active'")
            authorized_count = cursor.fetchone()[0]
            
            # Contar solicitudes pendientes
            cursor.execute("SELECT COUNT(*) FROM auth_requests WHERE status = 'pending'")
            pending_count = cursor.fetchone()[0]
        else:
            # Contar grupos autorizados
            cursor.execute("SELECT COUNT(*) FROM authorized_chats WHERE status = 'active'")
            authorized_count = cursor.fetchone()[0]
            
            # Contar solicitudes pendientes
            cursor.execute("SELECT COUNT(*) FROM auth_requests WHERE status = 'pending'")
            pending_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        status_message = (
            "📊 **Estado del Sistema de Autorización:**\n\n"
            f"✅ Grupos autorizados: {authorized_count}\n"
            f"⏳ Solicitudes pendientes: {pending_count}\n"
            f"👤 Administrador: {ADMIN_USER_ID}\n"
            f"🤖 Sistema: Activo"
        )
        
        await update.message.reply_text(
            status_message, 
            parse_mode='Markdown',
            reply_to_message_id=update.message.message_id
        )
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo status: {e}")
        await update.message.reply_text(
            "❌ Error obteniendo el estado del sistema.",
            reply_to_message_id=update.message.message_id
        )

# Función auxiliar para configurar administrador
def set_admin_user_id(admin_id: int):
    """Configurar ID del administrador principal"""
    global ADMIN_USER_ID
    ADMIN_USER_ID = admin_id
    logger.info(f"👤 Administrador configurado: {admin_id}")

# Función para obtener información de autorización de un chat
def get_chat_auth_info(chat_id: int):
    """Obtener información de autorización de un chat"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if is_postgresql():
            cursor.execute("""
                SELECT chat_title, authorized_by, authorized_at, status
                FROM authorized_chats 
                WHERE chat_id = %s
            """, (chat_id,))
        else:
            cursor.execute("""
                SELECT chat_title, authorized_by, authorized_at, status
                FROM authorized_chats 
                WHERE chat_id = ?
            """, (chat_id,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return {
                'chat_title': result[0],
                'authorized_by': result[1],
                'authorized_at': result[2],
                'status': result[3],
                'is_authorized': result[3] == 'active'
            }
        return None
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo info de autorización: {e}")
        return None

def get_all_authorized_chats():
    """Obtener todos los chats autorizados"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if is_postgresql():
            cursor.execute("""
                SELECT chat_id, chat_title, authorized_by, authorized_at, status
                FROM authorized_chats 
                WHERE status = 'active'
                ORDER BY authorized_at DESC
            """)
        else:
            cursor.execute("""
                SELECT chat_id, chat_title, authorized_by, authorized_at, status
                FROM authorized_chats 
                WHERE status = 'active'
                ORDER BY authorized_at DESC
            """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        chats = []
        for row in results:
            chats.append({
                'chat_id': row[0],
                'chat_title': row[1],
                'authorized_by': row[2],
                'authorized_at': row[3],
                'status': row[4]
            })
        
        return chats
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo chats autorizados: {e}")
        return []

def revoke_chat_authorization(chat_id: int):
    """Revocar autorización de un chat"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if is_postgresql():
            cursor.execute("""
                UPDATE authorized_chats 
                SET status = 'revoked' 
                WHERE chat_id = %s
            """, (chat_id,))
        else:
            cursor.execute("""
                UPDATE authorized_chats 
                SET status = 'revoked' 
                WHERE chat_id = ?
            """, (chat_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"🚫 Autorización revocada para chat {chat_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error revocando autorización: {e}")
        return False

def cleanup_old_requests(days_old: int = 30):
    """Limpiar solicitudes antiguas"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if is_postgresql():
            cursor.execute("""
                DELETE FROM auth_requests 
                WHERE requested_at < NOW() - INTERVAL '%s days' 
                AND status != 'pending'
            """, (days_old,))
        else:
            # Para SQLite, necesitamos calcular la fecha manualmente
            from datetime import datetime, timedelta
            cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()
            cursor.execute("""
                DELETE FROM auth_requests 
                WHERE requested_at < ? 
                AND status != 'pending'
            """, (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        if deleted_count > 0:
            logger.info(f"🧹 Limpiadas {deleted_count} solicitudes antiguas")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"❌ Error limpiando solicitudes antiguas: {e}")
        return 0

# Comando adicional para administradores: revocar autorización
async def cmd_revocar_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Revocar autorización de un grupo (solo administradores)"""
    user = update.effective_user
    
    if ADMIN_USER_ID is None or user.id != ADMIN_USER_ID:
        await update.message.reply_text(
            "❌ Solo los administradores pueden usar este comando.",
            reply_to_message_id=update.message.message_id
        )
        return
    
    if not context.args:
        await update.message.reply_text(
            "📝 Uso: /revocar <chat_id>\n"
            "Revoca la autorización de un grupo.",
            reply_to_message_id=update.message.message_id
        )
        return
    
    try:
        chat_id_to_revoke = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ ID de chat inválido.",
            reply_to_message_id=update.message.message_id
        )
        return
    
    # Verificar si el chat está autorizado
    auth_info = get_chat_auth_info(chat_id_to_revoke)
    if not auth_info or not auth_info['is_authorized']:
        await update.message.reply_text(
            "❌ Este chat no está autorizado actualmente.",
            reply_to_message_id=update.message.message_id
        )
        return
    
    # Revocar autorización
    if revoke_chat_authorization(chat_id_to_revoke):
        await update.message.reply_text(
            f"✅ Autorización revocada exitosamente:\n"
            f"📋 {auth_info['chat_title']}\n"
            f"🆔 Chat ID: {chat_id_to_revoke}",
            reply_to_message_id=update.message.message_id
        )
        
        # Notificar al grupo
        try:
            await context.bot.send_message(
                chat_id=chat_id_to_revoke,
                text="🚫 La autorización de este grupo ha sido revocada.\n"
                     "Los comandos del bot ya no funcionarán aquí.\n"
                     "Usa /solicitar para pedir una nueva autorización."
            )
            logger.info(f"📤 Grupo {chat_id_to_revoke} notificado de revocación")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo notificar al grupo {chat_id_to_revoke}: {e}")
    else:
        await update.message.reply_text(
            "❌ Error revocando la autorización.",
            reply_to_message_id=update.message.message_id
        )

# Comando para listar grupos autorizados
async def cmd_grupos_autorizados(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listar grupos autorizados (solo administradores)"""
    user = update.effective_user
    
    if ADMIN_USER_ID is None or user.id != ADMIN_USER_ID:
        await update.message.reply_text(
            "❌ Solo los administradores pueden usar este comando.",
            reply_to_message_id=update.message.message_id
        )
        return
    
    chats = get_all_authorized_chats()
    
    if not chats:
        await update.message.reply_text(
            "📭 No hay grupos autorizados actualmente.",
            reply_to_message_id=update.message.message_id
        )
        return
    
    message = "🏢 **Grupos Autorizados:**\n\n"
    for chat in chats[:10]:  # Mostrar solo los primeros 10
        message += f"📋 {chat['chat_title'] or 'Sin título'}\n"
        message += f"🆔 `{chat['chat_id']}`\n"
        message += f"📅 {chat['authorized_at']}\n"
        message += f"▫️ Para revocar: `/revocar {chat['chat_id']}`\n\n"
    
    if len(chats) > 10:
        message += f"... y {len(chats) - 10} grupos más."
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_to_message_id=update.message.message_id
    )

# Función de utilidad para verificar si un usuario es administrador
def is_admin(user_id: int) -> bool:
    """Verificar si un usuario es administrador"""
    return ADMIN_USER_ID is not None and user_id == ADMIN_USER_ID

# Función para obtener estadísticas del sistema de autorización
def get_auth_stats():
    """Obtener estadísticas del sistema de autorización"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        stats = {
            'authorized_chats': 0,
            'pending_requests': 0,
            'approved_requests': 0,
            'total_requests': 0
        }
        
        if is_postgresql():
            # Chats autorizados
            cursor.execute("SELECT COUNT(*) FROM authorized_chats WHERE status = 'active'")
            stats['authorized_chats'] = cursor.fetchone()[0]
            
            # Solicitudes pendientes
            cursor.execute("SELECT COUNT(*) FROM auth_requests WHERE status = 'pending'")
            stats['pending_requests'] = cursor.fetchone()[0]
            
            # Solicitudes aprobadas
            cursor.execute("SELECT COUNT(*) FROM auth_requests WHERE status = 'approved'")
            stats['approved_requests'] = cursor.fetchone()[0]
            
            # Total de solicitudes
            cursor.execute("SELECT COUNT(*) FROM auth_requests")
            stats['total_requests'] = cursor.fetchone()[0]
            
        else:
            # Mismas consultas para SQLite
            cursor.execute("SELECT COUNT(*) FROM authorized_chats WHERE status = 'active'")
            stats['authorized_chats'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM auth_requests WHERE status = 'pending'")
            stats['pending_requests'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM auth_requests WHERE status = 'approved'")
            stats['approved_requests'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM auth_requests")
            stats['total_requests'] = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas de autorización: {e}")
        return {
            'authorized_chats': 0,
            'pending_requests': 0,
            'approved_requests': 0,
            'total_requests': 0
        }

# Función de inicialización del sistema de autorización
def initialize_auth_system():
    """Inicializar el sistema de autorización"""
    try:
        logger.info("🔐 Inicializando sistema de autorización...")
        
        # Las tablas ya se crean en create_all_tables() en db.py
        # Solo verificar que el administrador esté configurado
        if ADMIN_USER_ID:
            logger.info(f"👤 Administrador configurado: {ADMIN_USER_ID}")
        else:
            logger.warning("⚠️ No hay administrador configurado")
        
        # Obtener estadísticas iniciales
        stats = get_auth_stats()
        logger.info(f"📊 Grupos autorizados: {stats['authorized_chats']}")
        logger.info(f"📊 Solicitudes pendientes: {stats['pending_requests']}")
        
        logger.info("✅ Sistema de autorización inicializado")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error inicializando sistema de autorización: {e}")
        return False

# Ejecutar inicialización si se importa el módulo directamente
if __name__ == "__main__":
    logger.info("🧪 Ejecutando sistema_autorizacion.py directamente...")
    if initialize_auth_system():
        logger.info("🎉 Sistema de autorización listo!")
    else:
        logger.error("💥 Error en la inicialización del sistema de autorización")