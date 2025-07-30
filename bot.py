# bot.py
#!/usr/bin/env python3

import os
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
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
    active_trivias,
    route_text_message # Asegúrate de que este también esté exportado
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

# Importar funciones de db.py
from db import (
    create_games_tables, # Cambiado de create_tables
    create_auth_tables,
    create_user_tables,
    get_connection # Necesario para la inicialización
)
from db import get_configured_chats, save_chat_config, get_chat_config # Importar configuración de chats

# Importar configuración
try:
    from config import Config
    BOT_TOKEN = Config.BOT_TOKEN
    ADMIN_USER_ID = Config.ADMIN_USER_ID
except (ImportError, AttributeError):
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID")
    if not BOT_TOKEN:
        print("❌ Error: BOT_TOKEN no está definido.")
        exit()
    if not ADMIN_USER_ID:
        print("❌ Advertencia: ADMIN_USER_ID no está definido. Algunas funciones de administración podrían no estar disponibles.")

# Configurar logging
import logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Clase de servidor HTTP para mantener el servicio activo en Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def start_health_check_server(port=10000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    logger.info(f"Servidor de Health Check iniciado en el puerto {port}")
    httpd.serve_forever()


async def initialize_bot():
    """Inicializa el bot: crea tablas, carga estados, etc."""
    logger.info("Initializing bot components...")

    # Crear conexión para las tablas de la base de datos
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Crear todas las tablas necesarias
        create_auth_tables(conn, cursor) # Llama a la función individual
        create_user_tables(conn, cursor) # Llama a la función individual
        create_games_tables(conn, cursor) # Llama a la función individual
        
        # También crear la tabla de chat_config si no existe
        if os.environ.get('DATABASE_URL'): # PostgreSQL
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_config (
                    chat_id BIGINT PRIMARY KEY,
                    chat_name TEXT,
                    rankings_enabled BOOLEAN DEFAULT TRUE,
                    challenges_enabled BOOLEAN DEFAULT TRUE
                )
            """)
        else: # SQLite
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_config (
                    chat_id INTEGER PRIMARY KEY,
                    chat_name TEXT,
                    rankings_enabled INTEGER DEFAULT 1,
                    challenges_enabled INTEGER DEFAULT 1
                )
            """)
        conn.commit()
        logger.info("Tablas de la base de datos verificadas/creadas.")

    except Exception as e:
        logger.error(f"Error durante la inicialización de la base de datos: {e}")
        if conn:
            conn.rollback() # Asegúrate de hacer rollback en caso de error
    finally:
        if conn:
            conn.close()

    # Inicializar el sistema de juegos (carga datos de la DB)
    initialize_games_system()
    logger.info("Sistema de juegos inicializado.")

    # Iniciar el chequeo de juegos activos en segundo plano
    asyncio.create_task(juegos.check_active_games())
    logger.info("Tarea de chequeo de juegos activos programada.")


def main() -> None:
    # Iniciar el servidor de health check en un hilo separado
    health_check_port = int(os.environ.get("PORT", 10000))
    health_thread = threading.Thread(target=start_health_check_server, args=(health_check_port,))
    health_thread.start()
    logger.info(f"Servidor de Health Check iniciado en hilo separado en puerto {health_check_port}.")

    # Construir la aplicación del bot
    app = ApplicationBuilder.token(BOT_TOKEN).build()

    # ======= MANEJADORES DE COMANDOS =======
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("ranking", cmd_ranking))
    app.add_handler(CommandHandler("miperfil", cmd_miperfil))
    app.add_handler(CommandHandler("reto", cmd_reto))

    # Comandos de juegos
    app.add_handler(CommandHandler("cinematrivia", auth_required(cmd_cinematrivia)))
    app.add_handler(CommandHandler("adivinapelicula", auth_required(cmd_adivinapelicula)))
    app.add_handler(CommandHandler("emojipelicula", auth_required(cmd_emojipelicula)))
    app.add_handler(CommandHandler("pista", auth_required(cmd_pista)))
    app.add_handler(CommandHandler("rendirse", auth_required(cmd_rendirse)))

    # Comandos de autorización
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
    try:
        # Para Render y entornos de producción
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Ejecutar la inicialización en el loop
        loop.run_until_complete(initialize_bot())
        
        # Ejecutar bot
        app.run_polling()
    except RuntimeError as e:
        logger.error(f"Error al iniciar el bucle de eventos principal: {e}")
        # Alternativa para entornos locales (si ya hay un loop corriendo, intentar con get_event_loop)
        try:
            current_loop = asyncio.get_event_loop()
            if current_loop.is_running():
                # Si ya hay un loop, schedule initialize_bot como una tarea
                asyncio.create_task(initialize_bot())
            else:
                # Si no hay un loop, pero RuntimeError fue por otra razón
                current_loop.run_until_complete(initialize_bot())
            app.run_polling()
        except Exception as inner_e:
            logger.error(f"Fallo en la alternativa de inicialización: {inner_e}")
            print("❌ No se pudo iniciar el bot. Verifica los logs para más detalles.")


if __name__ == "__main__":
    main()