# handlers/security.py - Sistema de seguridad y manejo de hashtags
import time
import re
from functools import wraps
from typing import Dict, List, Optional
import logging
from telegram import Update

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self):
        # Rate limiting: usuario_id -> {acción: [timestamps]}
        self.rate_limits = {}
        # Blacklist temporal para usuarios problemáticos
        self.temp_blacklist = {}
        # Patrones de spam más sofisticados
        self.spam_patterns = [
            r'(?i)(descarga|download)\s+(gratis|free)',
            r'(?i)(oferta|promocion|descuento)\s*[0-9]+%',
            r'(?i)(gana|earn)\s+(dinero|money)',
            r'https?://(?!t\.me|youtube\.com|imdb\.com)',  # URLs sospechosas
            r'(?i)telegram\s*@\w+',  # Promoción de otros canales
        ]
        # Límites por acción (acción: (max_count, window_seconds))
        self.action_limits = {
            'hashtag_usage': (5, 300),      # 5 hashtags por 5 min
            'message_send': (10, 60),       # 10 mensajes por minuto
            'command_usage': (3, 30),       # 3 comandos por 30 seg
        }
    
    def is_rate_limited(self, user_id: int, action: str) -> bool:
        """Verifica si un usuario excede los límites de rate"""
        current_time = time.time()
        
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = {}
        
        if action not in self.rate_limits[user_id]:
            self.rate_limits[user_id][action] = []
        
        user_actions = self.rate_limits[user_id][action]
        max_count, window = self.action_limits.get(action, (10, 60))
        
        # Limpiar timestamps antiguos
        cutoff = current_time - window
        user_actions[:] = [t for t in user_actions if t > cutoff]
        
        if len(user_actions) >= max_count:
            logger.warning(f"Rate limit exceeded for user {user_id} on action {action}")
            return True
        
        # Registrar nueva acción
        user_actions.append(current_time)
        return False
    
    def is_spam_content(self, text: str, user_id: int) -> Optional[str]:
        """Detecta contenido spam y retorna razón si lo encuentra"""
        # Verificar patrones de spam
        for pattern in self.spam_patterns:
            if re.search(pattern, text):
                return f"Patrón spam detectado"
        
        # Verificar exceso de mayúsculas
        if len(text) > 20:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if caps_ratio > 0.7:
                return "Exceso de mayúsculas"
        
        # Verificar repetición excesiva de caracteres
        if re.search(r'(.)\1{4,}', text):
            return "Repetición excesiva de caracteres"
        
        return None
    
    def add_to_blacklist(self, user_id: int, reason: str, duration: int = 3600):
        """Añade usuario a blacklist temporal"""
        self.temp_blacklist[user_id] = {
            'reason': reason,
            'until': time.time() + duration
        }
        logger.info(f"User {user_id} blacklisted for {duration}s: {reason}")
    
    def is_blacklisted(self, user_id: int) -> Optional[str]:
        """Verifica si usuario está en blacklist"""
        if user_id not in self.temp_blacklist:
            return None
        
        blacklist_info = self.temp_blacklist[user_id]
        if time.time() > blacklist_info['until']:
            del self.temp_blacklist[user_id]
            return None
        
        return blacklist_info['reason']
    
    def validate_hashtag_message(self, text: str, user_id: int) -> Dict[str, any]:
        """Validación completa para mensajes con hashtags"""
        result = {
            'is_valid': True,
            'warnings': [],
            'blocks': [],
            'spam_score': 0
        }
        
        # Verificar blacklist
        blacklist_reason = self.is_blacklisted(user_id)
        if blacklist_reason:
            result['is_valid'] = False
            result['blocks'].append(f"Usuario en blacklist: {blacklist_reason}")
            return result
        
        # Verificar rate limiting
        if self.is_rate_limited(user_id, 'hashtag_usage'):
            result['is_valid'] = False
            result['blocks'].append("Límite de hashtags excedido. Espera unos minutos.")
            return result
        
        # Verificar spam
        spam_reason = self.is_spam_content(text, user_id)
        if spam_reason:
            result['spam_score'] = 10
            result['warnings'].append(f"Contenido sospechoso: {spam_reason}")
            
            # Si es spam severo, bloquear
            if any(severe in spam_reason.lower() for severe in ['descarga', 'promocion', 'gana dinero']):
                result['is_valid'] = False
                result['blocks'].append("Contenido promocional no permitido")
                self.add_to_blacklist(user_id, spam_reason, 1800)  # 30 min
        
        return result

# Instancia global del security manager
security_manager = SecurityManager()

# Decorador para proteger comandos
def rate_limit(action: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(update, context):
            user_id = update.effective_user.id
            
            if security_manager.is_rate_limited(user_id, action):
                await update.message.reply_text(
                    "⏰ Vas muy rápido. Espera un momento antes de usar este comando."
                )
                return
            
            return await func(update, context)
        return wrapper
    return decorator

# === HANDLER DE HASHTAGS MEJORADO ===

POINTS = {
    "#aporte": 3,
    "#recomendación": 5,
    "#reseña": 7,
    "#crítica": 10,
    "#debate": 4,
    "#pregunta": 2,
    "#spoiler": 1,
}

# Validaciones específicas por hashtag
HASHTAG_VALIDATIONS = {
    "#reseña": {
        "min_words": 15,  # Reducido para pruebas
        "bonus_patterns": [r'\b\d{4}\b', r'\b[A-Z][a-z]+\b']  # Año, Nombres propios
    },
    "#crítica": {
        "min_words": 25,
        "bonus_patterns": [r'\b(?:cinematografía|guión|banda sonora|actuación|dirección)\b']
    },
    "#recomendación": {
        "min_words": 10,
        "bonus_patterns": [r'\b\d{4}\b', r'\b(?:Netflix|Prime|Disney|HBO)\b']  # Año o plataforma
    }
}

def count_words(text):
    """Cuenta palabras excluyendo hashtags y menciones"""
    # Remover hashtags, menciones y URLs
    clean_text = re.sub(r'#\w+|@\w+|https?://\S+', '', text)
    # Remover caracteres especiales y dividir por espacios
    words = re.findall(r'\b\w+\b', clean_text.lower())
    return len(words)

def validate_hashtag_content(hashtag: str, text: str) -> Dict[str, any]:
    """Valida contenido específico por hashtag"""
    result = {
        'is_valid': True,
        'points_modifier': 1.0,
        'warnings': [],
        'bonus_reason': None
    }
    
    if hashtag not in HASHTAG_VALIDATIONS:
        return result
    
    validation = HASHTAG_VALIDATIONS[hashtag]
    word_count = count_words(text)
    
    # Verificar longitud mínima
    min_words = validation.get('min_words', 0)
    if word_count < min_words:
        # Para pruebas, solo advertencia en lugar de invalidar
        result['warnings'].append(
            f"💡 {hashtag}: Para máximos puntos, incluye más detalles (mín. {min_words} palabras)."
        )
        result['points_modifier'] = 0.7  # Reducir puntos pero no invalidar
    
    # Verificar elementos bonus
    bonus_patterns = validation.get('bonus_patterns', [])
    bonus_found = sum(1 for pattern in bonus_patterns if re.search(pattern, text, re.IGNORECASE))
    if bonus_found > 0:
        result['points_modifier'] = min(1.5, 1.0 + (bonus_found * 0.2))  # Máximo 50% bonus
        result['bonus_reason'] = f"Bonus por información adicional (+{int((result['points_modifier']-1)*100)}%)"
    
    return result

def get_simple_reaction(hashtag: str) -> str:
    """Reacciones simples sin dependencias externas"""
    reactions = {
        "#aporte": "🎬 ¡Gracias por compartir!",
        "#reseña": "📝 ¡Excelente reseña!",
        "#crítica": "🎭 ¡Análisis profundo!",
        "#recomendación": "⭐ ¡Buena recomendación!",
        "#debate": "💬 ¡Debate interesante!",
        "#pregunta": "❓ ¡Buena pregunta!",
        "#spoiler": "⚠️ ¡Gracias por avisar!"
    }
    return reactions.get(hashtag, "🎬 ¡Gracias por participar!")

async def handle_hashtags_improved(update: Update, context):
    """Handler mejorado para procesar hashtags con seguridad avanzada"""
    if not update.message or not update.message.text:
        return
    
    text = update.message.text
    user = update.effective_user
    user_id = user.id
    username = user.username or f"user_{user_id}"
    
    logger.info(f"Processing message from {username} (ID: {user_id}): {text[:50]}...")
    
    # Verificar si hay hashtags válidos
    found_hashtags = [tag for tag in POINTS.keys() if tag in text.lower()]
    if not found_hashtags:
        logger.debug("No hashtags found, skipping")
        return
    
    # Validación de seguridad
    try:
        security_result = security_manager.validate_hashtag_message(text, user_id)
        
        if not security_result['is_valid']:
            for block_reason in security_result['blocks']:
                await update.message.reply_text(f"🚫 {block_reason}")
            return
        
        # Mostrar advertencias de seguridad si las hay
        for warning in security_result['warnings']:
            if security_result['spam_score'] > 7:  # Solo mostrar si es spam severo
                await update.message.reply_text(f"⚠️ {warning}")
                return
        
    except Exception as e:
        logger.error(f"Security validation error: {e}")
        # Continuar sin validación de seguridad en caso de error
    
    # Procesar hashtags
    total_points = 0
    found_tags = []
    warnings = []
    bonus_messages = []
    
    for hashtag, base_points in POINTS.items():
        if hashtag not in text.lower():
            continue
        
        try:
            # Validar contenido específico del hashtag
            validation_result = validate_hashtag_content(hashtag, text)
            
            # Calcular puntos con modificadores
            final_points = max(1, int(base_points * validation_result['points_modifier']))
            total_points += final_points
            
            tag_text = f"{hashtag} (+{final_points})"
            if validation_result['points_modifier'] != 1.0:
                tag_text += f" [x{validation_result['points_modifier']:.1f}]"
            
            found_tags.append(tag_text)
            
            if validation_result['bonus_reason']:
                bonus_messages.append(validation_result['bonus_reason'])
            
            # Agregar a warnings si hay
            warnings.extend(validation_result['warnings'])
            
        except Exception as e:
            logger.error(f"Error validating hashtag {hashtag}: {e}")
            # Usar puntos base sin validación
            total_points += base_points
            found_tags.append(f"{hashtag} (+{base_points})")
    
    # Si no hay puntos válidos
    if total_points == 0:
        if warnings:
            await update.message.reply_text("\n".join(warnings))
        return
    
    # Guardar puntos en base de datos
    try:
        from db import add_points
        add_points(
            user_id=user_id,
            username=username,
            points=total_points,
            hashtag=None,
            message_text=text[:500],  # Limitar longitud
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
            is_challenge_bonus=False,
            context=context
        )
        logger.info(f"Added {total_points} points for user {username}")
    except Exception as e:
        logger.error(f"Error adding points: {e}")
        await update.message.reply_text("❌ Error interno. Inténtalo más tarde.")
        return
    
    # Construir respuesta
    response_parts = []
    
    # Puntos básicos
    tags_text = ", ".join(found_tags)
    reaction = get_simple_reaction(found_hashtags[0])
    response_parts.append(f"✅ +{total_points} puntos por: {tags_text}\n{reaction}")
    
    # Mensajes bonus
    if bonus_messages:
        response_parts.extend([f"🌟 {msg}" for msg in bonus_messages])
    
    # Advertencias (solo las importantes)
    if warnings:
        response_parts.extend(warnings[:2])  # Máximo 2 advertencias
    
    # Verificar retos (con manejo de errores)
    try:
        await check_challenges(update, context, text, user_id, username, response_parts)
    except Exception as e:
        logger.error(f"Error checking challenges: {e}")
    
    # Enviar respuesta
    if response_parts:
        try:
            response_text = "\n".join(response_parts)
            if len(response_text) > 4000:  # Límite de Telegram
                response_text = response_text[:4000] + "..."
            
            await update.message.reply_text(response_text)
            logger.info(f"Sent response to {username}: {total_points} points")
            
        except Exception as e:
            logger.error(f"Error sending response: {e}")
            # Respuesta de emergencia
            try:
                await update.message.reply_text(f"✅ +{total_points} puntos!")
            except:
                pass

async def check_challenges(update, context, text, user_id, username, response_parts):
    """Verifica retos con manejo de errores mejorado"""
    try:
        # Intentar importar módulos de retos
        try:
            from handlers.retos import get_current_challenge, validate_challenge_submission
            # Reto semanal
            current_challenge = get_current_challenge()
            if current_challenge and current_challenge.get("hashtag"):
                hashtag_challenge = current_challenge["hashtag"]
                if hashtag_challenge in text.lower():
                    if validate_challenge_submission(current_challenge, text):
                        from db import add_points
                        bonus = current_challenge.get("bonus_points", 10)
                        add_points(
                            user_id=user_id,
                            username=username,
                            points=bonus,
                            hashtag=hashtag_challenge,
                            message_text=text,
                            chat_id=update.effective_chat.id,
                            message_id=update.message.message_id,
                            is_challenge_bonus=True,
                            context=context
                        )
                        response_parts.append(f"🎯 ¡Reto semanal completado! Bonus: +{bonus} puntos 🎉")
        except ImportError:
            logger.debug("Retos module not available")
        
        # Intentar reto diario
        try:
            from handlers.retos_diarios import get_today_challenge
            daily = get_today_challenge()
            if daily and check_daily_completion(daily, text):
                from db import add_points
                daily_bonus = daily.get("bonus_points", 5)
                add_points(
                    user_id=user_id,
                    username=username,
                    points=daily_bonus,
                    hashtag="(reto_diario)",
                    message_text=text,
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                    is_challenge_bonus=True,
                    context=context
                )
                response_parts.append(f"🎯 ¡Reto diario completado! Bonus: +{daily_bonus} puntos 🎉")
        except ImportError:
            logger.debug("Daily challenges module not available")
            
    except Exception as e:
        logger.error(f"Error checking challenges: {e}")

def check_daily_completion(daily_challenge, text):
    """Verifica si se completó el reto diario"""
    try:
        # Verificar hashtag específico
        if "hashtag" in daily_challenge and daily_challenge["hashtag"] in text.lower():
            if "min_words" in daily_challenge:
                return count_words(text) >= daily_challenge["min_words"]
            return True
        
        # Verificar palabras clave
        if "keywords" in daily_challenge:
            if any(word in text.lower() for word in daily_challenge["keywords"]):
                if "min_words" in daily_challenge:
                    return count_words(text) >= daily_challenge["min_words"]
                return True
        
        return False
    except Exception as e:
        logger.error(f"Error checking daily completion: {e}")
        return False
