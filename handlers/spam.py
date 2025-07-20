from telegram import Update

async def spam_handler(update: Update, context):
    if "gratis" in update.message.text.lower():
        await update.message.reply_text("🛑 ¡Cuidado con el spam!")
