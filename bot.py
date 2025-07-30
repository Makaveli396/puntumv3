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

# Servidor HTTP simple para Render
# ... (código anterior)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Bot is running!')
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8') # Añade charset=utf-8
            self.end_headers()
            
            # Codifica el string a bytes usando UTF-8
            html_content = """
            <!DOCTYPE html>
            <html>
            <head><title>Cinema Bot</title></head>
            <body>
                <h1>🎬 Cinema Bot está activo! 🍿</h1>
                <p>Bot de Telegram funcionando correctamente.</p>
            </body>
            </html>
            """
            self.wfile.write(html_content.encode('utf-8')) # .encode('utf-8') aquí
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suprimir logs del servidor HTTP
        pass

# ... (resto del código)

def start_health_server():
    """Inicia servidor HTTP para health checks"""
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"🌐 Servidor HTTP iniciado en puerto {port}")
    server.serve_forever()

async def route_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enrutar mensajes de texto según el contexto"""
    chat_id = update.effective_chat.id
    
    # Si hay juegos activos, manejar primero
    if chat_id in active_games or chat_id in active_trivias:
        await handle_game_message(update, context)
    else:
        # Si no hay juegos, procesar hashtags
        await handle_hashtags(update, context)

def create_games_tables():
    """Crear tablas específicas para juegos"""
    try:
        from db import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # Tabla de juegos activos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_games (
                chat_id BIGINT PRIMARY KEY,
                juego VARCHAR(50),
                respuesta TEXT,
                pistas TEXT,
                intentos INTEGER DEFAULT 0,
                started_by BIGINT,
                last_activity FLOAT
            )
        """)
        
        # Tabla de trivias activas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_trivias (
                chat_id BIGINT PRIMARY KEY,
                pregunta TEXT,
                respuesta TEXT,
                start_time FLOAT,
                started_by BIGINT
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Tablas de juegos creadas")
        
    except Exception as e:
        print(f"❌ Error creando tablas de juegos: {e}")

async def initialize_bot():
    """Función para inicializar el bot"""
    print("🔧 Creando tablas de base de datos...")
    from db import create_tables
    create_tables()
    
    print("🎮 Creando tablas de juegos...")
    create_games_tables()
    
    print("🔐 Creando tablas de autorización...")
    create_auth_tables()
    
    print("🎮 Inicializando sistema de juegos...")
    initialize_games_system()
    
    print("🤖 Bot listo para recibir comandos.")

def main():
    """Función principal del bot"""
    # Iniciar servidor HTTP en thread separado (para Render)
    print("🚀 Iniciando servidor HTTP...")
    http_thread = threading.Thread(target=start_health_server, daemon=True)
    http_thread.start()
    
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
    try:
        # Para Render y entornos de producción
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(initialize_bot())
        
        # Ejecutar bot
        app.run_polling()
    except RuntimeError:
        # Alternativa para entornos locales
        try:
            asyncio.run(initialize_bot())
        except RuntimeError:
            # Si ya hay un loop corriendo
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Crear una nueva tarea
                task = asyncio.create_task(initialize_bot())
                loop.run_until_complete(task)
            else:
                loop.run_until_complete(initialize_bot())
        app.run_polling()

if __name__ == "__main__":
    main()