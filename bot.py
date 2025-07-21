#!/usr/bin/env python3
import os
import logging
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

# Módulos personalizados
from db import initialize_db, add_points, get_user_stats, get_top10
from hashtags import handle_hashtags, VALID_HASHTAGS
from weekly_challenges import generate_new_challenge, get_current_challenge, check_challenge_completion
from generador_trivia import generar_pregunta
from comandos_basicos import (
    cmd_start, cmd_help, cmd_hashtags, cmd_reto, cmd_generarreto,
    cmd_puntos, cmd_top10, cmd_trivia, cmd_adivina, cmd_logros,
    cmd_id, cmd_saludar, cmd_rules, cmd_about
)

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONSTANTES ---
ACHIEVEMENTS = {
    "critico_experto": {
        "name": "Crítico Experto",
        "condition": lambda stats: stats.get("hashtag_counts", {}).get("critica", 0) >= 10,
        "reward": 100
    },
    "maratonista": {
        "name": "Maratonista",
        "condition": lambda stats: len(stats.get("active_days", [])) >= 30,
        "reward": 50
    }
}

# --- COMANDOS PRINCIPALES ---
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 ¡Bienvenido al Bot de Cine y Series!\n\n"
        "Usa /help para ver todos los comandos.\n"
        "Gana puntos con hashtags como #critica o #recomendacion"
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🍿 <b>Comandos Disponibles:</b>

🎥 <b>Interacción:</b>
/hashtags - Lista de hashtags válidos
/reto - Reto semanal actual
/puntos - Tus puntos y nivel
/top10 - Ranking de usuarios

🎮 <b>Juegos:</b>
/trivia - Trivia de cine
/adivina - Adivina la película

🏆 <b>Logros:</b>
/logros - Tus logros desbloqueados
"""
    await update.message.reply_text(help_text, parse_mode="HTML")

async def cmd_hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hashtags_text = "🏷️ <b>Hashtags Válidos:</b>\n\n"
    for tag, points in sorted(VALID_HASHTAGS.items(), key=lambda x: -x[1]):
        hashtags_text += f"#{tag}: {points} pts\n"
    await update.message.reply_text(hashtags_text, parse_mode="HTML")

async def cmd_reto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    challenge = get_current_challenge()
    if not challenge:
        await update.message.reply_text("⚠️ No hay retos activos ahora.")
        return
    
    challenge_info = {
        "genre": "🎭 Género",
        "director": "🎬 Director",
        "decade": "📅 Década"
    }[challenge["challenge_type"]]
    
    response = (
        f"🎬 <b>Reto Semanal</b> (válido hasta {challenge['end_date']})\n\n"
        f"{challenge_info}: <b>{challenge['challenge_value']}</b>\n\n"
        f"Para completarlo:\n"
        f"1. Usa #RetoSemanal + #pelicula o #serie\n"
        f"2. Gana <b>50 puntos extra</b>!"
    )
    await update.message.reply_text(response, parse_mode="HTML")

async def cmd_puntos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    stats = get_user_stats(user.id)
    
    if not stats:
        await update.message.reply_text("ℹ️ Aún no tienes puntos. ¡Participa usando hashtags!")
        return
    
    level_info = {
        1: "🌱 Novato",
        2: "🎭 Aficionado",
        3: "🎬 Crítico",
        4: "🏆 Experto",
        5: "👑 Maestro"
    }
    
    response = (
        f"📊 <b>Estadísticas de {user.first_name}</b>\n\n"
        f"⭐ Nivel: {level_info.get(stats['level'], 'N/A')}\n"
        f"💎 Puntos: {stats['points']}\n"
        f"🎯 Para siguiente nivel: {stats['points_to_next']} pts\n"
        f"📅 Miembro desde: {stats['member_since'][:10]}"
    )
    await update.message.reply_text(response, parse_mode="HTML")

async def cmd_top10(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = get_top10()
    if not top_users:
        await update.message.reply_text("ℹ️ Aún no hay suficientes participantes.")
        return
    
    response = "🏆 <b>Top 10 Cinéfilos</b>\n\n"
    for i, (username, points, level) in enumerate(top_users, 1):
        response += f"{i}. {username}: {points} pts (Nvl {level})\n"
    
    await update.message.reply_text(response, parse_mode="HTML")

# --- JUEGOS ---
async def cmd_trivia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pregunta, respuesta = generar_pregunta()
    if respuesta == "Error":
        await update.message.reply_text(pregunta)
        return
    
    context.chat_data['trivia_answer'] = respuesta.lower()
    await update.message.reply_text(
        f"🎬 <b>Trivia Cinéfila</b>\n\n{pregunta}\n\n"
        "Responde directamente a este mensaje.",
        parse_mode="HTML"
    )

async def cmd_adivina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Implementación simplificada (puedes expandirla)
    await update.message.reply_text(
        "🎥 <b>Adivina la Película</b>\n\n"
        "Próximamente: ¡Fotogramas y pistas!",
        parse_mode="HTML"
    )

# --- SISTEMA DE LOGROS ---
async def cmd_logros(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    stats = get_user_stats(user.id)
    
    if not stats or not stats.get("achievements"):
        await update.message.reply_text("ℹ️ Aún no has desbloqueado logros.")
        return
    
    response = "🏅 <b>Tus Logros</b>\n\n"
    for ach_id in stats["achievements"]:
        ach = ACHIEVEMENTS.get(ach_id, {})
        response += f"• {ach.get('name', 'Desconocido')}\n"
    
    await update.message.reply_text(response, parse_mode="HTML")

def check_achievements(user_id: int):
    stats = get_user_stats(user_id)
    if not stats:
        return []
    
    new_achievements = []
    for ach_id, ach in ACHIEVEMENTS.items():
        if ach_id not in stats.get("achievements", []) and ach["condition"](stats):
            add_achievement(user_id, ach_id)
            new_achievements.append(ach["name"])
    
    return new_achievements

# --- TAREAS PROGRAMADAS ---
async def weekly_challenge_task(context: ContextTypes.DEFAULT_TYPE):
    new_challenge = generate_new_challenge()
    if not new_challenge:
        return
    
    for chat in get_configured_chats():
        try:
            await context.bot.send_message(
                chat_id=chat["chat_id"],
                text=f"🎬 <b>Nuevo Reto Semanal!</b>\n\n"
                     f"🏆 {new_challenge['value']}\n\n"
                     f"Usa #RetoSemanal para participar!",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error enviando reto a chat {chat['id']}: {e}")

# --- CONFIGURACIÓN DEL BOT ---
async def post_init(application):
    # Configurar comandos del menú
    commands = [
        BotCommand("start", "Inicia el bot"),
        BotCommand("help", "Ayuda y comandos"),
        BotCommand("hashtags", "Hashtags válidos"),
        BotCommand("reto", "Reto semanal"),
        BotCommand("puntos", "Tus puntos"),
        BotCommand("top10", "Mejores usuarios"),
        BotCommand("trivia", "Trivia de cine"),
        BotCommand("adivina", "Adivina la película"),
        BotCommand("logros", "Tus logros")
    ]
    await application.bot.set_my_commands(commands)
    
    # Inicializar base de datos
    await initialize_db()
    
    # Programar tarea semanal
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        weekly_challenge_task,
        'cron',
        day_of_week='mon',
        hour=9,
        args=[application]
    )
    scheduler.start()

async def main():
    application = ApplicationBuilder() \
        .token(os.getenv('TELEGRAM_TOKEN')) \
        .post_init(post_init) \
        .build()

    # Manejadores de comandos
    command_handlers = {
        "start": cmd_start,
        "help": cmd_help,
        "hashtags": cmd_hashtags,
        "reto": cmd_reto,
        "generarreto": cmd_generarreto,  # 👈 NUEVO
        "puntos": cmd_puntos,
        "top10": cmd_top10,
        "trivia": cmd_trivia,
        "adivina": cmd_adivina,
        "logros": cmd_logros,
        "id": cmd_id,
        "saludar": cmd_saludar,          # 👈 OPCIONAL, si quieres /saludar
        "rules": cmd_rules,
        "about": cmd_about
    }
    
    for command, handler in command_handlers.items():
        application.add_handler(CommandHandler(command, handler))

    # Manejador de hashtags y mensajes
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_hashtags
    ))

    # Iniciar bot
    await application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
