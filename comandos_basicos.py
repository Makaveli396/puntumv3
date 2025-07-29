#!/usr/bin/env python3

from telegram import Update
from telegram.ext import ContextTypes
from db import get_user_stats, get_top10
import random
import datetime
import logging

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

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

def calculate_level(points: int) -> int:
    """Calcula el nivel de un usuario basado en sus puntos."""
    for level, (min_pts, max_pts, _, _) in LEVEL_THRESHOLDS.items():
        if min_pts <= points <= max_pts:
            return level
    return 1  # Nivel por defecto si no se encuentra

# --- DEFINICIONES DE COMANDOS BÁSICOS ---

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de inicio del bot"""
    user = update.effective_user
    welcome_message = f"""🎬 <b>¡Bienvenido al Bot Cinéfilo!</b> 🍿

¡Hola {user.mention_html()}! 👋

Gana puntos y compite usando hashtags como #critica, #reseña o #pelicula.

<b>📋 Comandos principales:</b>
• /help - Guía completa del bot
• /ranking - Ver el top 10 de usuarios
• /miperfil - Tus estadísticas personales
• /reto - Ver el reto cinéfilo del día

<b>🎮 Juegos disponibles:</b>
• /cinematrivia - Trivia de películas
• /adivinapelicula - Adivina por pistas
• /emojipelicula - Adivina por emojis

¡Empieza a compartir tu pasión por el cine y sube de nivel! 🏆"""
    await update.message.reply_text(welcome_message, parse_mode='HTML', disable_web_page_preview=True)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de ayuda del bot"""
    help_text = """🎬 <b>GUÍA COMPLETA DEL BOT CINÉFILO</b>

📊 <b>SISTEMA DE PUNTOS</b>
Gana puntos usando hashtags en tus mensajes. Los más valiosos son:
• <b>#critica</b>: 10 pts (requiere +25 palabras)
• <b>#reseña</b>: 7 pts (requiere +15 palabras)
• <b>#recomendacion</b>: 5 pts
• <b>#debate</b>: 4 pts
• Otros como #pelicula, #actor, #pregunta: 1-3 pts

🎮 <b>JUEGOS</b>
• /cinematrivia - Trivia de cine (15 puntos por victoria)
• /adivinapelicula - Adivina la película con pistas (15 puntos)
• /emojipelicula - Adivina la película con emojis (15 puntos)
• /pista - Pedir ayuda en juego activo
• /rendirse - Abandonar juego actual

📈 <b>COMANDOS</b>
• /start - Iniciar y conocer el bot
• /help - Esta guía
• /ranking - Top 10 usuarios
• /miperfil - Tus estadísticas y nivel
• /reto - Reto diario para ganar puntos extra

🏆 <b>NIVELES</b>
Asciende desde 🌱 Novato Cinéfilo hasta 👑 Maestro del Séptimo Arte acumulando puntos.

<b>🔐 AUTORIZACIÓN DE GRUPOS</b>
• /solicitar - Solicitar autorización para usar el bot en un grupo

¡Diviértete y comparte tu pasión por el cine! 🍿"""
    await update.message.reply_text(help_text, parse_mode='HTML')

async def cmd_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar el ranking de usuarios"""
    try:
        top_users = get_top10()
        if not top_users:
            await update.message.reply_text("📊 Aún no hay usuarios en el ranking. ¡Sé el primero en ganar puntos!")
            return
        
        ranking_text = "🏆 <b>TOP 10 CINÉFILOS</b> 🎬\n\n"
        icons = ["🥇", "🥈", "🥉"]
        
        for i, user_data in enumerate(top_users):
            username, points, level = user_data[0], user_data[1], user_data[2] if len(user_data) > 2 else calculate_level(user_data[1])
            level_emoji = LEVEL_THRESHOLDS.get(level, LEVEL_THRESHOLDS[1])[3]
            pos_icon = icons[i] if i < 3 else f"{i+1}."
            ranking_text += f"{pos_icon} {username} - <b>{points} pts</b> ({level_emoji} Nivel {level})\n"
        
        await update.message.reply_text(ranking_text, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error en cmd_ranking: {e}")
        await update.message.reply_text("❌ Error al obtener el ranking.")

async def cmd_miperfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar el perfil del usuario"""
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
        
        # Información sobre próximo nivel
        next_level_info = LEVEL_THRESHOLDS.get(level + 1)
        if next_level_info:
            points_needed = next_level_info[0] - points
            profile_text += f"\n\n📈 Faltan <b>{points_needed}</b> puntos para el siguiente nivel."
        else:
            profile_text += f"\n\n🏆 ¡Has alcanzado el nivel máximo!"

        # Mostrar hashtags más usados si están disponibles
        if hasattr(stats, 'hashtag_counts') and stats.hashtag_counts:
            top_hashtags = sorted(stats.hashtag_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            hashtag_text = ", ".join([f"{tag} ({count})" for tag, count in top_hashtags])
            profile_text += f"\n\n🏷️ Hashtags favoritos: {hashtag_text}"

        await update.message.reply_text(profile_text, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error en cmd_miperfil para {user.id}: {e}")
        await update.message.reply_text("❌ Error al obtener tu perfil.")

async def cmd_reto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar el reto diario"""
    today = datetime.date.today()
    random.seed(today.toordinal())  # Para que el reto sea el mismo durante todo el día
    daily_challenge = random.choice(DAILY_CHALLENGES)
    
    reto_text = f"""🎯 <b>RETO DIARIO</b> ({today.strftime('%d/%m/%Y')})

"{daily_challenge}"

💡 Responde al reto en un mensaje usando hashtags como #debate o #recomendacion para ganar puntos extra. ¡Sé creativo!

🎬 Los mejores aportes pueden ganar hasta 10 puntos adicionales."""
    
    await update.message.reply_text(reto_text, parse_mode='HTML')