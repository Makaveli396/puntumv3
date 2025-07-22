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
    create_auth_tables, 
    is_chat_authorized, 
    authorize_chat,
    auth_required, 
    cmd_solicitar_autorizacion, 
    cmd_aprobar_grupo, 
    cmd_ver_solicitudes,
    cmd_addadmin,
    cmd_removeadmin,
    cmd_listadmins,
    cmd_revocar,
    setup_admin_list
)
from comandos_basicos import (
    cmd_start, cmd_help, cmd_ranking, cmd_miperfil, cmd_reto
)
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
        # Comandos básicos
        BotCommand("start", "Iniciar bot y ver bienvenida"),
        BotCommand("help", "Ayuda y guía completa"),
        BotCommand("ranking", "Ver top 10 usuarios"),
        BotCommand("miperfil", "Ver mi perfil y estadísticas"),
        BotCommand("reto", "Ver reto diario"),
        
        # Comandos de autorización
        BotCommand("solicitar", "Solicitar autorización (solo grupos)"),
        
        # Comandos de juegos
        BotCommand("cinematrivia", "Trivia de películas"),
        BotCommand("adivinapelicula", "Adivina por pistas"),
        BotCommand("emojipelicula", "Adivina por emojis"),
        BotCommand("pista", "Pedir pista en juego activo"),
        BotCommand("rendirse", "Rendirse en juego activo"),
        BotCommand("estadisticasjuegos", "Ver tus estadísticas de juegos"),
        BotCommand("topjugadores", "Ranking global de juegos"),
        
        # Comandos administrativos (solo para admins)
        BotCommand("addadmin", "Agregar nuevo administrador"),
        BotCommand("removeadmin", "Remover administrador"),
        BotCommand("listadmins", "Listar administradores"),
        BotCommand("revocar", "Revocar autorización de grupo"),
        BotCommand("solicitudes", "Ver solicitudes pendientes")
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ Comandos del bot configurados")
    
    # Iniciar tareas periódicas
    asyncio.create_task(cleanup_games_periodically())
    logger.info("✅ Tarea de limpieza de juegos iniciada")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejar errores del bot"""
    import traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    logger.error(f"Exception while handling an update: {tb_string}")

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN no encontrado en variables de entorno")
        return

    logger.info("🤖 Iniciando bot...")
    logger.info(f"🔑 Token configurado: {token[:10]}...")

    # ======================
    #  INICIALIZACIÓN DE SISTEMAS
    # ======================
    create_tables()
    create_auth_tables()
    initialize_games_system()
    logger.info("✅ Sistemas de base de datos inicializados")

    # ======================
    #  CONFIGURACIÓN DE LA APLICACIÓN
    # ======================
    app = ApplicationBuilder().token(token).post_init(post_init).build()
    app.add_error_handler(error_handler)

    # ======================
    #  MANEJADORES DE COMANDOS
    # ======================

    # --- Comandos de autorización ---
    app.add_handler(CommandHandler("solicitar", cmd_solicitar_autorizacion))
    
    # --- Comandos administrativos (con decorador correcto) ---
    app.add_handler(CommandHandler("aprobar", cmd_aprobar_grupo))
    app.add_handler(CommandHandler("solicitudes", cmd_ver_solicitudes))
    app.add_handler(CommandHandler("addadmin", cmd_addadmin))
    app.add_handler(CommandHandler("removeadmin", cmd_removeadmin))
    app.add_handler(CommandHandler("listadmins", cmd_listadmins))
    app.add_handler(CommandHandler("revocar", cmd_revocar))

    # --- Comandos básicos (con decorador de autorización) ---
    app.add_handler(CommandHandler("start", auth_required()(cmd_start)))
    app.add_handler(CommandHandler("help", auth_required()(cmd_help)))
    app.add_handler(CommandHandler("ranking", auth_required()(cmd_ranking)))
    app.add_handler(CommandHandler("miperfil", auth_required()(cmd_miperfil)))
    app.add_handler(CommandHandler("reto", auth_required()(cmd_reto)))

    # --- Comandos de juegos (con decorador de autorización) ---
    app.add_handler(CommandHandler("cinematrivia", auth_required()(cmd_cinematrivia)))
    app.add_handler(CommandHandler("adivinapelicula", auth_required()(cmd_adivinapelicula)))
    app.add_handler(CommandHandler("emojipelicula", auth_required()(cmd_emojipelicula)))
    app.add_handler(CommandHandler("pista", auth_required()(cmd_pista)))
    app.add_handler(CommandHandler("rendirse", auth_required()(cmd_rendirse)))
    app.add_handler(CommandHandler("estadisticasjuegos", auth_required()(cmd_estadisticasjuegos)))
    app.add_handler(CommandHandler("topjugadores", auth_required()(cmd_top_jugadores)))

    # ======================
    #  MANEJADORES DE MENSAJES
    # ======================
    
    # Manejador de hashtags (prioridad alta)
    hashtag_filter = filters.TEXT & ~filters.COMMAND & filters.Regex(r'#\w+')
    app.add_handler(MessageHandler(hashtag_filter, auth_required()(handle_hashtags)))
    logger.info("✅ Manejador de hashtags configurado")
    
    # Manejadores de callbacks y mensajes (baja prioridad)
    app.add_handler(CallbackQueryHandler(handle_trivia_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auth_required()(handle_game_message)))
    logger.info("✅ Manejadores de mensajes configurados")

    # ======================
    #  INICIO DEL BOT
    # ======================
    if os.environ.get("DEVELOPMENT"):
        logger.info("🔄 Modo desarrollo - usando polling")
        app.run_polling(drop_pending_updates=True)
    else:
        logger.info("🌐 Modo producción - usando webhook")
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
            logger.info("🔄 Fallback a polling debido a error en webhook")
            app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
