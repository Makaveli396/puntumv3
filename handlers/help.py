from telegram import Update
from telegram.ext import ContextTypes

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "🎬 *Bienvenido a Puntum Bot: cinefilia sin censura* 🎬\n\n"
        "Aquí no hay espacio para el aburrimiento\\. Este bot es tu asistente en la jungla del cine, donde cada aporte cuenta y cada reseña deja huella\\.\n\n"
        "📌 *¿Qué puedes hacer?*\n\n"
        "*Comandos disponibles:*\n"
        "▪️ `/start` — Despierta al bot, como si abrieras el telón\\.\n"
        "▪️ `/help` — Estás aquí\\. ¿Qué más quieres?\n"
        "▪️ `/ranking` — Top 10 cinéfilos\\. Solo los duros sobreviven\\.\n"
        "▪️ `/reto` — El desafío de la semana\\. ¿Tienes agallas?\n"
        "▪️ `/mipuntaje` — Muestra tus stats\\. ¿Eres el protagonista o un extra más?\n\n"
        "👑 *¿Cómo ganar puntos?*\n\n"
        "Usa hashtags al estilo salvaje:\n"
        "🔸 `#aporte` — 3 pts: Comparte links o joyas ocultas\\.\n"
        "🔸 `#recomendación` — 5 pts: Que no se te escape ese peliculón\\.\n"
        "🔸 `#reseña` — 7 pts: Escribe como si fueras Scorsese\\. \\(Mín\\. 50 palabras\\)\n"
        "🔸 `#crítica` — 10 pts: A lo Tarantino, sin filtros\\. \\(Mín\\. 100 palabras\\)\n"
        "🔸 `#pregunta`, `#spoiler`, `#debate` — Más puntos si prendes fuego al grupo\\.\n\n"
        "⚠️ *El spam no se perdona* \\(ni repetir hashtags como loro\\)\\. Usa con cabeza\\.\n\n"
        "🎯 *Reto Semanal*\n"
        "Cada semana hay un reto temático que da *puntos extra*\\. Usa `/reto` para verlo y participa con el hashtag correcto\\. Si cumples las condiciones, te llevas el bono\\.\n\n"
        "🎭 *Sistema de Niveles*\n"
        "Sube de nivel y obtén títulos como:\n"
        "• 🎞️ Proyector de Barrio\n"
        "• 📽️ Crítico Emergente\n"
        "• 🎬 Director Honorario\n"
        "• 🏆 Cinéfilo de Oro\n"
        "• 👑 Maestro del Séptimo Arte\n\n"
        "💬 *Frases trigger:*\n"
        "¿Dijiste \\*cine\\*\\? Entonces prepárate, porque el bot responde\\. Como en un buen guion, las palabras importan\\.\n\n"
        "_Puntum Bot no es solo un bot\\. Es una experiencia Tarantinesca\\._ 💥"
    )
    
    await update.message.reply_markdown_v2(mensaje)
