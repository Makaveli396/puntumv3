
from telegram import Update
from telegram.ext import ContextTypes

# --- COMANDO: /id ---
async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    response = f"🆔 <b>Tu ID de usuario:</b> <code>{user.id}</code>\n💬 <b>ID del chat:</b> <code>{chat.id}</code>"
    try:
        await update.message.reply_text(response, parse_mode='HTML')
    except Exception as e:
        print(f"[ERROR] No se pudo enviar el ID: {e}")

# --- COMANDO: /saludar ---
async def cmd_saludar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"👋 ¡Hola, {user.first_name}! Bienvenido/a al grupo cinéfilo 🎬")

# --- COMANDO: /rules ---
async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_text = """📜 <b>Reglas del Grupo Cinéfilo</b>

1️⃣ Respeto entre miembros  
2️⃣ Solo contenido de cine y series  
3️⃣ Marca spoilers con #spoiler  
4️⃣ No spam o mensajes repetidos  
5️⃣ Sé cinéfilo, no tóxico 🎥

¡Gracias por mantener este espacio saludable! 🍿"""
    await update.message.reply_text(rules_text, parse_mode='HTML')

# --- COMANDO: /echo ---
async def cmd_echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        response = " ".join(context.args)
    else:
        response = "🔁 Usa el comando así: /echo Tu mensaje aquí"
    await update.message.reply_text(response)

# --- COMANDO: /about ---
async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = """🤖 <b>Acerca de Puntum Bot</b>

Este bot fue creado para fomentar la participación cinéfila en grupos de Telegram.  
Puedes ganar puntos usando hashtags, compartir críticas, y respetar las reglas del grupo.

👨‍💻 Desarrollado por Makaveli396  
🔗 Código abierto en GitHub  
🎬 ¡Sigue compartiendo tu pasión por el cine! 🍿"""
    await update.message.reply_text(about_text, parse_mode='HTML')

# --- COMANDO: /info ---
async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Usa /help para ver los comandos disponibles.")

# --- COMANDO: /donate ---
async def cmd_donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    donate_text = """☕ <b>¿Quieres apoyar el desarrollo?</b>

Tu apoyo permite seguir mejorando este bot.

🧡 Puedes donar vía:
- PayPal: paypal.me/tudireccion
- Cripto: wallet123456789

¡Gracias por tu apoyo cinéfilo! 🎬"""
    await update.message.reply_text(donate_text, parse_mode='HTML')

# --- COMANDO: /contacto ---
async def cmd_contacto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📬 Contacto: @Makaveli396")

# --- COMANDO: /links ---
async def cmd_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    links = """🔗 <b>Enlaces útiles</b>
🌐 GitHub: https://github.com/Makaveli396/puntumv3
📢 Canal: https://t.me/puntum_bot
"""
    await update.message.reply_text(links, parse_mode='HTML')

# --- COMANDO: /github ---
async def cmd_github(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🧠 Código abierto: https://github.com/Makaveli396/puntumv3")

# --- COMANDO: /version ---
async def cmd_version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔢 Versión actual: PuntumBot v3.0.0")

    from weekly_challenges import get_challenge_text, generate_new_challenge

# --- COMANDO: /reto ---
async def cmd_reto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = get_challenge_text()
    await update.message.reply_text(mensaje, parse_mode='HTML')

# --- COMANDO: /generarreto ---
async def cmd_generarreto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    # Solo admins pueden usarlo
    member = await chat.get_member(user.id)
    if not member.status in ("administrator", "creator"):
        await update.message.reply_text("⛔ Solo administradores pueden generar un nuevo reto.")
        return

    reto = generate_new_challenge()

    if not reto:
        await update.message.reply_text("⚠️ No se pudo generar un nuevo reto en este momento.")
        return

    tipo_str = {
        "genre": "🎭 Género",
        "director": "🎬 Director",
        "decade": "📽️ Década"
    }.get(reto["type"], reto["type"])

    mensaje = f"""✅ <b>Nuevo reto generado</b>

📅 <b>Del:</b> {reto["start"]} <b>al</b> {reto["end"]}
{tipo_str}: <b>{reto["value"]}</b>

¡A participar cinéfilos! 🎥🍿
"""
    await update.message.reply_text(mensaje, parse_mode='HTML')

