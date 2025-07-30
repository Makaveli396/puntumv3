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

# Configurar logging
import logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Cargar configuración del bot - MEJORADO
def load_config():
    """Carga la configuración del bot desde archivo o variables de entorno"""
    bot_token = None
    admin_user_id = None
    
    # Intentar cargar desde config.py primero
    try:
        from config import Config
        bot_token = getattr(Config, 'BOT_TOKEN', None)
        admin_user_id = getattr(Config, 'ADMIN_USER_ID', None)
        logger.info("✅ Configuración cargada desde config.py")
    except (ImportError, AttributeError) as e:
        logger.info("📁 No se encontró config.py, usando variables de entorno")
    
    # Si no se encuentra en config.py, usar variables de entorno
    if not bot_token:
        bot_token = os.environ.get("BOT_TOKEN")
    
    if not admin_user_id:
        admin_user_id = os.environ.get("ADMIN_USER_ID")
    
    # Validar BOT_TOKEN
    if not bot_token or bot_token.strip() == "":
        logger.error("❌ Error crítico: BOT_TOKEN no está definido o está vacío.")
        logger.error("💡 Soluciones:")
        logger.error("   1. Crea un archivo config.py con: class Config: BOT_TOKEN = 'tu_token_aqui'")
        logger.error("   2. O configura la variable de entorno BOT_TOKEN")
        exit(1)
    
    # Validar formato del token (básico)
    if not bot_token.count(':') == 1 or len(bot_token) < 30:
        logger.error("❌ Error: BOT_TOKEN no tiene el formato correcto de Telegram")
        logger.error("💡 El token debe tener el formato: 123456789:ABCdefGHIjklMNOpqrSTUvwxyz")
        exit(1)
    
    # Convertir ADMIN_USER_ID a int si existe
    if admin_user_id:
        try:
            admin_user_id = int(admin_user_id)
        except ValueError:
            logger.warning("⚠️ ADMIN_USER_ID no es un número válido, se ignorará")
            admin_user_id = None
    
    if not admin_user_id:
        logger.warning("⚠️ ADMIN_USER_ID no está definido. Algunas funciones de administración no estarán disponibles.")
    
    logger.info(f"✅ BOT_TOKEN cargado (longitud: {len(bot_token)})")
    if admin_user_id:
        logger.info(f"✅ ADMIN_USER_ID configurado: {admin_user_id}")
    
    return bot_token, admin_user_id

# Cargar configuración
BOT_TOKEN, ADMIN_USER_ID = load_config()

# Clase de servidor HTTP para mantener el servicio activo en Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        response = f"""
        <html>
        <body>
        <h1>🤖 Puntum Bot Status</h1>
        <p>✅ Bot is running!</p>
        <p>🕒 Status checked at: {os.popen('date').read().strip()}</p>
        <p>🔧 Python version: {os.popen('python3 --version').read().strip()}</p>
        </body>
        </html>
        """
        self.wfile.write(response.encode())
    
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
    
    def log_message(self, format, *args):
        # Silenciar logs del servidor HTTP para reducir spam
        pass

def start_health_check_server(port=10000):
    """Inicia el servidor de health check para Render"""
    try:
        server_address = ('', port)
        httpd = HTTPServer(server_address, HealthCheckHandler)
        logger.info(f"🌐 Servidor de Health Check iniciado en puerto {port}")
        httpd.serve_forever()
    except Exception as e:
        logger.error(f"❌ Error en servidor de health check: {e}")

async def initialize_bot():
    """Inicializa el bot: crea tablas, carga estados, etc."""
    logger.info("🔄 Inicializando componentes del bot...")

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
        logger.info("✅ Tablas de la base de datos verificadas/creadas.")

    except Exception as e:
        logger.error(f"❌ Error durante la inicialización de la base de datos: {e}")
        if conn:
            conn.rollback() # Asegúrate de hacer rollback en caso de error
    finally:
        if conn:
            conn.close()

    # Inicializar el sistema de juegos (carga datos de la DB)
    try:
        initialize_games_system()
        logger.info("✅ Sistema de juegos inicializado.")
    except Exception as e:
        logger.error(f"❌ Error inicializando sistema de juegos: {e}")

    # Iniciar el chequeo de juegos activos en segundo plano
    try:
        import juegos
        asyncio.create_task(juegos.check_active_games())
        logger.info("✅ Tarea de chequeo de juegos activos programada.")
    except Exception as e:
        logger.error(f"❌ Error programando chequeo de juegos: {e}")

def main() -> None:
    """Función principal del bot"""
    logger.info("🚀 Iniciando Puntum Bot...")
    
    # VERIFICACIÓN ADICIONAL: Asegurar que BOT_TOKEN esté disponible
    logger.info(f"🔍 Verificando BOT_TOKEN antes de crear aplicación...")
    logger.info(f"🔍 BOT_TOKEN disponible: {BOT_TOKEN is not None}")
    logger.info(f"🔍 BOT_TOKEN longitud: {len(BOT_TOKEN) if BOT_TOKEN else 'None'}")
    
    if not BOT_TOKEN:
        logger.error("❌ Error crítico: BOT_TOKEN es None en main()")
        exit(1)
    
    # Iniciar el servidor de health check en un hilo separado
    health_check_port = int(os.environ.get("PORT", 10000))
    health_thread = threading.Thread(
        target=start_health_check_server, 
        args=(health_check_port,),
        daemon=True  # El hilo se cerrará cuando el programa principal termine
    )
    health_thread.start()
    logger.info(f"🌐 Servidor de Health Check iniciado en hilo separado en puerto {health_check_port}")

    # Construir la aplicación del bot
    try:
        logger.info(f"🔧 Creando ApplicationBuilder con token de longitud {len(BOT_TOKEN)}")
        app = ApplicationBuilder.token(BOT_TOKEN).build()
        logger.info("✅ Aplicación de Telegram creada exitosamente")
    except Exception as e:
        logger.error(f"❌ Error creando aplicación de Telegram: {e}")
        logger.error(f"🔍 BOT_TOKEN en el momento del error: {type(BOT_TOKEN)} - {BOT_TOKEN is not None}")
        exit(1)

    # ======= MANEJADORES DE COMANDOS =======
    try:
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
        
        logger.info("✅ Todos los manejadores de comandos registrados")
        
    except Exception as e:
        logger.error(f"❌ Error registrando manejadores: {e}")
        exit(1)

    # ======= EJECUTAR BOT =======
    logger.info("🤖 Bot configurado, iniciando polling...")
    
    try:
        # Crear el loop de eventos de forma más robusta
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Ejecutar la inicialización en el loop
        loop.run_until_complete(initialize_bot())
        
        logger.info("🎯 Iniciando polling del bot...")
        # Ejecutar bot con configuración mejorada
        app.run_polling(
            poll_interval=1.0,  # Intervalo de polling
            timeout=10,         # Timeout para requests
            bootstrap_retries=-1, # Reintentos infinitos en bootstrap
            read_timeout=30,    # Timeout de lectura
            write_timeout=30,   # Timeout de escritura
            connect_timeout=30  # Timeout de conexión
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot detenido por el usuario (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Error crítico ejecutando el bot: {e}")
        logger.error("💡 Verifica que:")
        logger.error("   1. Tu BOT_TOKEN sea válido")
        logger.error("   2. Tengas conexión a internet")
        logger.error("   3. Todos los módulos estén instalados")
        exit(1)

if __name__ == "__main__":
    main()