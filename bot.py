#!/usr/bin/env python3

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes
)
from telegram import Update

# Importa los comandos básicos
from comandos_basicos import (
    cmd_start,
    cmd_help,
    cmd_ranking,
    cmd_miperfil,
    cmd_reto,
    handle_hashtags,  # Se usará en el enrutador
)

# Importa las funciones y estados de los juegos
from juegos import (
    cmd_cinematrivia,
    cmd_adivinapelicula,
    cmd_emojipelicula,
    cmd_pista,
    cmd_rendirse,
    handle_game_message,
    handle_trivia_callback,
    initialize_games_system,
    active_games,      # Necesario para el enrutador
    active_trivias     # Necesario para el enrutador
)

# Asumimos que tienes un archivo config.py para el token
# O que usas variables de entorno
try:
    from config import Config
    BOT_TOKEN = Config.BOT_TOKEN
except (ImportError, AttributeError):
    import os
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    if not BOT_TOKEN:
        print("Error: El token del bot no está configurado. Créalo en un archivo config.py o como variable de entorno 'BOT_TOKEN'.")
        exit()

# --- NUEVA FUNCIÓN ENRUTADORA ---
async def route_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Revisa si un mensaje es para un juego activo; si no, lo pasa al manejador de hashtags.
    """
    chat_id = update.effective_chat.id
    
    # Prioridad 1: Si hay un juego activo, el mensaje es una respuesta.
    if chat_id in active_games or chat_id in active_trivias:
        await handle_game_message(update, context)
    # Prioridad 2: Si no hay juego, procesar como un mensaje que puede tener hashtags.
    else:
        await handle_hashtags(update, context)

async def post_init(application: Application):
    """Función para ejecutar tareas después de que el bot se inicialice."""
    print("✅ Post-init completado. Inicializando sistema de juegos...")
    initialize_games_system()
    print("🤖 Bot iniciado y listo para recibir comandos.")

def main():
    """Función principal para configurar y correr el bot."""
    if not BOT_TOKEN:
        return

    # Construcción de la aplicación
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # --- REGISTRO DE MANEJADORES ---

    # 1. Comandos básicos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("ranking", cmd_ranking))
    app.add_handler(CommandHandler("miperfil", cmd_miperfil))
    app.add_handler(CommandHandler("reto", cmd_reto))

    # 2. Comandos de juegos
    app.add_handler(CommandHandler("cinematrivia", cmd_cinematrivia))
    app.add_handler(CommandHandler("adivinapelicula", cmd_adivinapelicula))
    app.add_handler(CommandHandler("emojipelicula", cmd_emojipelicula))
    app.add_handler(CommandHandler("pista", cmd_pista))
    app.add_handler(CommandHandler("rendirse", cmd_rendirse))

    # 3. Manejador de callbacks para botones (ej. trivia)
    app.add_handler(CallbackQueryHandler(handle_trivia_callback))

    # 4. Manejador unificado para todos los mensajes de texto (¡LA CLAVE DE LA CORRECCIÓN!)
    # Este manejador debe ir después de todos los CommandHandlers.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text_message))

    # Iniciar el bot
    app.run_polling()

if __name__ == "__main__":
    main()