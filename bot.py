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
    require_authorization,
    cmd_solicitar_autorizacion, 
    cmd_aprobar_grupo, 
    cmd_ver_solicitudes,
    cmd_addadmin,
    cmd_removeadmin,
    cmd_listadmins,
    cmd_revocar_grupo,
    handle_authorization_callback
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
        BotCommand("topjugadores", "Ranking global de juegos"),
        BotCommand("addadmin", "Agregar nuevo administrador"),
        BotCommand("removeadmin", "Remover administrador"),
        BotCommand("listadmins", "Listar administradores"),
        BotCommand("revocar", "Revocar autorización de grupo"),
        BotCommand("solicitudes", "Ver solicitudes pendientes")
    ]
    await application.bot.set_my_commands(commands)
    asyncio.create_task(cleanup_games_periodically())

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    import traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    logger.error(f"Exception while handling an update: {tb_string}")

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN no encontrado en variables de entorno")
        return

    create_tables()
    create_auth_tables()
    initialize_games_system()

    app = ApplicationBuilder().token(token).post_init(post_init).build()
    app.add_error_handler(error_handler)

    app.add_handler(CommandHandler("solicitar", cmd_solicitar_autorizacion))
    app.add_handler(CommandHandler("aprobar", cmd_aprobar_grupo))
    app.add_handler(CommandHandler("solicitudes", cmd_ver_solicitudes))
    app.add_handler(CommandHandler("addadmin", cmd_addadmin))
    app.add_handler(CommandHandler("removeadmin", cmd_removeadmin))
    app.add_handler(CommandHandler("listadmins", cmd_listadmins))
    app.add_handler(CommandHandler("revocar", cmd_revocar_grupo))
    app.add_handler(CallbackQueryHandler(handle_authorization_callback))

    app.add_handler(CommandHandler("start", require_authorization(cmd_start)))
    app.add_handler(CommandHandler("help", require_authorization(cmd_help)))
    app.add_handler(CommandHandler("ranking", require_authorization(cmd_ranking)))
    app.add_handler(CommandHandler("miperfil", require_authorization(cmd_miperfil)))
    app.add_handler(CommandHandler("reto", require_authorization(cmd_reto)))
    app.add_handler(CommandHandler("cinematrivia", require_authorization(cmd_cinematrivia)))
    app.add_handler(CommandHandler("adivinapelicula", require_authorization(cmd_adivinapelicula)))
    app.add_handler(CommandHandler("emojipelicula", require_authorization(cmd_emojipelicula)))
    app.add_handler(CommandHandler("pista", require_authorization(cmd_pista)))
    app.add_handler(CommandHandler("rendirse", require_authorization(cmd_rendirse)))
    app.add_handler(CommandHandler("estadisticasjuegos", require_authorization(cmd_estadisticasjuegos)))
    app.add_handler(CommandHandler("topjugadores", require_authorization(cmd_top_jugadores)))

    hashtag_filter = filters.TEXT & ~filters.COMMAND & filters.Regex(r'#\w+')
    app.add_handler(MessageHandler(hashtag_filter, require_authorization(handle_hashtags)))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, require_authorization(handle_game_message)))
    app.add_handler(CallbackQueryHandler(handle_trivia_callback))

    if os.environ.get("DEVELOPMENT"):
        app.run_polling(drop_pending_updates=True)
    else:
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
            app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
