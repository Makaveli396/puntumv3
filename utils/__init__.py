
from telegram import Update
from telegram.ext import ContextTypes
from db import get_user_stats

def get_user_level(points):
    if points < 50:
        return "🎞️ Novato"
    elif points < 150:
        return "🍿 Cinéfilo"
    elif points < 300:
        return "🎬 Crítico"
    else:
        return "🏆 Leyenda del Cine"

async def cmd_mipuntaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    stats = get_user_stats(user_id)

    if not stats:
        await update.message.reply_text("❌ Aún no tienes puntos.")
        return

    points = stats.get("points", 0)
    level = get_user_level(points)

    await update.message.reply_text(
        f"🎟️ {username}, tienes {points} puntos.\n"
        f"🌟 Nivel actual: {level}"
    )

async def cmd_miperfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = get_user_stats(user_id)

    if not stats:
        await update.message.reply_text("❌ No tienes actividad registrada.")
        return

    await update.message.reply_text(
        f"🎭 Perfil de {update.effective_user.first_name}:\n"
        f"- Puntos: {stats['points']}\n"
        f"- Nivel: {get_user_level(stats['points'])}\n"
        f"- Hashtags usados: {stats['hashtags']}\n"
        f"- Días activo: {stats['active_days']}"
    )

async def cmd_mirank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    rank = get_user_stats(user_id).get("rank", "No disponible")

    await update.message.reply_text(
        f"📈 Estás en la posición #{rank} del ranking."
    )
