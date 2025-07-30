# juegos.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, Application
import logging
from typing import Dict, Any
import random
import time
import asyncio
import json
from datetime import datetime
import telegram # Asegúrate de importar telegram para usar telegram.error.BadRequest

# Importar funciones corregidas de db.py
from db import (
    add_points, 
    get_connection, 
    is_postgresql,
    save_active_game,
    get_active_game,
    delete_active_game,
    save_active_trivia,
    get_active_trivia,
    delete_active_trivia,
    get_all_active_games,
    get_all_active_trivias,
    cleanup_expired_games
)
from generador_trivia import generar_pregunta

# Importar handle_hashtags correctamente
try:
    from hashtags import handle_hashtags
except ImportError:
    logger.warning("No se pudo importar handle_hashtags desde hashtags.py")
    async def handle_hashtags(update, context):
        # Función placeholder si no existe hashtags.py
        pass

logger = logging.getLogger(__name__)

# Diccionarios en memoria para acceso rápido (se sincronizan con DB)
active_games: Dict[int, Dict[str, Any]] = {}
active_trivias: Dict[int, Dict[str, Any]] = {}

def initialize_games_system():
    """Inicializar el sistema de juegos cargando datos de la base de datos"""
    logger.info("🎮 Inicializando sistema de juegos...")
    try:
        load_active_games_from_db()
        logger.info("✅ Sistema de juegos inicializado correctamente")
    except Exception as e:
        logger.error(f"❌ Error inicializando sistema de juegos: {e}")

def load_active_games_from_db():
    """Cargar juegos activos desde la base de datos"""
    global active_games, active_trivias
    
    try:
        # Limpiar primero los diccionarios en memoria
        active_games.clear()
        active_trivias.clear()
        
        # Cargar juegos activos usando las funciones de db.py
        games_from_db = get_all_active_games()
        for game in games_from_db:
            chat_id = game['chat_id']
            active_games[chat_id] = {
                'juego': game['juego'],
                'respuesta': game['respuesta'],
                'pistas': json.loads(game['pistas']) if game['pistas'] else [],
                'intentos': game['intentos'],
                'started_by': game['started_by'],
                'last_activity': game['last_activity']
            }
        
        # Cargar trivias activas usando las funciones de db.py
        trivias_from_db = get_all_active_trivias()
        for trivia in trivias_from_db:
            chat_id = trivia['chat_id']
            active_trivias[chat_id] = {
                'pregunta': trivia['pregunta'],
                'respuesta': trivia['respuesta'],
                'start_time': trivia['start_time'],
                'opciones': json.loads(trivia['opciones']) if trivia['opciones'] else [],
                'message_id': trivia['message_id'],
                'inline_keyboard_message_id': trivia['inline_keyboard_message_id']
            }
        
        logger.info(f"✅ Cargados {len(active_games)} juegos y {len(active_trivias)} trivias activas")
        
    except Exception as e:
        logger.error(f"❌ Error cargando juegos activos desde DB: {e}")

def sync_game_to_db(chat_id: int):
    """Sincronizar un juego específico con la base de datos"""
    try:
        if chat_id in active_games:
            game_data = active_games[chat_id]
            save_active_game(
                chat_id=chat_id,
                juego=game_data['juego'],
                respuesta=game_data['respuesta'],
                pistas=json.dumps(game_data['pistas']),
                intentos=game_data['intentos'],
                started_by=game_data['started_by']
            )
    except Exception as e:
        logger.error(f"❌ Error sincronizando juego {chat_id} con DB: {e}")

def sync_trivia_to_db(chat_id: int):
    """Sincronizar una trivia específica con la base de datos"""
    try:
        if chat_id in active_trivias:
            trivia_data = active_trivias[chat_id]
            save_active_trivia(
                chat_id=chat_id,
                pregunta=trivia_data['pregunta'],
                respuesta=trivia_data['respuesta'],
                start_time=trivia_data['start_time'],
                opciones=json.dumps(trivia_data['opciones']),
                message_id=trivia_data['message_id'],
                inline_keyboard_message_id=trivia_data['inline_keyboard_message_id']
            )
    except Exception as e:
        logger.error(f"❌ Error sincronizando trivia {chat_id} con DB: {e}")

async def check_active_games():
    """Función para revisar juegos activos y limpiar los inactivos."""
    while True:
        try:
            current_time = time.time()
            games_to_remove = []
            
            # Revisar juegos activos
            for chat_id, game_data in active_games.items():
                try:
                    # Convertir last_activity a timestamp si es necesario
                    if isinstance(game_data['last_activity'], datetime):
                        last_activity_timestamp = game_data['last_activity'].timestamp()
                    elif isinstance(game_data['last_activity'], str):
                        # Para SQLite que puede devolver strings
                        dt = datetime.fromisoformat(game_data['last_activity'])
                        last_activity_timestamp = dt.timestamp()
                    else:
                        last_activity_timestamp = game_data['last_activity']
                    
                    if current_time - last_activity_timestamp > 3600:  # 1 hora de inactividad
                        games_to_remove.append(chat_id)
                        
                except Exception as e:
                    logger.error(f"❌ Error procesando juego {chat_id}: {e}")
                    games_to_remove.append(chat_id)  # Remover juegos problemáticos

            # Remover juegos inactivos
            for chat_id in games_to_remove:
                logger.info(f"🧹 Juego en chat {chat_id} removido por inactividad")
                if chat_id in active_games:
                    del active_games[chat_id]
                try:
                    delete_active_game(chat_id)
                except Exception as e:
                    logger.error(f"❌ Error eliminando juego {chat_id} de DB: {e}")
            
            # Revisar trivias activas
            trivias_to_remove = []
            for chat_id, trivia_data in active_trivias.items():
                try:
                    if current_time - trivia_data['start_time'] > 600:  # 10 minutos para trivias
                        trivias_to_remove.append(chat_id)
                except Exception as e:
                    logger.error(f"❌ Error procesando trivia {chat_id}: {e}")
                    trivias_to_remove.append(chat_id)
            
            # Remover trivias inactivas
            for chat_id in trivias_to_remove:
                logger.info(f"🧹 Trivia en chat {chat_id} removida por inactividad")
                if chat_id in active_trivias:
                    del active_trivias[chat_id]
                try:
                    delete_active_trivia(chat_id)
                except Exception as e:
                    logger.error(f"❌ Error eliminando trivia {chat_id} de DB: {e}")

            # Usar la función de limpieza de db.py también
            try:
                cleanup_expired_games(timeout_minutes=60)  # 1 hora
            except Exception as e:
                logger.error(f"❌ Error en cleanup_expired_games: {e}")

            if games_to_remove or trivias_to_remove:
                logger.info(f"🧹 Limpieza completada: {len(games_to_remove)} juegos, {len(trivias_to_remove)} trivias")
            
        except Exception as e:
            logger.error(f"❌ Error en check_active_games: {e}")
        
        # Esperar 10 minutos antes de la próxima revisión
        await asyncio.sleep(600)

async def cmd_cinematrivia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando para iniciar una cinematrivia"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id in active_games:
        await update.message.reply_text(
            "🎮 Ya hay un juego activo en este chat. Usa /rendirse para terminarlo.",
            reply_to_message_id=update.message.message_id
        )
        return

    logger.info(f"🎬 Generando pregunta de cinematrivia para chat {chat_id}")
    
    try:
        pregunta, respuesta = generar_pregunta()
    except Exception as e:
        logger.error(f"❌ Error generando pregunta: {e}")
        await update.message.reply_text(
            "❌ Error generando la pregunta. Intenta más tarde.",
            reply_to_message_id=update.message.message_id
        )
        return

    if not pregunta or not respuesta or respuesta == "Error":
        await update.message.reply_text(
            "❌ No se pudo generar la pregunta. Intenta más tarde.",
            reply_to_message_id=update.message.message_id
        )
        logger.error(f"❌ Fallo al generar pregunta de trivia para chat {chat_id}: Pregunta='{pregunta}', Respuesta='{respuesta}'")
        return

    # Crear juego en memoria
    active_games[chat_id] = {
        'juego': 'cinematrivia',
        'respuesta': respuesta.lower().strip(),
        'pistas': [],
        'intentos': 0,
        'started_by': user_id,
        'last_activity': datetime.now()
    }
    
    # Sincronizar con base de datos
    sync_game_to_db(chat_id)

    keyboard = [[InlineKeyboardButton("Responder por texto", callback_data="text_answer")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🎬 **¡Nueva Cinematrivia!** 🍿\n\n{pregunta}\n\n"
        "🤔 ¡Adivina la respuesta! Tienes 5 intentos.",
        reply_markup=reply_markup,
        parse_mode='Markdown',
        reply_to_message_id=update.message.message_id
    )

async def cmd_adivinapelicula(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando para adivinar película (pendiente de implementar)"""
    await update.message.reply_text(
        "🎭 Comando /adivinapelicula aún no implementado.\n"
        "¡Próximamente tendremos este juego disponible!",
        reply_to_message_id=update.message.message_id
    )

async def cmd_emojipelicula(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando para adivinar película por emojis (pendiente de implementar)"""
    await update.message.reply_text(
        "😃 Comando /emojipelicula aún no implementado.\n"
        "¡Próximamente tendremos este juego disponible!",
        reply_to_message_id=update.message.message_id
    )

async def cmd_pista(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando para pedir una pista en el juego activo"""
    chat_id = update.effective_chat.id
    
    if chat_id not in active_games:
        await update.message.reply_text(
            "🤷‍♂️ No hay ningún juego activo en este chat para dar una pista.",
            reply_to_message_id=update.message.message_id
        )
        return

    game_data = active_games[chat_id]
    if game_data['juego'] != 'cinematrivia':
        await update.message.reply_text(
            "💡 Las pistas solo están disponibles para Cinematrivia en este momento.",
            reply_to_message_id=update.message.message_id
        )
        return
    
    # Lógica para dar una pista
    respuesta = game_data['respuesta']
    pistas = game_data.get('pistas', [])
    
    # Límite de pistas (máximo la mitad de los caracteres únicos)
    max_pistas = max(1, len(set(respuesta.replace(' ', ''))) // 2)
    
    if len(pistas) >= max_pistas:
        await update.message.reply_text(
            "🚫 Ya he dado suficientes pistas. ¡Esfuérzate un poco más!",
            reply_to_message_id=update.message.message_id
        )
        return

    # Encontrar una letra no revelada para dar una pista
    caracteres_no_revelados = [c for c in respuesta if c not in pistas and c.isalpha()]

    if not caracteres_no_revelados:
        await update.message.reply_text(
            "🔍 No hay más letras para revelar como pista.",
            reply_to_message_id=update.message.message_id
        )
        return
    
    # Seleccionar un carácter aleatorio para revelar
    nuevo_caracter = random.choice(caracteres_no_revelados)
    pistas.append(nuevo_caracter)
    active_games[chat_id]['pistas'] = pistas
    active_games[chat_id]['last_activity'] = datetime.now()
    
    # Sincronizar con base de datos
    sync_game_to_db(chat_id)
    
    # Mostrar la pista
    letras_reveladas = [c if c in pistas or not c.isalpha() else '_' for c in respuesta]
    pista_actual = " ".join(letras_reveladas)

    await update.message.reply_text(
        f"💡 **Pista revelada:**\n`{pista_actual}`\n\n"
        f"🔢 Pistas usadas: {len(pistas)}/{max_pistas}",
        parse_mode='Markdown',
        reply_to_message_id=update.message.message_id
    )

async def cmd_rendirse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando para rendirse en el juego activo"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id in active_games:
        game_data = active_games.pop(chat_id)
        try:
            delete_active_game(chat_id)
        except Exception as e:
            logger.error(f"❌ Error eliminando juego de DB: {e}")
            
        respuesta_correcta = game_data.get('respuesta', 'N/A')
        await update.message.reply_text(
            f"🏳️ Has abandonado el juego actual.\n"
            f"🎯 La respuesta era: **{respuesta_correcta.title()}**",
            parse_mode='Markdown',
            reply_to_message_id=update.message.message_id
        )
        
    elif chat_id in active_trivias:
        trivia_data = active_trivias.pop(chat_id)
        try:
            delete_active_trivia(chat_id)
        except Exception as e:
            logger.error(f"❌ Error eliminando trivia de DB: {e}")
            
        respuesta_correcta = trivia_data.get('respuesta', 'N/A')
        await update.message.reply_text(
            f"🏳️ Has abandonado la trivia actual.\n"
            f"🎯 La respuesta era: **{respuesta_correcta.title()}**",
            parse_mode='Markdown',
            reply_to_message_id=update.message.message_id
        )
    else:
        await update.message.reply_text(
            "🤷‍♂️ No hay ningún juego o trivia activa en este chat.",
            reply_to_message_id=update.message.message_id
        )

async def route_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ruta los mensajes de texto a los manejadores de juego o hashtags."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text

    # Verificar si hay un juego activo y si es una respuesta
    if chat_id in active_games and user_id != context.bot.id:
        game_data = active_games[chat_id]
        if game_data['juego'] == 'cinematrivia':
            await handle_game_message(update, context)
            return
    
    # Si no es una respuesta de juego, procesar hashtags
    try:
        await handle_hashtags(update, context)
    except Exception as e:
        logger.error(f"❌ Error procesando hashtags: {e}")

async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejar respuestas de juegos activos"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_answer = update.message.text.lower().strip()
    
    if chat_id not in active_games:
        return  # No hay juego activo para este chat

    game_data = active_games[chat_id]
    game_data['last_activity'] = datetime.now()
    
    if game_data['juego'] == 'cinematrivia':
        correct_answer = game_data['respuesta'].lower().strip()

        # Verificar si la respuesta es correcta
        if user_answer == correct_answer:
            # Respuesta correcta
            try:
                add_points(
                    user_id=user_id,
                    chat_id=chat_id,
                    points=15,  # Puntos por ganar cinematrivia
                    username=update.effective_user.username or update.effective_user.first_name,
                    chat_name=update.effective_chat.title or "Chat Privado",
                    reason="Cinematrivia ganada",
                    message_id=update.message.message_id
                )
            except Exception as e:
                logger.error(f"❌ Error agregando puntos: {e}")
            
            # Eliminar juego activo
            del active_games[chat_id]
            try:
                delete_active_game(chat_id)
            except Exception as e:
                logger.error(f"❌ Error eliminando juego de DB: {e}")
            
            await update.message.reply_text(
                f"🎉 **¡CORRECTO!** 🎉\n\n"
                f"¡Felicidades, {update.effective_user.mention_html()}!\n"
                f"🎯 La respuesta era: **{correct_answer.title()}**\n"
                f"⭐ Has ganado **15 puntos**",
                parse_mode='HTML',
                reply_to_message_id=update.message.message_id
            )
        else:
            # Respuesta incorrecta
            game_data['intentos'] += 1
            intentos_restantes = 5 - game_data['intentos']
            
            if intentos_restantes <= 0:
                # Se acabaron los intentos
                respuesta_real = game_data['respuesta']
                del active_games[chat_id]
                try:
                    delete_active_game(chat_id)
                except Exception as e:
                    logger.error(f"❌ Error eliminando juego de DB: {e}")
                
                await update.message.reply_text(
                    f"❌ **¡Se acabaron los intentos!**\n\n"
                    f"🎯 La respuesta correcta era: **{respuesta_real.title()}**\n"
                    f"🍀 ¡Mejor suerte la próxima vez!",
                    parse_mode='Markdown',
                    reply_to_message_id=update.message.message_id
                )
            else:
                # Sincronizar con base de datos
                sync_game_to_db(chat_id)
                
                await update.message.reply_text(
                    f"❌ **Respuesta incorrecta**\n"
                    f"🔢 Te quedan **{intentos_restantes}** intentos\n"
                    f"💡 Usa /pista si necesitas ayuda",
                    parse_mode='Markdown',
                    reply_to_message_id=update.message.message_id
                )

async def handle_trivia_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejar callbacks de botones en trivias"""
    query = update.callback_query
    
    try:
        await query.answer()
    except telegram.error.BadRequest as e:
        logger.warning(f"⚠️ Error al responder al callback query (quizás ya caducó): {e}")
        return
    except Exception as e:
        logger.error(f"❌ Error inesperado en callback: {e}")
        return
    
    if query.data == "text_answer":
        try:
            await query.edit_message_text(
                text=query.message.text + "\n\n✏️ **Responde escribiendo tu respuesta como mensaje de texto.**",
                parse_mode='Markdown'
            )
        except telegram.error.BadRequest as e:
            logger.warning(f"⚠️ No se pudo editar el mensaje del callback: {e}")
        except Exception as e:
            logger.error(f"❌ Error editando mensaje de trivia: {e}")

# Exportar todas las funciones necesarias
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
    "route_text_message",
    "check_active_games"
]