# phrases.py (nuevo sistema de frases cinéfilas por categoría)
import random
from telegram import Update
from telegram.ext import ContextTypes

# Historial simple para evitar repeticiones por usuario
last_reaction_by_user = {}

def get_random_reaction(hashtag: str, user_id: int) -> str:
    hashtag = hashtag.lower()

    REACTION_PHRASES = {
        "#aporte": [
            "📡 Transmitiendo conocimiento como una antena soviética.",
            "🎞️ Aporte digno de un archivo fílmico nacional.",
            "📁 Este aporte es más valioso que una cinta de 35mm sin rayones."
        ],
        "#recomendación": [
            "🎯 Esta recomendación apunta directo al corazón cinéfilo.",
            "🎬 Perfecta para una noche de cine con vino y teoría de autor.",
            "💡 Esta peli iría directo al watchlist de Truffaut."
        ],
        "#reseña": [
            "📝 Scorsese aprobaría esta reseña sin editar una coma.",
            "📖 Tus palabras tienen más peso que una voz en off de Malick.",
            "🎭 Esta reseña merece un aplauso lento, estilo Cannes."
        ],
        "#crítica": [
            "🔍 Crítica con bisturí, ni Kubrick fue tan preciso.",
            "🎬 Esta crítica es más afilada que los encuadres de Hitchcock.",
            "🔥 Tarantino estaría tomando nota con una copa de whisky."
        ],
        "#debate": [
            "🤔 El debate está servido. Que rueden las ideas como celuloide.",
            "🎤 Esto se pone más interesante que una mesa redonda en Berlinale.",
            "🧠 Diálogo de altura. Como Godard contra el mundo."
        ],
        "#pregunta": [
            "❓ La pregunta correcta siempre enciende el fuego del cine-foro.",
            "🎬 Buena duda. Hasta Tarkovsky tendría que pensarla.",
            "🔎 Pregunta que podría desencadenar una trilogía de respuestas."
        ],
        "#spoiler": [
            "⚠️ Alerta de spoiler con estilo. Te perdonamos esta vez."
        ],
        "default": [
            "🎥 Esto merece un slow clap con fondo de Morricone.",
            "📽️ Cine del bueno. Sigue así."
        ]
    }

    frases = REACTION_PHRASES.get(hashtag, REACTION_PHRASES["default"])
    last = last_reaction_by_user.get(user_id)
    opciones = [f for f in frases if f != last] or frases  # evita repetir
    elegida = random.choice(opciones)
    last_reaction_by_user[user_id] = elegida
    return elegida

# Middleware function for handling phrase reactions
async def phrase_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Middleware that detects hashtags in messages and responds with cinematic phrases
    """
    if not update.message or not update.message.text:
        return
    
    message_text = update.message.text.lower()
    user_id = update.effective_user.id
    
    # List of supported hashtags
    hashtags = ["#aporte", "#recomendación", "#reseña", "#crítica", "#debate", "#pregunta", "#spoiler"]
    
    # Check if any hashtag is present in the message
    for hashtag in hashtags:
        if hashtag in message_text:
            reaction = get_random_reaction(hashtag, user_id)
            await update.message.reply_text(reaction)
            break  # Only respond to the first hashtag found
