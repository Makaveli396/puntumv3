#!/usr/bin/env python3

import os
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
    Application
)
from telegram import Update

# Importar desde comandos_basicos.py
from comandos_basicos import (
    cmd_start,
    cmd_help,
    cmd_ranking,
    cmd_miperfil,
    cmd_reto,
)

# Importar desde hashtags.py
from hashtags import handle_hashtags

# Importar desde juegos.py
from juegos import (
    cmd_cinematrivia,
    cmd_adivinapelicula,
    cmd_emojipelicula,
    cmd_pista,
    cmd_rendirse,
    handle_game_message,
    handle_trivia_callback,
    initialize_games_system,
    active_games,
    active_trivias
)

# Importar sistema de autorización
from sistema_autorizacion import (
    create_auth_tables,
    auth_required,
    cmd_solicitar_autorizacion,
    cmd_aprobar_grupo,
    cmd_ver_solicitudes,
    cmd_status_auth
)

# Importar configuración
try:
    from config import Config
    BOT_TOKEN = Config.BOT_TOKEN
except (ImportError, AttributeError):
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    if not BOT_TOKEN:
        print("❌ Error: BOT_TOKEN no está definido.")
        exit()

async def route_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enrutar mensajes de texto según el contexto"""
    chat_id = update.effective_chat.id
    
    # Si hay juegos activos, manejar primero
    if chat_id in active_games or chat_id in active_trivias:
        await handle_game_message(update, context)
    else:
        # Si no hay juegos, procesar hashtags
        await handle_hashtags(update, context)

async def initialize_bot():
    """Función para inicializar el bot"""
    print("🔧 Creando tablas de base de datos...")
    from db import create_tables
    create_tables()
    
    print("🔐 Creando tablas de autorización...")
    create_auth_tables()
    
    print("🎮 Inicializando sistema de juegos...")
    initialize_games_system()
    
    print("🤖 Bot listo para recibir comandos.")

def main():
    """Función principal del bot"""
    # Crear aplicación
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ======= COMANDOS BÁSICOS =======
    app.add_handler(CommandHandler("start", auth_required(cmd_start)))
    app.add_handler(CommandHandler("help", auth_required(cmd_help)))
    app.add_handler(CommandHandler("ranking", auth_required(cmd_ranking)))
    app.add_handler(CommandHandler("miperfil", auth_required(cmd_miperfil)))
    app.add_handler(CommandHandler("reto", auth_required(cmd_reto)))

    # ======= COMANDOS DE JUEGOS =======
    app.add_handler(CommandHandler("cinematrivia", auth_required(cmd_cinematrivia)))
    app.add_handler(CommandHandler("adivinapelicula", auth_required(cmd_adivinapelicula)))
    app.add_handler(CommandHandler("emojipelicula", auth_required(cmd_emojipelicula)))
    app.add_handler(CommandHandler("pista", auth_required(cmd_pista)))
    app.add_handler(CommandHandler("rendirse", auth_required(cmd_rendirse)))

    # ======= COMANDOS DE AUTORIZACIÓN =======
    app.add_handler(CommandHandler("solicitar", cmd_solicitar_autorizacion))
    app.add_handler(CommandHandler("aprobar", cmd_aprobar_grupo))
    app.add_handler(CommandHandler("solicitudes", cmd_ver_solicitudes))
    app.add_handler(CommandHandler("statusauth", cmd_status_auth))

    # ======= MANEJADORES DE EVENTOS =======
    # Callback queries (botones)
    app.add_handler(CallbackQueryHandler(handle_trivia_callback))

    # Mensajes de texto (hashtags y juegos)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        auth_required(route_text_message)
    ))

    # ======= EJECUTAR BOT =======
    print("🚀 Iniciando bot...")
    
    # Inicializar bot de forma síncrona
    import asyncio
    asyncio.run(initialize_bot())
    
    # Ejecutar bot
    app.run_polling()

if __name__ == "__main__":
    main()