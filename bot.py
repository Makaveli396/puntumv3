# bot.py
import os
import logging
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

# Importaciones de tus módulos locales
# CAMBIO CLAVE: Importaciones de sistema_autorizacion.py (sin setup_admin_list)
from sistema_autorizacion import (
    create_auth_tables, is_chat_authorized, authorize_chat,
    auth_required, cmd_solicitar_autorizacion, cmd_aprobar_grupo, cmd_ver_solicitudes,
    cmd_status_auth # Asegúrate de que cmd_status_auth esté si lo usas en sistema_autorizacion.py
)

# CORRECCIÓN DE SINTAXIS: Nueva línea para separar importaciones
from comandos_basicos import (
    cmd_id, cmd_saludar, cmd_rules, cmd_echo, cmd_about,
    cmd_info, cmd_donate, cmd_contacto, cmd_links,
    cmd_github, cmd_version
    # Nota: cmd_start, cmd_help, cmd_config, cmd_stats, cmd_broadcast_message, cmd_ping, cmd_status
    # no están en tu comandos_basicos.py proporcionado.
    # Si los tienes en otro lugar, deberás importarlos de allí o definirlos.
    # Aquí solo importo los que sí estaban en tu comandos_basicos.py.
)

from db import (
    initialize_db, add_user, get_user_by_telegram_id,
    add_chat, get_chat_by_telegram_id, record_message,
    get_top_users, get_top_chats, get_bot_stats,
    update_user_activity, update_chat_activity
)
from utils import (
    load_env, get_random_meme_url,
    get_crypto_price, fetch_weather, get_exchange_rate,
    get_youtube_video_info, get_joke, get_random_fact
)
from juegos import (
    cmd_adivinapelicula, cmd_emojipelicula, handle_game_message,
    handle_trivia_callback
)

from generador_trivia import generar_pregunta

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Comandos Administrativos (auth_required) ---
# Si estas funciones no están en comandos_basicos.py o sistema_autorizacion.py,
# deberás definirlas o importarlas de donde estén.
# Por simplicidad, asumo que las funciones importadas son las que están definidas.

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia el bot."""
    if not update.effective_chat: return
    await update.effective_chat.send_message("¡Hola! Soy tu bot cinéfilo. Usa /help para ver mis funciones.")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra la ayuda."""
    if not update.effective_chat: return
    help_text = """
    🎥 **Comandos Cinéfilos:**
    /cinematrivia - Inicia una trivia de películas.
    /adivinapelicula - Juega a adivinar la película (en desarrollo).
    /emojipelicula - Juega a adivinar la película con emojis (en desarrollo).

    🤖 **Comandos Básicos:**
    /id - Muestra tu ID de usuario y el ID del chat.
    /saludar - El bot te saluda.
    /rules - Muestra las reglas del grupo.
    /echo [mensaje] - El bot repite tu mensaje.
    /about - Información sobre el bot.
    /info - Información general.
    /contacto - Contacto del desarrollador.
    /links - Enlaces útiles.
    /github - Enlace al repositorio de GitHub.
    /version - Muestra la versión del bot.

    💰 **Apoyo:**
    /donate - Información para donar.

    ✨ **Utilidades (solo admins):**
    /crypto [moneda] - Precio de criptomonedas (ej. /crypto BTC).
    /weather [ciudad] - Clima de una ciudad (ej. /weather Madrid).
    /exchange [USD EUR] - Tasa de cambio (ej. /exchange USD EUR).
    /youtube [URL] - Información de video de YouTube.
    /joke - Un chiste aleatorio.
    /fact - Un dato curioso aleatorio.
    /status - Estado del bot.
    /ping - Comprueba la latencia.
    /config - Configuración del bot.
    /stats - Estadísticas de uso.
    /broadcast_message [mensaje] - Envía un mensaje a todos los chats.

    🔒 **Comandos de Autorización:**
    /solicitarautorizacion - Solicita autorización para tu chat.
    /aprobar_grupo [chat_id] - Aprueba un grupo (solo admins).
    /ver_solicitudes - Ve solicitudes pendientes (solo admins).
    /status_auth - Ver estado de autorización del chat.

    ¡Disfruta del cine con Puntum Bot! 🍿
    """
    await update.effective_chat.send_message(help_text, parse_mode="Markdown")

# --- Funciones de Comandos de Juegos ---
async def cmd_cinematrivia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia una nueva trivia de películas."""
    if not update.effective_chat:
        return

    chat_id = update.effective_chat.id

    if 'active_trivia_answer' in context.chat_data:
        await update.effective_chat.send_message(
            "Ya hay una trivia de películas activa en este chat. ¡Responde la pregunta actual!"
        )
        return

    try:
        pregunta, respuesta_correcta = generar_pregunta()
        if respuesta_correcta == "Error":
             await update.effective_chat.send_message(pregunta)
             return

        context.chat_data['active_trivia_question'] = pregunta
        context.chat_data['active_trivia_answer'] = respuesta_correcta.lower().strip()

        await update.effective_chat.send_message(f"🎬 ¡Nueva Trivia de Cine!\n\n{pregunta}")
        await update.effective_chat.send_message("Responde directamente a este mensaje para adivinar.")

    except Exception as e:
        logger.error(f"Error al iniciar trivia de películas: {e}")
        await update.effective_chat.send_message("Lo siento, no pude generar una pregunta de trivia en este momento. Por favor, intenta de nuevo más tarde.")


# --- Manejadores de Mensajes Generales ---
async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja todos los mensajes de texto para registrar actividad y otras lógicas."""
    if update.effective_user and update.effective_chat and update.message and update.message.text:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        username = update.effective_user.username or update.effective_user.first_name
        chat_type = update.effective_chat.type

        await add_user(user_id, username)
        await add_chat(chat_id, update.effective_chat.title or "Private Chat", chat_type)
        await record_message(user_id, chat_id, update.message.text)
        await update_user_activity(user_id)
        await update_chat_activity(chat_id)

        if 'active_trivia_answer' in context.chat_data:
            user_response = update.message.text.lower().strip()
            expected_answer = context.chat_data['active_trivia_answer']

            if user_response == expected_answer:
                await update.effective_chat.send_message(
                    f"🎉 ¡Correcto, {update.effective_user.first_name}! La respuesta era '{expected_answer.title()}'."
                )
                del context.chat_data['active_trivia_question']
                del context.chat_data['active_trivia_answer']
                return
    await handle_game_message(update, context)


# --- Inicialización y Ejecución del Bot ---
async def post_init(application):
    """Configurar comandos y tareas después de inicializar la aplicación"""
    commands = [
        # Comandos básicos
        BotCommand("start", "Inicia el bot"),
        BotCommand("help", "Muestra la ayuda"),
        BotCommand("id", "Muestra tu ID de usuario y chat"),
        BotCommand("echo", "Repite tu mensaje"),
        BotCommand("saludar", "El bot te saluda"),
        BotCommand("rules", "Muestra las reglas del grupo"),
        BotCommand("about", "Información sobre el bot"),
        BotCommand("info", "Muestra información útil"),
        BotCommand("contacto", "Información de contacto"),
        BotCommand("links", "Enlaces útiles"),
        BotCommand("donate", "Información para donaciones"),
        BotCommand("github", "Enlace al repositorio de GitHub"),
        BotCommand("version", "Muestra la versión del bot"),
        # Comandos de utilidad (asumiendo que los de 'utils' los manejas directamente en bot.py)
        BotCommand("meme", "Obtén un meme aleatorio"),
        BotCommand("crypto", "Obtén el precio de una criptomoneda"),
        BotCommand("weather", "Obtén el clima de una ciudad"),
        BotCommand("exchange", "Obtén tasa de cambio"),
        BotCommand("youtube", "Obtén info de video de YouTube"),
        BotCommand("joke", "Obtén un chiste aleatorio"),
        BotCommand("fact", "Obtén un dato curioso aleatorio"),
        # Comandos de juegos
        BotCommand("cinematrivia", "Inicia una trivia de películas"),
        BotCommand("adivinapelicula", "Inicia el juego Adivina la Película"),
        BotCommand("emojipelicula", "Inicia el juego Emoji Película"),
        # Comandos de autorización (si los quieres mantener, si no, elimínalos)
        BotCommand("solicitarautorizacion", "Solicita autorización para el grupo"),
        BotCommand("aprobar_grupo", "Aprobar solicitud de grupo (solo admins)"),
        BotCommand("ver_solicitudes", "Ver solicitudes pendientes (solo admins)"),
        BotCommand("status_auth", "Ver estado de autorización del chat."),
        # Estos comandos (status, ping, config, stats, broadcast_message) no están en comandos_basicos.py
        # Si existen como funciones, deben definirse o importarse.
        # Asumo que pueden ser administrativos y usen auth_required.
        BotCommand("status", "Estado actual del bot (solo admins)"),
        BotCommand("ping", "Comprueba la latencia del bot (solo admins)"),
        BotCommand("config", "Configura el bot (solo admins)"),
        BotCommand("stats", "Estadísticas del bot (solo admins)"),
        BotCommand("broadcast_message", "Envía un mensaje a todos los chats (solo admins)"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Comandos del bot establecidos.")

    await initialize_db()
    logger.info("Base de datos inicializada.")

    # YA NO SE LLAMA A setup_admin_list() AQUI porque no existe en sistema_autorizacion.py
    # Y ADMIN_USER_ID es hardcodeado allí.

    # También llama a create_auth_tables para la DB de autorización
    await create_auth_tables()
    logger.info("Tablas de autorización inicializadas.")


async def main():
    load_env()

    TOKEN = os.environ.get('TOKEN')
    if not TOKEN:
        logger.error("No se encontró el TOKEN del bot en las variables de entorno.")
        return

    application = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    # Comandos básicos (algunos con autenticación)
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("id", auth_required(cmd_id)))
    application.add_handler(CommandHandler("echo", auth_required(cmd_echo)))
    application.add_handler(CommandHandler("saludar", cmd_saludar))
    application.add_handler(CommandHandler("rules", cmd_rules))
    application.add_handler(CommandHandler("about", cmd_about))
    application.add_handler(CommandHandler("info", cmd_info))
    application.add_handler(CommandHandler("contacto", cmd_contacto))
    application.add_handler(CommandHandler("links", cmd_links))
    application.add_handler(CommandHandler("donate", cmd_donate))
    application.add_handler(CommandHandler("github", cmd_github))
    application.add_handler(CommandHandler("version", cmd_version))

    # Comandos de utilidad (generalmente auth_required)
    # Estas funciones deben definirse o importarse de 'utils.py'
    # y si son comandos, deben tener su propia función asíncrona.
    # Los ejemplos aquí asumen que las funciones de 'utils.py' son directamente comandos.
    application.add_handler(CommandHandler("meme", auth_required(get_random_meme_url)))
    application.add_handler(CommandHandler("crypto", auth_required(get_crypto_price)))
    application.add_handler(CommandHandler("weather", auth_required(fetch_weather)))
    application.add_handler(CommandHandler("exchange", auth_required(get_exchange_rate)))
    application.add_handler(CommandHandler("youtube", auth_required(get_youtube_video_info)))
    application.add_handler(CommandHandler("joke", auth_required(get_joke)))
    application.add_handler(CommandHandler("fact", auth_required(get_random_fact)))

    # Comandos de juegos
    application.add_handler(CommandHandler("cinematrivia", auth_required(cmd_cinematrivia)))
    application.add_handler(CommandHandler("adivinapelicula", auth_required(cmd_adivinapelicula)))
    application.add_handler(CommandHandler("emojipelicula", auth_required(cmd_emojipelicula)))

    # Comandos de autorización (si los quieres mantener, si no, elimínalos junto con sus importaciones)
    application.add_handler(CommandHandler("solicitarautorizacion", cmd_solicitar_autorizacion)) # Este no suele ser auth_required
    application.add_handler(CommandHandler("aprobar_grupo", auth_required(cmd_aprobar_grupo)))
    application.add_handler(CommandHandler("ver_solicitudes", auth_required(cmd_ver_solicitudes)))
    application.add_handler(CommandHandler("status_auth", auth_required(cmd_status_auth)))


    # Otros comandos administrativos que no están en comandos_basicos.py
    # Deben existir como funciones o importarse de otro módulo.
    # Aquí los dejo con auth_required asumiendo que son admin.
    # Si no tienes estas funciones, tendrías que definirlas o eliminarlas.
    # Por ejemplo, si tienes un cmd_status en db.py o utils.py:
    # from db import cmd_status (ejemplo)
    async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.effective_chat.send_message("Bot está activo y funcionando.")

    async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.effective_chat.send_message("Pong!")

    async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.effective_chat.send_message("Comando de configuración (en desarrollo).")

    async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.effective_chat.send_message("Comando de estadísticas (en desarrollo).")

    async def cmd_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.effective_chat.send_message("Comando de broadcast (en desarrollo).")


    application.add_handler(CommandHandler("status", auth_required(cmd_status)))
    application.add_handler(CommandHandler("ping", auth_required(cmd_ping)))
    application.add_handler(CommandHandler("config", auth_required(cmd_config)))
    application.add_handler(CommandHandler("stats", auth_required(cmd_stats)))
    application.add_handler(CommandHandler("broadcast_message", auth_required(cmd_broadcast_message)))


    # Manejadores de callbacks
    application.add_handler(CallbackQueryHandler(handle_trivia_callback))

    # Manejador de mensajes de texto (NO COMANDOS)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))


    logger.info("Bot iniciado. Presiona Ctrl+C para detener.")
    await application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
