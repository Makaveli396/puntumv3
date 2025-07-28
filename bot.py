from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler # Añadido para manejar botones de juegos
)
from comandos_basicos import (
    cmd_start,
    cmd_help,
    cmd_ranking,
    cmd_miperfil,
    cmd_reto,
    handle_hashtags,
)
from juegos import ( # Importa las funciones de juegos
    cmd_cinematrivia,
    cmd_adivinapelicula,
    cmd_emojipelicula,
    cmd_pista,
    cmd_rendirse,
    handle_game_message,
    handle_trivia_callback,
    initialize_games_system # Posiblemente para inicializar al arrancar
)
from config import Config

async def post_init(application):
    print("✅ Post-init completado")
    # Opcional: inicializar el sistema de juegos aquí si es necesario
    initialize_games_system()

def main():
    Config.validate_config()
    token = Config.BOT_TOKEN

    app = ApplicationBuilder().token(token).post_init(post_init).build()

    # Comandos básicos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("ranking", cmd_ranking))
    app.add_handler(CommandHandler("miperfil", cmd_miperfil))
    app.add_handler(CommandHandler("reto", cmd_reto))

    # Comandos de juegos (¡AÑADIDOS AQUÍ!)
    app.add_handler(CommandHandler("cinematrivia", cmd_cinematrivia))
    app.add_handler(CommandHandler("adivinapelicula", cmd_adivinapelicula))
    app.add_handler(CommandHandler("emojipelicula", cmd_emojipelicula))
    app.add_handler(CommandHandler("pista", cmd_pista))
    app.add_handler(CommandHandler("rendirse", cmd_rendirse))

    # Manejadores de mensajes para juegos (si un juego está activo y requiere una respuesta de texto)
    # Este manejador debe ir DESPUÉS de los CommandHandlers de juegos
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_game_message))
    
    # Manejador de callbacks de botones para juegos (ej. trivia)
    app.add_handler(CallbackQueryHandler(handle_trivia_callback))

    # Mensajes normales con hashtags (este debe ir DESPUÉS de los manejadores de juegos que procesan texto)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hashtags))


    print("🤖 Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()