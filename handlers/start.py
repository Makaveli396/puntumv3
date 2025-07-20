from telegram import Update
from telegram.ext import ContextTypes

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "🎬 *¡Luces, cámara… acción\\!* 🎬\n\n"
        "Bienvenido a *Puntum Bot*, el set donde los verdaderos cinéfilos se ganan su lugar escena por escena\\.\n\n"
        "Aquí no hay extras\\. Cada mensaje con `#aporte`, `#reseña`, `#crítica` o `#recomendación` "
        "te da puntos, reconocimiento y un lugar en el *ranking estelar*\\.\n\n"
        "🎯 Cada semana hay un reto para valientes\\. ¿Te atreves? Usa `/reto` para verlo\\.\n"
        "🏆 Usa `/mipuntaje` para saber en qué nivel estás y cuántos aplausos te faltan para el Óscar\\.\n"
        "📊 Consulta `/ranking` para ver a los más taquilleros del grupo\\.\n\n"
        "Si eres nuevo, grita `/help` como si fuera el último acto\\.\n\n"
        "_Puntum Bot no es un simple bot\\. Es tu compañero de guion en este drama colectivo llamado cine\\._ 🍿"
    )
    await update.message.reply_markdown_v2(mensaje)
