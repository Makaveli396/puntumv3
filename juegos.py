# juegos.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, Application
import logging
from typing import Dict, Any
import random
import time
import asyncio
import json
import telegram # Asegúrate de importar telegram para usar telegram.error.BadRequest

from db import add_points, get_connection # Importar get_connection también
from generador_trivia import generar_pregunta

logger = logging.getLogger(__name__)

active_games: Dict[int, Dict[str, Any]] = {}
active_trivias: Dict[int, Dict[str, Any]] = {}

def initialize_games_system():
    logger.info("Sistema de juegos inicializado")
    load_active_games_from_db()

def save_active_games_to_db():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Para PostgreSQL, usa %s como marcador de posición
        # Y asegúrate de que 'respuesta' esté en la definición de la tabla en db.py
        if conn.info.dsn.startswith("host=") if hasattr(conn, 'info') else False: # Detectar PostgreSQL
            cursor.execute("DELETE FROM active_games")
            for chat_id, data in active_games.items():
                cursor.execute(
                    """INSERT INTO active_games (chat_id, juego, respuesta, pistas, intentos, started_by, last_activity)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        chat_id,
                        data.get('juego'),
                        data.get('respuesta'),
                        json.dumps(data.get('pistas', [])),
                        data.get('intentos', 0),
                        data.get('started_by'),
                        data.get('last_activity')
                    )
                )

            cursor.execute("DELETE FROM active_trivias")
            for chat_id, data in active_trivias.items():
                cursor.execute(
                    """INSERT INTO active_trivias (chat_id, pregunta, respuesta, start_time, opciones, message_id, inline_keyboard_message_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        chat_id,
                        data.get('pregunta'),
                        data.get('respuesta'),
                        data.get('start_time'),
                        json.dumps(data.get('opciones', [])),
                        data.get('message_id'),
                        data.get('inline_keyboard_message_id')
                    )
                )
        else: # SQLite
            cursor.execute("DELETE FROM active_games")
            for chat_id, data in active_games.items():
                cursor.execute(
                    """INSERT INTO active_games (chat_id, juego, respuesta, pistas, intentos, started_by, last_activity)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        chat_id,
                        data.get('juego'),
                        data.get('respuesta'),
                        json.dumps(data.get('pistas', [])),
                        data.get('intentos', 0),
                        data.get('started_by'),
                        data.get('last_activity')
                    )
                )

            cursor.execute("DELETE FROM active_trivias")
            for chat_id, data in active_trivias.items():
                cursor.execute(
                    """INSERT INTO active_trivias (chat_id, pregunta, respuesta, start_time, opciones, message_id, inline_keyboard_message_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        chat_id,
                        data.get('pregunta'),
                        data.get('respuesta'),
                        data.get('start_time'),
                        json.dumps(data.get('opciones', [])),
                        data.get('message_id'),
                        data.get('inline_keyboard_message_id')
                    )
                )
        
        conn.commit()
    except Exception as e:
        logger.error(f"Error guardando juegos activos: {e}")
    finally:
        if conn:
            conn.close()

def load_active_games_from_db():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        global active_games, active_trivias
        active_games = {}
        active_trivias = {}

        # Cargar juegos activos
        if conn.info.dsn.startswith("host=") if hasattr(conn, 'info') else False: # Detectar PostgreSQL
            cursor.execute("SELECT chat_id, juego, respuesta, pistas, intentos, started_by, last_activity FROM active_games")
        else: # SQLite
            cursor.execute("SELECT chat_id, juego, respuesta, pistas, intentos, started_by, last_activity FROM active_games")
        
        rows = cursor.fetchall()
        for row in rows:
            chat_id, juego, respuesta, pistas_json, intentos, started_by, last_activity = row
            active_games[chat_id] = {
                'juego': juego,
                'respuesta': respuesta,
                'pistas': json.loads(pistas_json) if pistas_json else [],
                'intentos': intentos,
                'started_by': started_by,
                'last_activity': last_activity # PostgreSQL timestamp ya es un objeto datetime
            }
            # Asegúrate de que last_activity se maneje correctamente si es un string en SQLite
            if not (conn.info.dsn.startswith("host=") if hasattr(conn, 'info') else False) and isinstance(last_activity, str):
                active_games[chat_id]['last_activity'] = datetime.strptime(last_activity, '%Y-%m-%d %H:%M:%S.%f')
            
        # Cargar trivias activas
        if conn.info.dsn.startswith("host=") if hasattr(conn, 'info') else False: # Detectar PostgreSQL
            cursor.execute("SELECT chat_id, pregunta, respuesta, start_time, opciones, message_id, inline_keyboard_message_id FROM active_trivias")
        else: # SQLite
            cursor.execute("SELECT chat_id, pregunta, respuesta, start_time, opciones, message_id, inline_keyboard_message_id FROM active_trivias")
        
        rows = cursor.fetchall()
        for row in rows:
            chat_id, pregunta, respuesta, start_time, opciones_json, message_id, inline_keyboard_message_id = row
            active_trivias[chat_id] = {
                'pregunta': pregunta,
                'respuesta': respuesta,
                'start_time': start_time,
                'opciones': json.loads(opciones_json) if opciones_json else [],
                'message_id': message_id,
                'inline_keyboard_message_id': inline_keyboard_message_id
            }
        
    except Exception as e:
        logger.error(f"Error cargando juegos activos: {e}")
    finally:
        if conn:
            conn.close()

async def check_active_games():
    """Función para revisar juegos activos y limpiar los inactivos."""
    current_time = time.time()
    games_to_remove = []
    
    for chat_id, game_data in active_games.items():
        # Para PostgreSQL, last_activity es un objeto datetime, convertir a timestamp
        last_activity_timestamp = game_data['last_activity'].timestamp() if isinstance(game_data['last_activity'], datetime) else game_data['last_activity']
        
        if current_time - last_activity_timestamp > 3600:  # 1 hora de inactividad
            games_to_remove.append(chat_id)

    for chat_id in games_to_remove:
        logger.info(f"Juego en chat {chat_id} removido por inactividad.")
        del active_games[chat_id]
    
    # También revisa trivias activas
    trivias_to_remove = []
    for chat_id, trivia_data in active_trivias.items():
        if current_time - trivia_data['start_time'] > 600: # 10 minutos para trivias
            trivias_to_remove.append(chat_id)
    
    for chat_id in trivias_to_remove:
        logger.info(f"Trivia en chat {chat_id} removida por inactividad.")
        del active_trivias[chat_id]
        # Opcional: intentar editar el mensaje para indicar que la trivia terminó
        # if 'message_id' in trivia_data:
        #     try:
        #         await context.bot.edit_message_text(
        #             chat_id=chat_id,
        #             message_id=trivia_data['message_id'],
        #             text="La trivia ha caducado por inactividad."
        #         )
        #     except Exception as e:
        #         logger.warning(f"No se pudo editar el mensaje de trivia caducada: {e}")

    if games_to_remove or trivias_to_remove:
        save_active_games_to_db() # Guarda los cambios si se eliminaron juegos/trivias
    
    # Programar la próxima revisión
    await asyncio.sleep(600)  # Revisa cada 10 minutos
    await check_active_games()


async def cmd_cinematrivia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id in active_games:
        await update.message.reply_text("Ya hay un juego activo en este chat. Usa /rendirse para terminarlo.")
        return

    logger.info(f"Generando pregunta de cinematrivia para chat {chat_id}")
    pregunta, respuesta = generar_pregunta()

    if not pregunta or not respuesta or respuesta == "Error":
        await update.message.reply_text("❌ No se pudo generar la pregunta. Intenta más tarde.")
        logger.error(f"Fallo al generar pregunta de trivia para chat {chat_id}: Pregunta='{pregunta}', Respuesta='{respuesta}'")
        return

    active_games[chat_id] = {
        'juego': 'cinematrivia',
        'respuesta': respuesta.lower(),  # Convertir a minúsculas para comparación sin distinción de mayúsculas
        'pistas': [],
        'intentos': 0,
        'started_by': user_id,
        'last_activity': datetime.now() # Usar datetime.now() para PostgreSQL y SQLite
    }
    save_active_games_to_db()

    keyboard = [[InlineKeyboardButton("Responder por texto", callback_data="text_answer")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🎬 **¡Nueva Cinematrivia!** 🍿\n\n{pregunta}\n\n"
        "🤔 ¡Adivina la respuesta! Tienes 5 intentos.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def cmd_adivinapelicula(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Comando /adivinapelicula aún no implementado.")

async def cmd_emojipelicula(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Comando /emojipelicula aún no implementado.")

async def cmd_pista(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    
    if chat_id not in active_games:
        await update.message.reply_text("No hay ningún juego activo en este chat para dar una pista.")
        return

    game_data = active_games[chat_id]
    if game_data['juego'] != 'cinematrivia':
        await update.message.reply_text("Las pistas solo están disponibles para Cinematrivia en este momento.")
        return
    
    # Lógica para dar una pista (ej. revelar una letra)
    respuesta = game_data['respuesta']
    pistas = game_data.get('pistas', [])
    
    if len(pistas) >= len(respuesta) / 2: # Límite de pistas
        await update.message.reply_text("Ya he dado suficientes pistas. ¡Esfuérzate un poco más!")
        return

    # Generar una nueva pista
    letras_reveladas = [c if c in pistas else '_' for c in respuesta]
    
    # Encontrar una letra no revelada para dar una pista
    posiciones_no_reveladas = [i for i, char in enumerate(respuesta) if char not in pistas and char.isalpha()]

    if not posiciones_no_reveladas:
        await update.message.reply_text("No hay más letras para revelar como pista.")
        return
    
    pista_char = random.choice(posiciones_no_reveladas)
    pistas.append(respuesta[pista_char])
    active_games[chat_id]['pistas'] = pistas
    save_active_games_to_db()
    
    letras_reveladas = [c if c in pistas else '_' for c in respuesta]
    pista_actual = " ".join(letras_reveladas)

    await update.message.reply_text(f"Aquí tienes una pista: `{pista_actual}`", parse_mode='Markdown')


async def cmd_rendirse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    if chat_id in active_games:
        game_data = active_games.pop(chat_id)
        save_active_games_to_db()
        respuesta_correcta = game_data.get('respuesta', 'N/A')
        await update.message.reply_text(f"Has abandonado el juego actual. La respuesta era: **{respuesta_correcta}**", parse_mode='Markdown')
    elif chat_id in active_trivias:
        trivia_data = active_trivias.pop(chat_id)
        save_active_games_to_db()
        respuesta_correcta = trivia_data.get('respuesta', 'N/A')
        await update.message.reply_text(f"Has abandonado la trivia actual. La respuesta era: **{respuesta_correcta}**", parse_mode='Markdown')
    else:
        await update.message.reply_text("No hay ningún juego o trivia activa en este chat.")


async def route_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ruta los mensajes de texto a los manejadores de juego o hashtags."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text

    # Primero, verificar si hay un juego activo y si es una respuesta
    if chat_id in active_games and user_id != context.bot.id: # Asegurarse de que el bot no se responda a sí mismo
        game_data = active_games[chat_id]
        if game_data['juego'] == 'cinematrivia':
            await handle_game_message(update, context)
            return
    
    # Si no es una respuesta de juego, procesar hashtags
    await handle_hashtags(update, context)


async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_answer = update.message.text.lower().strip() # Convertir a minúsculas y quitar espacios
    
    if chat_id not in active_games:
        return # No hay juego activo para este chat

    game_data = active_games[chat_id]
    game_data['last_activity'] = datetime.now() # Actualizar actividad
    
    if game_data['juego'] == 'cinematrivia':
        correct_answer = game_data['respuesta'].lower().strip()

        if user_answer == correct_answer:
            add_points(user_id, chat_id, 10, update.effective_user.username, update.effective_chat.title, "Cinematrivia Correcta", update.message.message_id)
            del active_games[chat_id] # Eliminar juego activo
            save_active_games_to_db()
            await update.message.reply_text(
                f"🎉 **¡Correcto!** 🎉\n\n"
                f"¡Felicidades, {update.effective_user.mention_html()}! Has adivinado la película: **{correct_answer.title()}**\n"
                "Has ganado 10 puntos. 🌟",
                parse_mode='HTML'
            )
        else:
            game_data['intentos'] += 1
            # Lógica para respuesta incorrecta
            intentos_restantes = 5 - game_data['intentos']
            
            if intentos_restantes <= 0:
                # Se acabaron los intentos
                respuesta_real = game_data['respuesta']
                del active_games[chat_id]
                save_active_games_to_db()
                
                await update.message.reply_text(
                    f"❌ ¡Se acabaron los intentos!\\n\\n"\
                    f"La respuesta correcta era: **{respuesta_real.title()}**\\n"\
                    f"¡Mejor suerte la próxima vez! 🍀",
                    parse_mode='Markdown'
                )
            else:
                save_active_games_to_db()
                await update.message.reply_text(
                    f"❌ Respuesta incorrecta.\\n"\
                    f"Te quedan {intentos_restantes} intentos. ¡Sigue intentando!"
                )

async def handle_trivia_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejar callbacks de botones en trivias"""
    query = update.callback_query
    
    try:
        await query.answer() # Intenta responder al callback
    except telegram.error.BadRequest as e:
        logger.warning(f"Error al responder al callback query (quizás ya caducó): {e}")
        # Puedes optar por no hacer nada, o enviar un mensaje al usuario indicando que la interacción caducó
        # await query.edit_message_text("Esta interacción ha caducado. Por favor, inicia una nueva trivia.")
        return # Salir si el callback ya caducó
    
    if query.data == "text_answer":
        await query.edit_message_text(
            text=query.message.text + "\n\n✏️ Responde escribiendo tu respuesta como mensaje de texto."
        )

# Actualizar __all__ para incluir las nuevas funciones
__all__ = [
    "cmd_cinematrivia",
    "cmd_adivinapelicula", 
    "cmd_emojipelicula",
    "cmd_pista",
    "cmd_rendirse",
    "handle_game_message",
    "handle_trivia_callback",
    "initialize_games_system",
    "active_games",
    "active_trivias",
    "route_text_message" # Asegúrate de que este también esté exportado para que bot.py lo use
]