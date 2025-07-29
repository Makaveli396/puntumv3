#!/usr/bin/env python3

import asyncio
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

from comandos_basicos import (
    cmd_start,
    cmd_help,
    cmd_ranking,
    cmd_miperfil,
    cmd_reto,
    handle_hashtags,
)
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

try:
    from config import Config
    BOT_TOKEN = Config.BOT_TOKEN
except (ImportError, AttributeError):
    import os
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    if not BOT_TOKEN:
        print("Error: El token del bot no está configurado. Usa config.py o la variable de entorno BOT_TOKEN.")
        exit()

async def route_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in active_games or chat_id in active_trivias:
        await handle_game_message(update, context)
    else:
        await handle_hashtags(update, context)

async def post_init(application: Application):
    print("✅ Post-init completado. Inicializando sistema de juegos...")
    initialize_games_system()
    print("🤖 Bot iniciado y listo para recibir comandos.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Registro de comandos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("ranking", cmd_ranking))
    app.add_handler(CommandHandler("miperfil", cmd_miperfil))
    app.add_handler(CommandHandler("reto", cmd_reto))

    # Juegos
    app.add_handler(CommandHandler("cinematrivia", cmd_cinematrivia))
    app.add_handler(CommandHandler("adivinapelicula", cmd_adivinapelicula))
    app.add_handler(CommandHandler("emojipelicula", cmd_emojipelicula))
    app.add_handler(CommandHandler("pista", cmd_pista))
    app.add_handler(CommandHandler("rendirse", cmd_rendirse))

    app.add_handler(CallbackQueryHandler(handle_trivia_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text_message))

    await post_init(app)
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
