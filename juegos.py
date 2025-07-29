from telegram import Update
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
                "INSERT INTO active_games (chat_id, juego, respuesta, pistas, intentos, started_by, last_activity) VALUES (?, ?, ?, ?, ?, ?, ?)",
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
                "INSERT INTO active_trivias (chat_id, pregunta, respuesta, start_time, started_by) VALUES (?, ?, ?, ?, ?)",
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

        cursor.execute("SELECT * FROM active_games")
        for row in cursor.fetchall():
            active_games[row[0]] = {
                'juego': row[1],
                'respuesta': row[2],
                'pistas': json.loads(row[3]),
                'intentos': row[4],
                'started_by': row[5],
                'last_activity': row[6]
            }

        cursor.execute("SELECT * FROM active_trivias")
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

        await update.message.reply_text(
            f"🎬 TRIVIA CINEMATOGRÁFICA 🍿\n\n{pregunta}\n\nTienes 60 segundos para responder. ¡Buena suerte!"
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

    save_active_games_to_db()

    await update.message.reply_text(
        "🎬 ADIVINA LA PELÍCULA 🍿\n\nEstoy pensando en una película...\n"
        f"Pista: {pista}\n\nResponde con el título de la película. ¡Tienes 3 intentos!"
    )

async def cmd_emojipelicula(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id in active_games:
        await update.message.reply_text("¡Ya hay un juego activo en este chat!")
        return

    emoji_peliculas = {
        "🦁👑": "El Rey León", "👽📞": "E.T.", "👻🚫": "Cazafantasmas",
        "🦈🎶": "Tiburón", "🧙‍♂️⚡": "Harry Potter", "🧛‍♂️💍": "El Señor de los Anillos",
        "🚀👨‍🚀": "Apollo 13", "🦸‍♂️🦇": "Batman", "👩‍🚀🌌": "Interstellar"
    }

    emojis, respuesta = random.choice(list(emoji_peliculas.items()))
    active_games[chat_id] = {
        'juego': 'emojipelicula',
        'respuesta': respuesta,
        'pistas': [],
        'intentos': 0,
        'started_by': user.id,
        'last_activity': time.time()
    }

    save_active_games_to_db()

    await update.message.reply_text(
        "🎬 ADIVINA LA PELÍCULA POR EMOJIS 🍿\n\n"
        f"¿Qué película es esta? {emojis}\n\nResponde con el título exacto de la película. ¡Tienes 3 intentos!"
    )
__all__ = [
    "cmd_cinematrivia",
    "cmd_adivinapelicula",
    "cmd_emojipelicula",
    "initialize_games_system",
    "cleanup_games_periodically",
    "active_games",
    "active_trivias"
]
