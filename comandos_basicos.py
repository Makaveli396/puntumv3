#!/usr/bin/env python3

from telegram import Update
from telegram.ext import ContextTypes
# Asumimos que tienes un archivo db.py con estas funciones
from db import get_user_stats, get_top10, add_points
import random
import datetime
import logging
import re
import time
import unicodedata

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- LISTA ÚNICA Y MEJORADA DE HASHTAGS ---
VALID_HASHTAGS = {
    # Alto valor
    'critica': 10,         # Análisis profundo, mínimo 100 palabras
    'reseña': 7,           # Reseña detallada, mínimo 50 palabras
    'resena': 7,           # Alias sin tilde
    'recomendacion': 5,
    
    # Participación media
    'debate': 4, 'aporte': 3, 'cinefilo': 3, 'pelicula': 3, 'cine': 3,
    'serie': 3, 'director': 3, 'oscar': 3, 'festival': 3, 'documental': 3,
    'animacion': 3, 'clasico': 3, 'independiente': 3,
    
    # Participación baja
    'actor': 2, 'genero': 2, 'pregunta': 2, 'ranking': 2, 'rankin': 2,
    
    # Mínimo
    'spoiler': 1
}

# Cache para control de spam (por usuario)
user_hashtag_cache = {}

# Niveles del sistema
LEVEL_THRESHOLDS = {
    1: (0, 99, "Novato Cinéfilo", "🌱"),
    2: (100, 249, "Aficionado", "🎭"),
    3: (250, 499, "Crítico Amateur", "🎬"),
    4: (500, 999, "Experto Cinematográfico", "🏆"),
    5: (1000, float('inf'), "Maestro del Séptimo Arte", "👑")
}

# Retos diarios
DAILY_CHALLENGES = [
    "🎬 Comparte tu película favorita de ciencia ficción y explica por qué.",
    "🎭 Menciona un actor que te haya sorprendido en su último papel.",
    "📽️ ¿Cuál fue la última película que viste en el cine? ¿La recomendarías?",
    "🏆 Nombra una película que mereció más reconocimiento en los premios.",
    "📚 Comparte una adaptación cinematográfica que superó al libro original.",
    "🎨 Menciona un director con un estilo visual único y describe su técnica.",
    "🎵 ¿Qué película tiene tu banda sonora favorita? Comparte una canción.",
    "💔 Comparte una película que te hizo llorar y explica la escena.",
    "😱 Menciona el mejor thriller que hayas visto este año.",
    "🤣 ¿Cuál es tu comedia favorita y tu escena más divertida?",
    "🌍 Recomienda una película internacional que pocos conozcan."
]

# --- FUNCIONES AUXILIARES (Hashtags, Palabras, Niveles) ---

def normalize_text(text: str) -> str:
    """Normaliza texto removiendo tildes y lo convierte a minúsculas."""
    if not text: return ""
    normalized = unicodedata.normalize('NFD', text)
    normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return normalized.lower()

def find_hashtags_in_message(text: str) -> list:
    """Encuentra TODOS los hashtags válidos en un mensaje con detección flexible."""
    if not text: return []
    found_hashtags = set()
    hashtag_pattern = r'#(\w+)'
    potential_hashtags = re.findall(hashtag_pattern, text)
    
    for hashtag_word in potential_hashtags:
        normalized_hashtag = normalize_text(hashtag_word)
        if normalized_hashtag in VALID_HASHTAGS:
            points = VALID_HASHTAGS[normalized_hashtag]
            found_hashtags.add((f"#{hashtag_word}", points))
            
    return list(found_hashtags)

def is_spam(user_id: int, hashtag: str) -> bool:
    """Detecta si un usuario está usando el mismo hashtag repetidamente."""
    current_time = time.time()
    if user_id not in user_hashtag_cache:
        user_hashtag_cache[user_id] = {}
    
    user_data = user_hashtag_cache[user_id]
    if user_data.get("last_time") and current_time - user_data["last_time"] > 300:
        user_data.clear()
    
    count = user_data.get(hashtag, 0) + 1
    user_data[hashtag] = count
    user_data["last_time"] = current_time
    return count > 3

def count_words(text: str) -> int:
    """Cuenta las palabras en un texto, excluyendo los propios hashtags."""
    if not text: return 0
    text_without_hashtags = re.sub(r'#\w+', '', text)
    return len(text_without_hashtags.split())

def calculate_level(points: int) -> int:
    """Calcula el nivel de un usuario basado en sus puntos."""
    for level, (min_pts, max_pts, _, _) in LEVEL_THRESHOLDS.items():
        if min_pts <= points <= max_pts:
            return level
    return 1 # Nivel por defecto si no se encuentra

# --- MANEJADOR DE MENSAJES CON HASHTAGS ---

async def handle_hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return

    message_text = update.message.text
    user = update.effective_user
    chat = update.effective_chat
    
    found_hashtags = find_hashtags_in_message(message_text)
    if not found_hashtags: return

    valid_hashtags_for_points, total_points, warnings = [], 0, []
    word_count = count_words(message_text)
    
    for hashtag, points in found_hashtags:
        normalized_hashtag = normalize_text(hashtag[1:])
        if is_spam(user.id, hashtag):
            warnings.append(f"⚠️ {hashtag}: Has usado este hashtag muy seguido.")
            continue
        
        if normalized_hashtag == "critica" and word_count < 100:
            warnings.append(f"❌ Para #critica se requiere un análisis de mín. 100 palabras (tienes {word_count}).")
            points = max(1, points // 2)
        elif normalized_hashtag in ["reseña", "resena"] and word_count < 50:
            warnings.append(f"❌ Para #reseña se requiere un texto de mín. 50 palabras (tienes {word_count}).")
            points = max(1, points // 2)
        
        valid_hashtags_for_points.append((hashtag, points))
        total_points += points
    
    if total_points <= 0: return
        
    bonus_text = ""
    if len(message_text) > 280:
        total_points += 2
        bonus_text = " (+2 bonus por detalle)"

    try:
        primary_hashtag = valid_hashtags_for_points[0][0] if valid_hashtags_for_points else "#aporte"
        add_points(
            user_id=user.id,
            username=user.username or user.first_name,
            points=total_points,
            hashtag=primary_hashtag,
            message_text=message_text[:250],
            chat_id=chat.id,
            message_id=update.message.message_id
        )
    except Exception as e:
        logger.error(f"Error al guardar puntos en la BD para el usuario {user.id}: {e}")
        await update.message.reply_text("🚨 Hubo un error al guardar tus puntos.")
        return

    hashtags_list_str = ", ".join([h for h, p in valid_hashtags_for_points])
    response_header = random.choice(["¡Excelente aporte!", "¡Puntos ganados!", "¡Gran contribución!"])
    
    response_text = (
        f"✅ <b>{response_header}</b> 🎬\n\n"
        f"👤 {user.mention_html()}\n"
        f"🏷️ Hashtags: {hashtags_list_str}\n"
        f"💎 Puntos: <b>+{total_points}</b>{bonus_text}\n\n"
        "🎭 ¡Sigue compartiendo tu pasión por el cine! 🍿"
    )
    if warnings:
        response_text += "\n\n⚠️ <b>Notas:</b>\n" + "\n".join(warnings)
        
    try:
        await update.message.reply_text(response_text, parse_mode='HTML', reply_to_message_id=update.message.message_id)
        logger.info(f"Usuario {user.id} ganó {total_points} puntos con: {hashtags_list_str}")
    except Exception as e:
        logger.error(f"Error al enviar respuesta de puntos a {user.id}: {e}")

# --- DEFINICIONES DE COMANDOS BÁSICOS ---

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_message = f"""🎬 <b>¡Bienvenido al Bot Cinéfilo!</b> 🍿

¡Hola {user.mention_html()}! 👋

Gana puntos y compite usando hashtags como #critica, #reseña o #pelicula.

<b>📋 Comandos principales:</b>
• /help - Guía completa del bot
• /ranking - Ver el top 10 de usuarios
• /miperfil - Tus estadísticas personales
• /reto - Ver el reto cinéfilo del día

¡Empieza a compartir tu pasión por el cine y sube de nivel! 🏆"""
    await update.message.reply_text(welcome_message, parse_mode='HTML', disable_web_page_preview=True)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """🎬 <b>GUÍA COMPLETA DEL BOT CINÉFILO</b>

📊 <b>SISTEMA DE PUNTOS</b>
Gana puntos usando hashtags en tus mensajes. Los más valiosos son:
• <b>#critica</b>: 10 pts (requiere +100 palabras)
• <b>#reseña</b>: 7 pts (requiere +50 palabras)
• <b>#recomendacion</b>: 5 pts
• <b>#debate</b>: 4 pts
• Otros como #pelicula, #actor, #pregunta: 1-3 pts

🎮 <b>JUEGOS</b>
• /cinematrivia - Trivia de cine (¡Próximamente con más preguntas!)
• /adivinapelicula - Adivina la película con una pista
• /emojipelicula - Adivina la película con emojis

📈 <b>COMANDOS</b>
• /start - Iniciar y conocer el bot
• /help - Esta guía
• /ranking - Top 10 usuarios
• /miperfil - Tus estadísticas y nivel
• /reto - Reto diario para ganar puntos extra

🏆 <b>NIVELES</b>
Asciende desde 🌱 Novato Cinéfilo hasta 👑 Maestro del Séptimo Arte acumulando puntos.

¡Diviértete y comparte tu pasión por el cine! 🍿"""
    await update.message.reply_text(help_text, parse_mode='HTML')

async def cmd_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        top_users = get_top10()
        if not top_users:
            await update.message.reply_text("📊 Aún no hay usuarios en el ranking. ¡Sé el primero en ganar puntos!")
            return
        
        ranking_text = "🏆 <b>TOP 10 CINÉFILOS</b> 🎬\n\n"
        icons = ["🥇", "🥈", "🥉"]
        for i, user_data in enumerate(top_users):
            username, points = user_data[0], user_data[1]
            level = calculate_level(points)
            level_emoji = LEVEL_THRESHOLDS[level][3]
            pos_icon = icons[i] if i < 3 else f"{i+1}."
            ranking_text += f"{pos_icon} {username} - <b>{points} pts</b> ({level_emoji} Nivel {level})\n"
        
        await update.message.reply_text(ranking_text, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error en cmd_ranking: {e}")
        await update.message.reply_text("❌ Error al obtener el ranking.")

async def cmd_miperfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        stats = get_user_stats(user.id)
        if not stats:
            await update.message.reply_text("📊 Aún no tienes estadísticas. ¡Usa hashtags como #pelicula para empezar a ganar puntos!")
            return

        points = stats.get('points', 0)
        level = calculate_level(points)
        level_name, level_emoji = LEVEL_THRESHOLDS[level][2], LEVEL_THRESHOLDS[level][3]
        
        profile_text = (
            f"{level_emoji} <b>PERFIL DE {user.first_name.upper()}</b>\n\n"
            f"💎 Puntos totales: <b>{points}</b>\n"
            f"📝 Contribuciones: <b>{stats.get('count', 0)}</b>\n"
            f"🎯 Nivel: <b>{level} - {level_name}</b>"
        )
        
        next_level_info = LEVEL_THRESHOLDS.get(level + 1)
        if next_level_info:
            points_needed = next_level_info[0] - points
            profile_text += f"\n\n📈 Faltan <b>{points_needed}</b> puntos para el siguiente nivel."
        else:
            profile_text += f"\n\n🏆 ¡Has alcanzado el nivel máximo!"

        await update.message.reply_text(profile_text, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error en cmd_miperfil para {user.id}: {e}")
        await update.message.reply_text("❌ Error al obtener tu perfil.")

async def cmd_reto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.date.today()
    random.seed(today.toordinal()) # Para que el reto sea el mismo durante todo el día
    daily_challenge = random.choice(DAILY_CHALLENGES)
    
    reto_text = f"""🎯 <b>RETO DIARIO</b> ({today.strftime('%d/%m/%Y')})

"{daily_challenge}"

💡 Responde al reto en un mensaje usando hashtags como #debate o #recomendacion para ganar puntos extra. ¡Sé creativo!"""
    await update.message.reply_text(reto_text, parse_mode='HTML')
