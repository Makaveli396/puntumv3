from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime

# Retos predefinidos con validaciones string-based
WEEKLY_CHALLENGES = [
    {
        "id": 1,
        "title": "Documental Latinoamericano",
        "description": "Recomienda un documental latinoamericano anterior al año 2000",
        "hashtag": "#recomendación",
        "bonus_points": 10,
        "validation_keywords": ["argentina", "méxico", "brasil", "chile", "colombia", "perú", "venezuela", "bolivia", "ecuador"],
        "validation_type": "country_keywords"
    },
    {
        "id": 2,
        "title": "Cine de Terror Clásico",
        "description": "Reseña una película de terror de los años 70-80",
        "hashtag": "#reseña",
        "bonus_points": 15,
        "validation_keywords": ["70", "80", "1970", "1980", "terror", "horror"],
        "validation_type": "genre_keywords"
    },
]

def get_weekly_challenge():
    """Devuelve el reto predefinido en función de la semana actual"""
    week_number = datetime.now().isocalendar()[1]
    return WEEKLY_CHALLENGES[week_number % len(WEEKLY_CHALLENGES)]

def get_current_challenge():
    """Alias para get_weekly_challenge para mantener compatibilidad"""
    try:
        # Primero intenta obtener un reto personalizado desde la DB
        from db import get_challenge_from_db  # Solo importar si existe
        custom_challenge = get_challenge_from_db()
        if custom_challenge:
            return custom_challenge
    except (ImportError, AttributeError, Exception):
        # Si no existe la función en db, usa el reto automático
        pass
    
    # Devuelve el reto automático semanal
    return get_weekly_challenge()

def set_challenge_safe(challenge_text):
    """Wrapper seguro para set_challenge"""
    try:
        from db import set_challenge
        return set_challenge(challenge_text)
    except (ImportError, AttributeError, Exception) as e:
        print(f"[WARNING] set_challenge no disponible: {e}")
        return False

def clear_challenge_safe():
    """Wrapper seguro para clear_challenge"""
    try:
        from db import clear_challenge
        return clear_challenge()
    except (ImportError, AttributeError, Exception) as e:
        print(f"[WARNING] clear_challenge no disponible: {e}")
        return False

def validate_challenge_submission(challenge, message_text):
    """Valida si un mensaje cumple con los requisitos del reto"""
    message_text = message_text.lower()
    if challenge.get("validation_type") == "country_keywords":
        return any(keyword in message_text for keyword in challenge["validation_keywords"])
    elif challenge.get("validation_type") == "genre_keywords":
        return any(keyword in message_text for keyword in challenge["validation_keywords"])
    return False

async def reto_job(context: ContextTypes.DEFAULT_TYPE):
    """Job automático para publicar el reto semanal"""
    try:
        # Obtener chat_id desde job.data
        chat_id = context.job.data if context.job else None
        if not chat_id:
            print("[ERROR] reto_job: No se encontró chat_id en job.data")
            return

        reto = get_weekly_challenge()
        text = (
            f"🎬 *¡Nuevo reto semanal!*\n\n"
            f"*{reto['title']}*\n"
            f"{reto['description']}\n\n"
            f"Usa el hashtag `{reto['hashtag']}` para participar\n"
            f"🏆 Bonus: +{reto['bonus_points']} puntos adicionales"
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown"
        )
        print(f"[INFO] Reto semanal enviado al chat {chat_id}")
        
    except Exception as e:
        print(f"[ERROR] Error en reto_job: {e}")

async def cmd_reto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para mostrar el reto actual"""
    reto = get_current_challenge()
    text = (
        f"📢 *Reto semanal actual:*\n\n"
        f"*{reto['title']}*\n"
        f"{reto['description']}\n\n"
        f"*Hashtag:* `{reto['hashtag']}`\n"
        f"*Bonus:* +{reto['bonus_points']} puntos"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_nuevo_reto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para admin: limpiar reto personalizado"""
    try:
        result = set_challenge_safe("")
        if result:
            await update.message.reply_text("✅ El reto personalizado ha sido limpiado. Se usará el reto automático.")
        else:
            await update.message.reply_text("⚠️ Función de retos personalizados no disponible. Usando reto automático.")
    except Exception as e:
        print(f"[ERROR] Error en cmd_nuevo_reto: {e}")
        await update.message.reply_text("❌ Error al limpiar el reto personalizado.")

async def cmd_borrar_reto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para admin: borrar reto personalizado"""
    try:
        result = clear_challenge_safe()
        if result:
            await update.message.reply_text("🗑️ Reto semanal personalizado eliminado.")
        else:
            await update.message.reply_text("⚠️ Función de retos personalizados no disponible.")
    except Exception as e:
        print(f"[ERROR] Error en cmd_borrar_reto: {e}")
        await update.message.reply_text("❌ Error al borrar el reto personalizado.")
