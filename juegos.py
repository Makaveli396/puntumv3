# juegos.py
from telegram import Update
from telegram.ext import ContextTypes
import logging
from typing import Dict, Any
import random
import asyncio
from db import add_points

logger = logging.getLogger(__name__)

# Estado global para juegos activos
active_games: Dict[int, Dict[str, Any]] = {}
active_trivias: Dict[int, Dict[str, Any]] = {}

def initialize_games_system():
    """Inicializa el sistema de juegos"""
    logger.info("Sistema de juegos inicializado")
    # Puedes agregar aquí cualquier inicialización necesaria

async def cleanup_games_periodically():
    """Limpia juegos inactivos periódicamente"""
    while True:
        await asyncio.sleep(3600)  # Cada hora
        current_time = time.time()
        for chat_id in list(active_games.keys()):
            if current_time - active_games[chat_id].get('last_activity', 0) > 7200:  # 2 horas de inactividad
                del active_games[chat_id]
                logger.info(f"Juego inactivo eliminado en chat {chat_id}")

async def cmd_cinematrivia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Iniciar una trivia cinematográfica"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if chat_id in active_trivias:
        await update.message.reply_text("¡Ya hay una trivia activa en este chat!")
        return
        
    try:
        from generador_trivia import generar_pregunta
        pregunta, respuesta = generar_pregunta()
        
        active_trivias[chat_id] = {
            'pregunta': pregunta,
            'respuesta': respuesta,
            'start_time': time.time(),
            'started_by': user.id
        }
        
        await update.message.reply_text(
            f"🎬 TRIVIA CINEMATOGRÁFICA 🍿\n\n{pregunta}\n\n"
            "Tienes 60 segundos para responder. ¡Buena suerte!"
        )
        
        # Programar finalización automática
        await asyncio.sleep(60)
        if chat_id in active_trivias:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⌛ Tiempo terminado! La respuesta correcta era: {active_trivias[chat_id]['respuesta']}"
            )
            del active_trivias[chat_id]
            
    except Exception as e:
        logger.error(f"Error en trivia: {e}")
        await update.message.reply_text("Ocurrió un error al generar la trivia. Intenta más tarde.")

async def cmd_adivinapelicula(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Implementación de Adivina la Película."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if chat_id in active_games:
        await update.message.reply_text("¡Ya hay un juego activo en este chat!")
        return
        
    # Implementación básica del juego
    peliculas = [
        ("El Padrino", "película de mafia de 1972 dirigida por Francis Ford Coppola"),
        ("Titanic", "película romántica de 1997 sobre un barco que se hunde"),
        ("Star Wars", "película de ciencia ficción con jedis y sables de luz"),
        ("El Señor de los Anillos", "trilogía de fantasía con hobbits y un anillo")
    ]
    
    pelicula, pista = random.choice(peliculas)
    active_games[chat_id] = {
        'juego': 'adivinapelicula',
        'respuesta': pelicula,
        'pistas': [pista],
        'intentos': 0,
        'started_by': user.id,
        'last_activity': time.time()
    }
    
    await update.message.reply_text(
        "🎬 ADIVINA LA PELÍCULA 🍿\n\n"
        "Estoy pensando en una película...\n"
        f"Pista: {pista}\n\n"
        "Responde con el título de la película. ¡Tienes 3 intentos!"
    )

async def cmd_emojipelicula(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Implementación de Emoji Película."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if chat_id in active_games:
        await update.message.reply_text("¡Ya hay un juego activo en este chat!")
        return
        
    # Diccionario de películas y sus representaciones en emoji
    emoji_peliculas = {
        "🦁👑": "El Rey León",
        "👽📞": "E.T.",
        "👻🚫": "Cazafantasmas",
        "🦈🎶": "Tiburón",
        "🧙‍♂️⚡": "Harry Potter",
        "🧛‍♂️💍": "El Señor de los Anillos",
        "🚀👨‍🚀": "Apollo 13",
        "🦸‍♂️🦇": "Batman",
        "👩‍🚀🌌": "Interstellar"
    }
    
    emojis, respuesta = random.choice(list(emoji_peliculas.items()))
    active_games[chat_id] = {
        'juego': 'emojipelicula',
        'respuesta': respuesta,
        'emojis': emojis,
        'intentos': 0,
        'started_by': user.id,
        'last_activity': time.time()
    }
    
    await update.message.reply_text(
        "🎬 ADIVINA LA PELÍCULA POR EMOJIS 🍿\n\n"
        f"¿Qué película es esta? {emojis}\n\n"
        "Responde con el título exacto de la película. ¡Tienes 3 intentos!"
    )

async def cmd_pista(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dar una pista en el juego activo"""
    chat_id = update.effective_chat.id
    
    if chat_id not in active_games:
        await update.message.reply_text("No hay ningún juego activo en este chat.")
        return
        
    game = active_games[chat_id]
    
    if game['juego'] == 'adivinapelicula':
        if len(game['pistas']) > 1:
            await update.message.reply_text("No hay más pistas disponibles.")
        else:
            # Agregar una nueva pista
            nuevas_pistas = {
                "El Padrino": "Protagonizada por Marlon Brando y Al Pacino",
                "Titanic": "Protagonizada por Leonardo DiCaprio y Kate Winslet",
                "Star Wars": "La frase 'Que la fuerza te acompañe' es de esta película",
                "El Señor de los Anillos": "Basada en los libros de J.R.R. Tolkien"
            }
            game['pistas'].append(nuevas_pistas[game['respuesta']])
            await update.message.reply_text(f"Nueva pista: {game['pistas'][1]}")
            
    elif game['juego'] == 'emojipelicula':
        await update.message.reply_text("Lo siento, este juego no tiene pistas adicionales.")

async def cmd_rendirse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Rendirse en el juego actual"""
    chat_id = update.effective_chat.id
    
    if chat_id not in active_games:
        await update.message.reply_text("No hay ningún juego activo en este chat.")
        return
        
    game = active_games[chat_id]
    respuesta = game['respuesta']
    del active_games[chat_id]
    
    await update.message.reply_text(
        f"🏳️ Te has rendido. La respuesta correcta era: {respuesta}\n\n"
        "Puedes iniciar un nuevo juego cuando quieras."
    )

async def cmd_estadisticasjuegos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostrar estadísticas de juegos del usuario"""
    user = update.effective_user
    await update.message.reply_text(
        "📊 Estadísticas de juegos (próximamente)\n\n"
        f"Usuario: {user.first_name}\n"
        "Esta función estará disponible en la próxima actualización."
    )

async def cmd_top_jugadores(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostrar ranking de jugadores"""
    await update.message.reply_text(
        "🏆 Top jugadores (próximamente)\n\n"
        "Esta función estará disponible en la próxima actualización."
    )

async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja mensajes de juegos."""
    if not update.message or not update.message.text:
        return
        
    chat_id = update.effective_chat.id
    user = update.effective_user
    message_text = update.message.text.strip()
    
    # Manejar trivia primero
    if chat_id in active_trivias:
        trivia = active_trivias[chat_id]
        if message_text.lower() == trivia['respuesta'].lower():
            puntos = 10
            add_points(
                user_id=user.id,
                username=user.username or user.first_name,
                points=puntos,
                hashtag="#trivia",
                chat_id=chat_id,
                message_id=update.message.message_id
            )
            await update.message.reply_text(
                f"✅ ¡Correcto {user.first_name}! 🎬\n\n"
                f"Has ganado {puntos} puntos por acertar la trivia.\n\n"
                f"La respuesta era: {trivia['respuesta']}"
            )
            del active_trivias[chat_id]
        return
    
    # Manejar otros juegos
    if chat_id not in active_games:
        return
        
    game = active_games[chat_id]
    game['last_activity'] = time.time()
    
    if message_text.lower() == game['respuesta'].lower():
        puntos = 15 if game['juego'] == 'adivinapelicula' else 10
        add_points(
            user_id=user.id,
            username=user.username or user.first_name,
            points=puntos,
            hashtag=f"#{game['juego']}",
            chat_id=chat_id,
            message_id=update.message.message_id
        )
        await update.message.reply_text(
            f"🎉 ¡Correcto {user.first_name}! 🍿\n\n"
            f"Has acertado la película y ganado {puntos} puntos.\n\n"
            f"La respuesta era: {game['respuesta']}"
        )
        del active_games[chat_id]
    else:
        game['intentos'] += 1
        if game['intentos'] >= 3:
            await update.message.reply_text(
                f"❌ ¡Agotaste tus intentos! La respuesta correcta era: {game['respuesta']}\n\n"
                "Puedes iniciar un nuevo juego cuando quieras."
            )
            del active_games[chat_id]
        else:
            intentos_restantes = 3 - game['intentos']
            if game['juego'] == 'adivinapelicula' and len(game['pistas']) > 1:
                pista = game['pistas'][1]
            else:
                pista = game['pistas'][0] if game['juego'] == 'adivinapelicula' else game['emojis']
                
            await update.message.reply_text(
                f"❌ Incorrecto. Te quedan {intentos_restantes} intentos.\n\n"
                f"Pista: {pista}"
            )

async def handle_trivia_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja callbacks de botones para la trivia."""
    query = update.callback_query
    await query.answer()
    
    # Implementación básica para callbacks (puedes expandir esto)
    await query.edit_message_text(f"Has seleccionado: {query.data}")
