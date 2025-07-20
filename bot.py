# bot.py
import os
import logging
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

# Importaciones de tus módulos locales
from sistema_autorizacion import (
    create_auth_tables, is_chat_authorized, authorize_chat,
    auth_required, cmd_solicitar_autorizacion, cmd_aprobar_grupo, cmd_ver_solicitudes,
    cmd_status_auth # Asegúrate de que cmd_status_auth también esté si lo usas
)
from comandos_basicos import (
    cmd_start, cmd_help, cmd_id, cmd_saludar, cmd_rules,
    cmd_about, cmd_info, cmd_contacto, cmd_links, cmd_donate,
    cmd_github, cmd_version, cmd_status, cmd_ping,
    cmd_config, cmd_stats, cmd_broadcast_message
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
    cmd_adivinapelicula, cmd_emojipelicula, handle_game_message, # Mantén estos si los usas
    handle_trivia_callback # Si lo usas para la trivia
)

# IMPORTANTE: Importar generar_pregunta directamente desde generador_trivia.py
# porque está en la misma carpeta.
from generador_trivia import generar_pregunta 

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Diccionario para almacenar el estado de la trivia por chat
# Reemplazamos 'active_trivias' por datos en context.chat_data para una mejor gestión de estado por chat.
# Se eliminará la variable global active_trivias para usar solo context.chat_data


# --- Comandos Administrativos (auth_required) ---
# ... (Mantén tus comandos administrativos aquí) ...

# --- Comandos de Usuario ---
# ... (Mantén tus comandos de usuario aquí) ...

# --- Funciones de Comandos de Juegos ---
# Modificamos cmd_cinematrivia para usar generar_pregunta
async def cmd_cinematrivia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia una nueva trivia de películas."""
    if not update.effective_chat:
        return

    chat_id = update.effective_chat.id

    # Comprobar si ya hay una trivia activa en este chat
    if 'active_trivia_answer' in context.chat_data:
        await update.effective_chat.send_message(
            "Ya hay una trivia de películas activa en este chat. ¡Responde la pregunta actual!"
        )
        return

    try:
        pregunta, respuesta_correcta = generar_pregunta()
        if respuesta_correcta == "Error": # Manejo de errores de generar_pregunta
             await update.effective_chat.send_message(pregunta)
             return

        # Almacenar la pregunta y respuesta en context.chat_data para este chat
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

        # Lógica para manejar respuestas de trivia (AHORA VA AQUÍ)
        # Se verifica si hay una trivia activa en este chat
        if 'active_trivia_answer' in context.chat_data:
            user_response = update.message.text.lower().strip()
            expected_answer = context.chat_data['active_trivia_answer']

            if user_response == expected_answer:
                await update.effective_chat.send_message(
                    f"🎉 ¡Correcto, {update.effective_user.first_name}! La respuesta era '{expected_answer.title()}'."
                )
                # Opcional: añadir puntos al usuario
                # await add_points(user_id, 10) 
                
                # Eliminar la trivia activa del chat_data
                del context.chat_data['active_trivia_question']
                del context.chat_data['active_trivia_answer']
                return # Importante: el mensaje ha sido manejado por la trivia
            # Si la respuesta es incorrecta, el bot no dice nada para no "spammear".
            # Puedes añadir un mensaje de "incorrecto, intenta de nuevo" si lo deseas.
            # else:
            #     await update.effective_chat.send_message(
            #         f"❌ Incorrecto, {update.effective_user.first_name}. ¡Sigue intentando!"
            #     )
            # return # Si quieres que el mensaje de respuesta de trivia no sea procesado por otros manejadores


    # Si el mensaje no fue una respuesta de trivia, o no era texto, o era un comando,
    # entonces puede ser procesado por otros manejadores.
    # Por ejemplo, si tienes un handle_game_message general en juegos.py,
    # este se llamaría después de que la lógica de trivia haya fallado en reconocer el mensaje.
    # Si quieres que handle_game_message maneje también otras respuestas de juegos (adivina, emoji),
    # asegúrate de que su lógica no interfiera con la de la trivia o viceversa.
    await handle_game_message(update, context) # Llama a tu manejador general de mensajes de juegos


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
        BotCommand("status", "Estado actual del bot"),
        BotCommand("ping", "Comprueba la latencia del bot"),
        BotCommand("config", "Configura el bot (solo admins)"),
        BotCommand("stats", "Estadísticas del bot"),
        BotCommand("broadcast_message", "Envía un mensaje a todos los chats (solo admins)"),
        # Comandos de utilidad
        BotCommand("meme", "Obtén un meme aleatorio"),
        BotCommand("crypto", "Obtén el precio de una criptomoneda (ej. /crypto BTC)"),
        BotCommand("weather", "Obtén el clima de una ciudad (ej. /weather Madrid)"),
        BotCommand("exchange", "Obtén tasa de cambio (ej. /exchange USD EUR)"),
        BotCommand("youtube", "Obtén info de video de YouTube (ej. /youtube <URL>)"),
        BotCommand("joke", "Obtén un chiste aleatorio"),
        BotCommand("fact", "Obtén un dato curioso aleatorio"),
        # Comandos de juegos
        BotCommand("cinematrivia", "Inicia una trivia de películas"), # AÑADIDO
        BotCommand("adivinapelicula", "Inicia el juego Adivina la Película"),
        BotCommand("emojipelicula", "Inicia el juego Emoji Película"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Comandos del bot establecidos.")
    
    # Inicializar la base de datos
    await initialize_db()
    logger.info("Base de datos inicializada.")

    # Cargar lista de administradores
    await setup_admin_list()
    logger.info("Lista de administradores cargada.")

async def main():
    load_env() # Cargar variables de entorno

    TOKEN = os.environ.get('TOKEN')
    if not TOKEN:
        logger.error("No se encontró el TOKEN del bot en las variables de entorno.")
        return

    application = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    # --- Registra tus handlers aquí ---

    # Comandos básicos (algunos con autenticación)
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("id", auth_required(cmd_id)))
    application.add_handler(CommandHandler("saludar", cmd_saludar))
    application.add_handler(CommandHandler("rules", cmd_rules))
    application.add_handler(CommandHandler("about", cmd_about))
    application.add_handler(CommandHandler("info", cmd_info))
    application.add_handler(CommandHandler("contacto", cmd_contacto))
    application.add_handler(CommandHandler("links", cmd_links))
    application.add_handler(CommandHandler("donate", cmd_donate))
    application.add_handler(CommandHandler("github", cmd_github))
    application.add_handler(CommandHandler("version", cmd_version))
    application.add_handler(CommandHandler("status", auth_required(cmd_status)))
    application.add_handler(CommandHandler("ping", auth_required(cmd_ping)))
    application.add_handler(CommandHandler("config", auth_required(cmd_config)))
    application.add_handler(CommandHandler("stats", auth_required(cmd_stats)))
    application.add_handler(CommandHandler("broadcast_message", auth_required(cmd_broadcast_message)))
    
    # Comandos de utilidad
    application.add_handler(CommandHandler("meme", auth_required(get_random_meme_url)))
    application.add_handler(CommandHandler("crypto", auth_required(get_crypto_price)))
    application.add_handler(CommandHandler("weather", auth_required(fetch_weather)))
    application.add_handler(CommandHandler("exchange", auth_required(get_exchange_rate)))
    application.add_handler(CommandHandler("youtube", auth_required(get_youtube_video_info)))
    application.add_handler(CommandHandler("joke", auth_required(get_joke)))
    application.add_handler(CommandHandler("fact", auth_required(get_random_fact)))

    # Comandos de juegos
    application.add_handler(CommandHandler("cinematrivia", auth_required(cmd_cinematrivia))) # Usa la nueva función
    application.add_handler(CommandHandler("adivinapelicula", auth_required(cmd_adivinapelicula)))
    application.add_handler(CommandHandler("emojipelicula", auth_required(cmd_emojipelicula)))

    # Manejadores de callbacks
    application.add_handler(CallbackQueryHandler(handle_trivia_callback)) # Si usas botones para trivia

    # Manejador de mensajes de texto (NO COMANDOS)
    # Este manejador debe ir al final o su lógica debe ser muy cuidadosa
    # para no interferir con otros handlers (ej. trivia).
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))


    logger.info("Bot iniciado. Presiona Ctrl+C para detener.")
    await application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
