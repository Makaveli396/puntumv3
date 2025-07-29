#!/usr/bin/env python3

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
        print("❌ Error: BOT_TOKEN no está definido.")
        exit()

async def route_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in active_games or chat_id in active_trivias:
        await handle_game_message(update, context)
    else:
        await handle_hashtags(update, context)

async def on_startup(app: Application):
    print("✅ Inicializando sistema de juegos...")
    initialize_games_system()
    print("🤖 Bot listo para recibir comandos.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Comandos básicos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("ranking", cmd_ranking))
    app.add_handler(CommandHandler("miperfil", cmd_miperfil))
    app.add_handler(CommandHandler("reto", cmd_reto))

    # Comandos de juegos
    app.add_handler(CommandHandler("cinematrivia", cmd_cinematrivia))
    app.add_handler(CommandHandler("adivinapelicula", cmd_adivinapelicula))
    app.add_handler(CommandHandler("emojipelicula", cmd_emojipelicula))
    app.add_handler(CommandHandler("pista", cmd_pista))
    app.add_handler(CommandHandler("rendirse", cmd_rendirse))

    # Callback de botones
    app.add_handler(CallbackQueryHandler(handle_trivia_callback))

    # Manejador de texto general
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text_message))

    # Correr el bot con función de arranque
    app.run_polling(on_startup=on_startup)

if __name__ == "__main__":
    main()
