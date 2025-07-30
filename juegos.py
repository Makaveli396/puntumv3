from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, Application
import logging
from typing import Dict, Any
import random
import time
import asyncio
import json
from db import add_points, get_connection
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

        cursor.execute("DELETE FROM active_games")
        for chat_id, data in active_games.items():
            cursor.execute(
                "INSERT INTO active_games (chat_id, juego, respuesta, pistas, intentos, started_by, last_activity) VALUES (%s, %s, %s, %s, %s, %s, %s)",
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
                "INSERT INTO active_trivias (chat_id, pregunta, respuesta, start_time, started_by) VALUES (%s, %s, %s, %s, %s)",
                (
                    chat_id,
                    data.get('pregunta'),
                    data.get('respuesta'),
                    data.get('start_time'),
                    data.get('started_by')
                )
            )

        conn.commit()
        conn.close()
        logger.info("Juegos activos guardados en la BD")
    except Exception as e:
        logger.error(f"Error guardando juegos activos: {e}")

def load_active_games_from_db():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT chat_id, juego, respuesta, pistas, intentos, started_by, last_activity FROM active_games")
        for row in cursor.fetchall():
            active_games[row[0]] = {
                'juego': row[1],
                'respuesta': row[2],
                'pistas': json.loads(row[3]) if row[3] else [],
                'intentos': row[4],
                'started_by': row[5],
                'last_activity': row[6]
            }

        cursor.execute("SELECT chat_id, pregunta, respuesta, start_time, started_by FROM active_trivias")
        for row in cursor.fetchall():
            active_trivias[row[0]] = {
                'pregunta': row[1],
                'respuesta': row[2],
                'start_time': row[3],
                'started_by': row[4]
            }

        conn.close()
        logger.info("Juegos activos cargados desde la BD")
    except Exception as e:
        logger.error(f"Error cargando juegos activos: {e}")

async def cleanup_games_periodically():
    while True:
        await asyncio.sleep(3600)
        current_time = time.time()

        for chat_id in list(active_games.keys()):
            if current_time - active_games[chat_id].get('last_activity', 0) > 7200:
                del active_games[chat_id]
                logger.info(f"Juego inactivo eliminado en chat {chat_id}")

        for chat_id in list(active_trivias.keys()):
            if current_time - active_trivias[chat_id].get('start_time', 0) > 7200:
                del active_trivias[chat_id]
                logger.info(f"Trivia inactiva eliminada en chat {chat_id}")

        save_active_games_to_db()

async def cmd_cinematrivia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id in active_trivias:
        await update.message.reply_text("¡Ya hay una trivia activa en este chat!")
        return

    try:
        pregunta, respuesta = generar_pregunta()
        if not pregunta or not respuesta:
            await update.message.reply_text("❌ No se pudo generar la pregunta. Intenta más tarde.")
            return

        active_trivias[chat_id] = {
            'pregunta': pregunta,
            'respuesta': respuesta,
            'start_time': time.time(),
            'started_by': user.id
        }

        save_active_games_to_db()

        # Crear botones para respuestas múltiples (opcional)
        keyboard = [
            [InlineKeyboardButton("Responder por texto", callback_data="text_answer")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"🎬 TRIVIA CINEMATOGRÁFICA 🍿\n\n{pregunta}\n\nTienes 60 segundos para responder. ¡Buena suerte!",
            reply_markup=reply_markup
        )

        await asyncio.sleep(60)
        if chat_id in active_trivias:
            respuesta_correcta = active_trivias[chat_id]['respuesta']
            del active_trivias[chat_id]
            save_active_games_to_db()
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⌛ ¡Tiempo agotado! La respuesta correcta era: {respuesta_correcta}"
            )

    except Exception as e:
        logger.error(f"Error en trivia: {e}")
        await update.message.reply_text("Ocurrió un error al generar la trivia. Intenta más tarde.")

async def cmd_adivinapelicula(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id in active_games:
        await update.message.reply_text("¡Ya hay un juego activo en este chat!")
        return

    peliculas = [
        ("El Padrino", ["película de mafia de 1972 dirigida por Francis Ford Coppola", "protagonizada por Marlon Brando", "es considerada una de las mejores películas de la historia"]),
        ("Titanic", ["película romántica de 1997 sobre un barco que se hunde", "dirigida por James Cameron", "protagonizada por Leonardo DiCaprio y Kate Winslet"]),
        ("Star Wars", ["película de ciencia ficción con jedis y sables de luz", "creada por George Lucas", "la saga comenzó en 1977"]),
        ("El Señor de los Anillos", ["trilogía de fantasía con hobbits y un anillo", "basada en la obra de J.R.R. Tolkien", "dirigida por Peter Jackson"])
    ]

    pelicula, todas_las_pistas = random.choice(peliculas)
    active_games[chat_id] = {
        'juego': 'adivinapelicula',
        'respuesta': pelicula,
        'pistas': todas_las_pistas,
        'pistas_dadas': 0,
        'intentos': 0,
        'started_by': user.id,
        'last_activity': time.time()
    }

    save_active_games_to_db()

    await update.message.reply_text(
        f"🎬 ADIVINA LA PELÍCULA 🍿\n\nEstoy pensando en una película...\n"
        f"Pista 1: {todas_las_pistas[0]}\n\n"
        f"Responde con el título de la película. ¡Tienes 5 intentos!\n"
        f"Usa /pista para obtener más pistas o /rendirse para terminar el juego."
    )

async def cmd_emojipelicula(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id in active_games:
        await update.message.reply_text("¡Ya hay un juego activo en este chat!")
        return

    emoji_peliculas = {
        "🦁👑": "El Rey León", 
        "👽📞": "E.T.", 
        "👻🚫": "Cazafantasmas",
        "🦈🎶": "Tiburón", 
        "🧙‍♂️⚡": "Harry Potter", 
        "🧛‍♂️💍": "El Señor de los Anillos",
        "🚀👨‍🚀": "Apollo 13", 
        "🦸‍♂️🦇": "Batman", 
        "👩‍🚀🌌": "Interstellar",
        "🐟🔍": "Buscando a Nemo",
        "🏰👸": "La Bella y la Bestia",
        "🦖🌴": "Jurassic Park"
    }

    emojis, respuesta = random.choice(list(emoji_peliculas.items()))
    active_games[chat_id] = {
        'juego': 'emojipelicula',
        'respuesta': respuesta,
        'emojis': emojis,
        'pistas': [],
        'intentos': 0,
        'started_by': user.id,
        'last_activity': time.time()
    }

    save_active_games_to_db()

    await update.message.reply_text(
        f"🎬 ADIVINA LA PELÍCULA POR EMOJIS 🍿\n\n"
        f"¿Qué película es esta? {emojis}\n\n"
        f"Responde con el título exacto de la película. ¡Tienes 5 intentos!\n"
        f"Usa /rendirse si quieres terminar el juego."
    )

# ======= FUNCIONES FALTANTES =======

async def cmd_pista(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando para obtener pistas adicionales en juegos activos"""
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in active_games:
        await update.message.reply_text("❌ No hay ningún juego activo en este chat.")
        return

    game_data = active_games[chat_id]
    
    if game_data['juego'] == 'adivinapelicula':
        pistas_disponibles = game_data.get('pistas', [])
        pistas_dadas = game_data.get('pistas_dadas', 0)
        
        if pistas_dadas >= len(pistas_disponibles):
            await update.message.reply_text("❌ Ya se han dado todas las pistas disponibles.")
            return
        
        # Dar la siguiente pista
        siguiente_pista = pistas_disponibles[pistas_dadas]
        game_data['pistas_dadas'] = pistas_dadas + 1
        game_data['last_activity'] = time.time()
        
        save_active_games_to_db()
        
        await update.message.reply_text(
            f"💡 PISTA {pistas_dadas + 2}: {siguiente_pista}\n\n"
            f"Pistas restantes: {len(pistas_disponibles) - pistas_dadas - 1}"
        )
    
    elif game_data['juego'] == 'emojipelicula':
        await update.message.reply_text(
            "❌ En el juego de emojis no hay pistas adicionales. "
            "¡Los emojis ya son la pista principal!"
        )
    
    else:
        await update.message.reply_text("❌ Este juego no admite pistas adicionales.")

async def cmd_rendirse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando para rendirse en un juego activo"""
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in active_games and chat_id not in active_trivias:
        await update.message.reply_text("❌ No hay ningún juego activo en este chat.")
        return

    # Manejar rendición en juegos regulares
    if chat_id in active_games:
        game_data = active_games[chat_id]
        respuesta_correcta = game_data['respuesta']
        tipo_juego = game_data['juego']
        
        del active_games[chat_id]
        save_active_games_to_db()
        
        mensaje = f"🏳️ ¡Te has rendido!\n\n"
        if tipo_juego == 'adivinapelicula':
            mensaje += f"La película era: **{respuesta_correcta}**"
        elif tipo_juego == 'emojipelicula':
            emojis = game_data.get('emojis', '')
            mensaje += f"La película {emojis} era: **{respuesta_correcta}**"
        
        await update.message.reply_text(mensaje)

    # Manejar rendición en trivias
    elif chat_id in active_trivias:
        trivia_data = active_trivias[chat_id]
        respuesta_correcta = trivia_data['respuesta']
        
        del active_trivias[chat_id]
        save_active_games_to_db()
        
        await update.message.reply_text(
            f"🏳️ ¡Te has rendido en la trivia!\n\n"
            f"La respuesta correcta era: **{respuesta_correcta}**"
        )

async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejar mensajes de texto cuando hay juegos activos"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    mensaje = update.message.text.strip().lower()

    # Manejar respuestas de trivia
    if chat_id in active_trivias:
        trivia_data = active_trivias[chat_id]
        respuesta_correcta = trivia_data['respuesta'].lower()
        
        if mensaje == respuesta_correcta:
            del active_trivias[chat_id]
            save_active_games_to_db()
            
            # Dar puntos al usuario
            add_points(user.id, user.first_name, 10)
            
            await update.message.reply_text(
                f"🎉 ¡CORRECTO! 🎉\n\n"
                f"La respuesta era: **{trivia_data['respuesta']}**\n"
                f"¡Has ganado 10 puntos! 🌟"
            )
            return
        else:
            await update.message.reply_text("❌ Respuesta incorrecta. ¡Sigue intentando!")
            return

    # Manejar respuestas de juegos regulares
    if chat_id in active_games:
        game_data = active_games[chat_id]
        respuesta_correcta = game_data['respuesta'].lower()
        
        # Incrementar intentos
        game_data['intentos'] += 1
        game_data['last_activity'] = time.time()
        
        # Verificar respuesta
        if mensaje == respuesta_correcta:
            puntos = max(15 - game_data['intentos'] * 2, 5)  # Más puntos con menos intentos
            
            del active_games[chat_id]
            save_active_games_to_db()
            
            # Dar puntos al usuario
            add_points(user.id, user.first_name, puntos)
            
            mensaje_victoria = f"🎉 ¡CORRECTO! 🎉\n\n"
            mensaje_victoria += f"La respuesta era: **{game_data['respuesta']}**\n"
            mensaje_victoria += f"Intentos usados: {game_data['intentos']}\n"
            mensaje_victoria += f"¡Has ganado {puntos} puntos! 🌟"
            
            await update.message.reply_text(mensaje_victoria)
            return
        
        # Respuesta incorrecta
        intentos_restantes = 5 - game_data['intentos']
        
        if intentos_restantes <= 0:
            # Se acabaron los intentos
            respuesta_real = game_data['respuesta']
            del active_games[chat_id]
            save_active_games_to_db()
            
            await update.message.reply_text(
                f"❌ ¡Se acabaron los intentos!\n\n"
                f"La respuesta correcta era: **{respuesta_real}**\n"
                f"¡Mejor suerte la próxima vez! 🍀"
            )
        else:
            save_active_games_to_db()
            await update.message.reply_text(
                f"❌ Respuesta incorrecta.\n"
                f"Te quedan {intentos_restantes} intentos. ¡Sigue intentando!"
            )

async def handle_trivia_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejar callbacks de botones en trivias"""
    query = update.callback_query
    await query.answer()
    
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
    "cleanup_games_periodically",
    "active_games",
    "active_trivias"
]