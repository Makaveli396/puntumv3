from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)
from comandos_basicos import (
    cmd_start,
    cmd_help,
    cmd_ranking,
    cmd_miperfil,
    cmd_reto,
    handle_hashtags,
)
from config import Config

async def post_init(application): # Esta es la línea corregida
    print("✅ Post-init completado")

def main():
    Config.validate_config()
    token = Config.BOT_TOKEN

    app = ApplicationBuilder().token(token).post_init(post_init).build()

    # Comandos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("ranking", cmd_ranking))
    app.add_handler(CommandHandler("miperfil", cmd_miperfil))
    app.add_handler(CommandHandler("reto", cmd_reto))

    # Mensajes normales con hashtags
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hashtags))

    print("🤖 Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()