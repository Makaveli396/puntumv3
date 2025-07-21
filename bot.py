#!/usr/bin/env python3

import os
import logging
import sqlite3
import asyncio
from datetime import datetime
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from db import create_tables, add_points, get_user_stats, get_top10
from juegos import (
    initialize_games_system,
    cleanup_games_periodically,
    cmd_cinematrivia,
    cmd_adivinapelicula,
    cmd_emojipelicula,
    cmd_pista,
    cmd_rendirse,
    cmd_estadisticasjuegos,
    cmd_top_jugadores,
    handle_trivia_callback,
    handle_game_message
)
from sistema_autorizacion import (
    create_auth_tables, is_chat_authorized, authorize_chat,
    auth_required, cmd_solicitar_autorizacion, cmd_aprobar_grupo, cmd_ver_solicitudes
)
from comandos_basicos import (
    cmd_start, cmd_help, cmd_ranking, cmd_miperfil, cmd_reto
)
# IMPORTACIÓN CORREGIDA: Importar handle_hashtags desde hashtags.py
from hashtags import handle_hashtags

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def post_init(application):
    """Configurar comandos y tareas después de inicializar la aplicación"""
    commands = [
        BotCommand("start", "Iniciar bot y ver bienvenida"),
        BotCommand("help", "Ayuda y guía completa"),
        BotCommand("ranking", "Ver top 10 usuarios"),
        BotCommand("miperfil", "Ver mi perfil y estadísticas"),
        BotCommand("reto", "Ver reto diario"),
        BotCommand("solicitar", "Solicitar autorización (solo grupos)"),
        BotCommand("cinematrivia", "Trivia de películas"),
        BotCommand("adivinapelicula", "Adivina por pistas"),
        BotCommand("emojipelicula", "Adivina por emojis"),
        BotCommand("pista", "Pedir pista en juego activo"),
        BotCommand("rendirse", "Rendirse en juego activo"),
        BotCommand("estadisticasjuegos", "Ver tus estadísticas de juegos"),
        BotCommand("topjugadores", "Ranking global de juegos")
    ]
    await application.bot.set_my_commands(commands)
    print("[INFO] ✅ Comandos del bot configurados")
    
    # Crear la tarea de limpieza aquí, dentro del loop de eventos
    asyncio.create_task(cleanup_games_periodically())
    print("[INFO] ✅ Tarea de limpieza de juegos iniciada")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejar errores del bot"""
    import traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    logger.error(f"Exception while handling an update: {tb_string}")

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("[ERROR] BOT_TOKEN no encontrado en variables de entorno")
        return

    print(f"[INFO] 🤖 Iniciando bot...")
    print(f"[INFO] 🔑 Token configurado: {token[:10]}...")

    # Inicializar base de datos y sistemas
    create_tables()
    create_auth_tables()
    initialize_games_system()

    # Crear aplicación
    app = ApplicationBuilder().token(token).post_init(post_init).build()

    # Agregar manejador de errores
    app.add_error_handler(error_handler)

    # Comandos de autorización
    app.add_handler(CommandHandler("solicitar", cmd_solicitar_autorizacion))
    app.add_handler(CommandHandler("aprobar", cmd_aprobar_grupo))
    app.add_handler(CommandHandler("solicitudes", cmd_ver_solicitudes))
    
    # Comandos básicos (requieren autorización)
    app.add_handler(CommandHandler("start", auth_required(cmd_start)))
    app.add_handler(CommandHandler("help", auth_required(cmd_help)))
    app.add_handler(CommandHandler("ranking", auth_required(cmd_ranking)))
    app.add_handler(CommandHandler("miperfil", auth_required(cmd_miperfil)))
    app.add_handler(CommandHandler("reto", auth_required(cmd_reto)))

    # Comandos de juegos (requieren autorización)
    app.add_handler(CommandHandler("cinematrivia", auth_required(cmd_cinematrivia)))
    app.add_handler(CommandHandler("adivinapelicula", auth_required(cmd_adivinapelicula)))
    app.add_handler(CommandHandler("emojipelicula", auth_required(cmd_emojipelicula)))
    app.add_handler(CommandHandler("pista", auth_required(cmd_pista)))
    app.add_handler(CommandHandler("rendirse", auth_required(cmd_rendirse)))
    app.add_handler(CommandHandler("estadisticasjuegos", auth_required(cmd_estadisticasjuegos)))
    app.add_handler(CommandHandler("topjugadores", auth_required(cmd_top_jugadores)))
    
    # MANEJADOR DE HASHTAGS - DEBE IR ANTES que handle_game_message
    # para que tenga prioridad en el procesamiento
    hashtag_filter = filters.TEXT & ~filters.COMMAND & filters.Regex(r'#\w+')
    app.add_handler(MessageHandler(hashtag_filter, auth_required(handle_hashtags)))
    print("[INFO] ✅ Manejador de hashtags configurado")
    
    # Manejadores de callbacks y mensajes (van después)
    app.add_handler(CallbackQueryHandler(handle_trivia_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auth_required(handle_game_message)))

    print("[INFO] ✅ Todos los handlers configurados")

    # Ejecutar en modo desarrollo o producción
    if os.environ.get("DEVELOPMENT"):
        print("[INFO] 🔄 Modo desarrollo - usando polling")
        app.run_polling(drop_pending_updates=True)
    else:
        print("[INFO] 🌐 Modo producción - usando webhook")
        webhook_url = f"{os.environ.get('RENDER_EXTERNAL_URL', '')}/webhook"
        
        try:
            app.run_webhook(
                listen="0.0.0.0",
                port=int(os.environ.get("PORT", 8000)),
                webhook_url=webhook_url,
                url_path="/webhook",
                drop_pending_updates=True
            )
        except Exception as e:
            logger.error(f"Error configurando webhook: {e}")
            print("[INFO] 🔄 Fallback a polling debido a error en webhook")
            app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
