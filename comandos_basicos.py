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
    'debate': 4,
    'aporte': 3,
    'cinefilo': 3,
    'pelicula': 3,
    'cine': 3,
    'serie': 3,
    'director': 3,
    'oscar': 3,
    'festival': 3,
    'documental': 3,
    'animacion': 3,
    'clasico': 3,
    'independiente': 3,
    
    # Participación baja
    'actor': 2,
    'genero': 2,
    'pregunta': 2,
    'ranking': 2,
    'rankin': 2,           # Alias común
    
    # Mínimo
    'spoiler': 1
}

# Cache para control de spam (por usuario)
user_hashtag_cache = {}

# --- LÓGICA DE HASHTAGS MEJORADA (de tu archivo hashtags.py) ---

def normalize_text(text: str) -> str:
    """Normaliza texto removiendo tildes y lo convierte a minúsculas."""
    if not text:
        return ""
    # Descomponer caracteres (ej. 'á' -> 'a' + ´)
    normalized = unicodedata.normalize('NFD', text)
    # Eliminar los caracteres diacríticos (las tildes)
    normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return normalized.lower()

def find_hashtags_in_message(text: str) -> list:
    """Encuentra TODOS los hashtags válidos en un mensaje con detección flexible."""
    if not text:
        return []
    
    found_hashtags = set()
    
    # Patrón de regex que encuentra palabras después de un #
    hashtag_pattern = r'#(\w+)'
    
    # Extraer todas las posibles palabras de hashtag del texto
    potential_hashtags = re.findall(hashtag_pattern, text)
    
    for hashtag_word in potential_hashtags:
        # Normalizar la palabra encontrada para compararla con nuestra lista
        normalized_hashtag = normalize_text(hashtag_word)
        
        # Si la versión normalizada está en nuestra lista de hashtags válidos...
        if normalized_hashtag in VALID_HASHTAGS:
            points = VALID_HASHTAGS[normalized_hashtag]
            # Guardamos el hashtag original (con #) y sus puntos
            found_hashtags.add((f"#{hashtag_word}", points))
            
    # Convertir el set a lista para mantener un orden (aunque el orden original se pierde, se evitan duplicados)
    return list(found_hashtags)

def is_spam(user_id: int, hashtag: str) -> bool:
    """Detecta si un usuario está usando el mismo hashtag repetidamente."""
    current_time = time.time()
    
    if user_id not in user_hashtag_cache:
        user_hashtag_cache[user_id] = {}
    
    user_data = user_hashtag_cache[user_id]
    
    # Limpiar caché del usuario si ha pasado mucho tiempo (ej. 5 minutos)
    if user_data.get("last_time") and current_time - user_data["last_time"] > 300:
        user_data.clear()
    
    count = user_data.get(hashtag, 0) + 1
    user_data[hashtag] = count
    user_data["last_time"] = current_time
    
    # Si el mismo hashtag se usa más de 3 veces en 5 minutos, es spam
    return count > 3

def count_words(text: str) -> int:
    """Cuenta las palabras en un texto, excluyendo los propios hashtags."""
    if not text:
        return 0
    # Elimina los hashtags para no contarlos como palabras
    text_without_hashtags = re.sub(r'#\w+', '', text)
    return len(text_without_hashtags.split())

# --- MANEJADOR DE HASHTAGS (PRINCIPAL) ---

async def handle_hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    message_text = update.message.text
    user = update.effective_user
    chat = update.effective_chat
    
    # 1. Encontrar hashtags válidos en el mensaje
    found_hashtags = find_hashtags_in_message(message_text)
    
    if not found_hashtags:
        return # No hay nada que procesar
    
    valid_hashtags_for_points = []
    total_points = 0
    warnings = []
    
    word_count = count_words(message_text)
    
    # 2. Validar cada hashtag encontrado
    for hashtag, points in found_hashtags:
        normalized_hashtag = normalize_text(hashtag[1:]) # Quita el # para validar
        
        # Control de spam
        if is_spam(user.id, hashtag):
            warnings.append(f"⚠️ {hashtag}: Has usado este hashtag muy seguido. Intenta variar.")
            continue
        
        # --- VALIDACIONES ESPECIALES (CORREGIDAS) ---
        original_points = points
        
        # Validación para #critica
        if normalized_hashtag == "critica" and word_count < 100:
            warnings.append(f"❌ Para #critica se requiere un análisis de mín. 100 palabras (tienes {word_count}).")
            points = max(1, points // 2) # Penalización de puntos, pero se da algo
        
        # Validación para #reseña
        elif normalized_hashtag in ["reseña", "resena"] and word_count < 50:
            warnings.append(f"❌ Para #reseña se requiere un texto de mín. 50 palabras (tienes {word_count}).")
            points = max(1, points // 2)
        
        valid_hashtags_for_points.append((hashtag, points))
        total_points += points
    
    if total_points <= 0:
        return # No hay puntos que dar
        
    # 3. Bonus por mensaje largo
    bonus_text = ""
    if len(message_text) > 280: # Caracteres, no palabras
        total_points += 2
        bonus_text = " (+2 bonus por detalle)"

    # 4. Guardar en la base de datos
    try:
        primary_hashtag = valid_hashtags_for_points[0][0] if valid_hashtags_for_points else "#aporte"
        add_points(
            user_id=user.id,
            username=user.username or user.first_name,
            points=total_points,
            hashtag=primary_hashtag,
            message_text=message_text[:250], # Guardar un trozo del mensaje
            chat_id=chat.id,
            message_id=update.message.message_id
        )
    except Exception as e:
        logger.error(f"Error al guardar puntos en la BD para el usuario {user.id}: {e}")
        await update.message.reply_text("🚨 Hubo un error al guardar tus puntos. Por favor, contacta a un admin.")
        return

    # 5. Enviar respuesta al usuario
    hashtags_list_str = ", ".join([h for h, p in valid_hashtags_for_points])
    
    response_header = random.choice([
        "¡Excelente aporte cinéfilo!", "¡Puntos ganados!", "¡Gran contribución!",
        "¡Sigue así, cinéfilo!", "¡Fantástico análisis!"
    ])
    
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
        await update.message.reply_text(
            response_text,
            parse_mode='HTML',
            reply_to_message_id=update.message.message_id
        )
        logger.info(f"Usuario {user.id} ganó {total_points} puntos con: {hashtags_list_str}")
    except Exception as e:
        logger.error(f"Error al enviar respuesta de puntos a {user.id}: {e}")
        # Respuesta de emergencia si el HTML falla
        await update.message.reply_text(f"¡Ganaste +{total_points} puntos! (Hubo un error al mostrar el detalle)")

# (El resto de tus comandos: cmd_start, cmd_help, cmd_ranking, cmd_miperfil, cmd_reto, etc., van aquí sin cambios)
# ...
