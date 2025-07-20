#!/usr/bin/env python3

from telegram import Update
from telegram.ext import ContextTypes
from db import get_user_stats, get_top10, add_points
import random
import datetime
import logging
import re
import time
import unicodedata

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# HASHTAGS UNIFICADOS - SIN REPETICIONES Y CON DETECCIÓN FLEXIBLE
VALID_HASHTAGS = {
    # Alto valor
    'critica': 10,         # Análisis profundo, mínimo 20 palabras  
    'reseña': 7,           # Reseña detallada, mínimo 50 palabras
    'resena': 7,           # Sin tilde
    'recomendacion': 5,    # Formato específico requerido
    
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
    'rankin': 2,           # Typo común
    
    # Mínimo
    'spoiler': 1
}

# Cache para control de spam
user_hashtag_cache = {}

def normalize_text(text):
    """Normaliza texto removiendo tildes y caracteres especiales"""
    if not text:
        return ""
    
    # Remover tildes y normalizar
    normalized = unicodedata.normalize('NFD', text)
    normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    
    # Convertir a minúsculas
    return normalized.lower()

def find_hashtags_in_message(text):
    """FUNCIÓN CORREGIDA - Encuentra TODOS los hashtags válidos con detección mejorada"""
    if not text:
        return []
    
    print(f"[DEBUG] 🔍 Texto original: '{text}'")
    
    found_hashtags = []
    
    # ✅ PATRONES MEJORADOS - Detecta hashtags en CUALQUIER posición
    hashtag_patterns = [
        # Patrón principal: # seguido de palabra (Unicode completo)
        r'#([\w\u00C0-\u024F\u1E00-\u1EFF]+)',
        # Patrón con espacio después del #
        r'#\s+([\w\u00C0-\u024F\u1E00-\u1EFF]+)',
        # Patrón al final de línea o antes de puntuación
        r'#([\w\u00C0-\u024F\u1E00-\u1EFF]+)(?=\s|$|[.,;:!?])',
    ]
    
    for i, pattern in enumerate(hashtag_patterns):
        hashtags_found = re.findall(pattern, text, re.IGNORECASE | re.UNICODE)
        
        for hashtag_word in hashtags_found:
            # Limpiar la palabra (remover espacios extra)
            hashtag_word = hashtag_word.strip()
            if not hashtag_word:
                continue
                
            # Normalizar la palabra encontrada
            normalized_hashtag = normalize_text(hashtag_word)
            
            print(f"[DEBUG] 🏷️ Hashtag encontrado (patrón {i+1}): '{hashtag_word}' -> normalizado: '{normalized_hashtag}'")
            
            # Verificar si está en la lista de hashtags válidos
            if normalized_hashtag in VALID_HASHTAGS:
                points = VALID_HASHTAGS[normalized_hashtag]
                found_hashtags.append((f"#{hashtag_word}", points))
                print(f"[DEBUG] ✅ VÁLIDO: #{hashtag_word} = {points} puntos")
            else:
                print(f"[DEBUG] ❌ NO VÁLIDO: #{hashtag_word} (normalizado: {normalized_hashtag})")
                # DEBUG ADICIONAL: Mostrar hashtags válidos similares
                similar = [h for h in VALID_HASHTAGS.keys() if h.startswith(normalized_hashtag[:3])]
                if similar:
                    print(f"[DEBUG] 💡 Hashtags similares disponibles: {similar}")
    
    # Eliminar duplicados manteniendo el orden
    unique_hashtags = []
    seen = set()
    for hashtag, points in found_hashtags:
        hashtag_lower = normalize_text(hashtag)
        if hashtag_lower not in seen:
            unique_hashtags.append((hashtag, points))
            seen.add(hashtag_lower)
    
    print(f"[DEBUG] 🎯 Hashtags únicos finales: {unique_hashtags}")
    return unique_hashtags

def is_spam(user_id, hashtag):
    """Detecta spam basado en frecuencia de hashtags por usuario"""
    current_time = time.time()
    
    if user_id not in user_hashtag_cache:
        user_hashtag_cache[user_id] = {}
    
    user_data = user_hashtag_cache[user_id]
    
    # Limpiar datos antiguos (más de 5 minutos)
    if "last_time" in user_data and current_time - user_data["last_time"] > 300:
        user_data.clear()
    
    # Contar uso del hashtag
    if hashtag in user_data:
        user_data[hashtag] = user_data.get(hashtag, 0) + 1
        if user_data[hashtag] > 3:  # Máximo 3 veces en 5 minutos
            return True
    else:
        user_data[hashtag] = 1
    
    user_data["last_time"] = current_time
    return False

def count_words(text):
    """Cuenta palabras sin incluir hashtags"""
    if not text:
        return 0
    text_without_hashtags = re.sub(r'#\w+', '', text)
    return len(text_without_hashtags.split())

# Niveles del sistema
LEVEL_THRESHOLDS = {
    1: (0, 99, "Novato Cinéfilo", "🌱"),
    2: (100, 249, "Aficionado", "🎭"),
    3: (250, 499, "Crítico Amateur", "🎬"),
    4: (500, 999, "Experto Cinematográfico", "🏆"),
    5: (1000, float('inf'), "Maestro del Séptimo Arte", "👑")
}

def calculate_level(points):
    """Calcular nivel basado en puntos"""
    for level, (min_pts, max_pts, _, _) in LEVEL_THRESHOLDS.items():
        if min_pts <= points <= max_pts:
            return level
    return 1

async def handle_hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """FUNCIÓN PRINCIPAL MEJORADA - Detecta TODOS los hashtags válidos"""
    if not update.message or not update.message.text:
        return
    
    message_text = update.message.text
    user = update.effective_user
    chat = update.effective_chat
    
    print(f"[DEBUG] 🔍 === INICIANDO PROCESAMIENTO ===")
    print(f"[DEBUG] 👤 Usuario: {user.username or user.first_name} (ID: {user.id})")
    print(f"[DEBUG] 📝 Mensaje: '{message_text}'")
    print(f"[DEBUG] 💬 Chat: {chat.id}")
    
    # 🎯 DETECCIÓN MEJORADA DE HASHTAGS
    found_hashtags = find_hashtags_in_message(message_text)
    
    if not found_hashtags:
        print(f"[DEBUG] ❌ No se encontraron hashtags válidos")
        return
    
    print(f"[DEBUG] ✅ Hashtags detectados: {found_hashtags}")
    
    # Verificar spam y calcular puntos
    valid_hashtags = []
    total_points = 0
    warnings = []
    
    for hashtag, points in found_hashtags:
        hashtag_word = hashtag[1:].lower()  # Remover # y convertir a minúsculas
        
        print(f"[DEBUG] 🔄 Procesando: {hashtag} ({points} pts)")
        
        # Verificar spam
        if is_spam(user.id, hashtag):
            warnings.append(f"⚠️ {hashtag}: Detectado spam. Usa hashtags con moderación.")
            print(f"[DEBUG] 🚫 Spam detectado para {hashtag}")
            continue
        
        # Validaciones especiales
        word_count = count_words(message_text)
        original_points = points
        
        if hashtag_word == "critica" and word_count < 25:
            warnings.append(f"❌ {hashtag}: Necesitas análisis más profundo (mín. 100 palabras). Tienes ~{word_count*4} palabras.")
            points = max(1, points // 2)
        elif hashtag_word in ["reseña", "resena"] and word_count < 15:
            warnings.append(f"❌ {hashtag}: Necesitas reseña más detallada (mín. 50 palabras). Tienes ~{word_count*4} palabras.")
            points = max(1, points // 2)
        
        valid_hashtags.append((hashtag, points))
        total_points += points
        
        print(f"[DEBUG] ✅ {hashtag}: {original_points} -> {points} puntos")
    
    if total_points <= 0:
        print(f"[DEBUG] ❌ Total de puntos = 0, no procesar")
        return
    
    # Bonus por mensaje detallado
    bonus_text = ""
    if len(message_text) > 150:
        total_points += 2
        bonus_text = " (+2 bonus detalle)"
        print(f"[DEBUG] 💎 Bonus por detalle: +2 puntos")
    
    print(f"[DEBUG] 💰 Total final: {total_points} puntos")
    
    try:
        # Guardar en base de datos
        primary_hashtag = valid_hashtags[0][0] if valid_hashtags else "#aporte"
        
        print(f"[DEBUG] 💾 Guardando en BD...")
        add_points(
            user_id=user.id,
            username=user.username or user.first_name,
            points=total_points,
            hashtag=primary_hashtag,
            message_text=message_text[:200],
            chat_id=chat.id,
            message_id=update.message.message_id,
            context=context
        )
        
        print(f"[DEBUG] ✅ Datos guardados exitosamente")
        
        # Crear respuesta - FORMATEO CORREGIDO
        hashtags_list = ", ".join([h[0] for h, p in valid_hashtags])
        
        responses = [
            "¡Excelente aporte cinéfilo!",
            "¡Puntos ganados!",
            "¡Gran contribución al cine!",
            "¡Sigue así, cinéfilo!",
            "¡Fantástico análisis!",
            "¡Perfecto para el grupo!"
        ]
        
        random_response = random.choice(responses)
        
        # ✅ CORRECCIÓN CRÍTICA: Usar solo HTML, eliminar ** que causa conflicto
        response = f"""✅ <b>{random_response}</b> 🎬

👤 {user.mention_html()}
🏷️ {hashtags_list}  
💎 <b>+{total_points} puntos</b>{bonus_text}

🎭 ¡Sigue compartiendo tu pasión por el cine! 🍿"""
        
        # Agregar advertencias si las hay
        if warnings:
            response += f"\n\n⚠️ <b>Notas:</b>\n" + "\n".join(warnings)
        
        await update.message.reply_text(
            response, 
            parse_mode='HTML',
            reply_to_message_id=update.message.message_id
        )
        
        print(f"[DEBUG] ✅ Respuesta enviada correctamente")
        logger.info(f"Usuario {user.id} ganó {total_points} puntos con: {hashtags_list}")
        
    except Exception as e:
        logger.error(f"❌ ERROR en handle_hashtags: {e}")
        import traceback
        traceback.print_exc()
        
        # Respuesta de emergencia - TAMBIÉN CORREGIDA
        try:
            await update.message.reply_text(f"✅ ¡Puntos ganados! +{total_points} pts 🎬")
            print(f"[DEBUG] 🆘 Respuesta de emergencia enviada")
        except Exception as e2:
            print(f"[DEBUG] ❌ Error crítico: No se pudo enviar respuesta: {e2}")

    print(f"[DEBUG] 🏁 === PROCESAMIENTO TERMINADO ===\n")
