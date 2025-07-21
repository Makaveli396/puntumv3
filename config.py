#!/usr/bin/env python3
"""
Configuración central del bot
"""

import os
from pathlib import Path

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv no instalado. Usando variables de entorno del sistema.")

class Config:
    """Configuración del bot"""
    
    # Token del bot (OBLIGATORIO)
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    
    # IDs de administradores (separados por comas)
    ADMIN_IDS_STR = os.environ.get("ADMIN_IDS", "5548909327")  # Cambia por tu ID
    ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(",") if id.strip()]
    
    # Configuración de base de datos
    DB_PATH = os.environ.get("DB_PATH", "puntum.db")
    BACKUP_DIR = os.environ.get("BACKUP_DIR", "backups")
    
    # Configuración de desarrollo
    DEVELOPMENT = os.environ.get("DEVELOPMENT", "1") == "1"
    DEBUG = os.environ.get("DEBUG", "0") == "1"
    
    # Configuración de producción
    PORT = int(os.environ.get("PORT", 8000))
    WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
    
    # Configuración de logging
    LOG_DIR = "logs"
    LOG_LEVEL = "DEBUG" if DEBUG else "INFO"
    
    # Configuración de juegos
    GAME_TIMEOUT = int(os.environ.get("GAME_TIMEOUT", 300))  # 5 minutos
    MAX_HINTS = int(os.environ.get("MAX_HINTS", 3))
    
    # Puntos del sistema
    POINTS_CONFIG = {
        "hashtag_basic": 1,
        "hashtag_weekly": 5,
        "daily_challenge": 10,
        "game_win": 15,
        "first_contribution": 5,
        "streak_bonus": 3
    }
    
    # Hashtags válidos
    VALID_HASHTAGS = [
        "#pelicula", "#serie", "#documental", "#corto", "#animacion",
        "#terror", "#comedia", "#drama", "#accion", "#cienciaficcion",
        "#romance", "#thriller", "#musical", "#biografia", "#western"
    ]
    
    # Niveles del usuario
    LEVELS = {
        1: {"name": "Novato Cinéfilo", "min_points": 0, "next_points": 100},
        2: {"name": "Aficionado", "min_points": 100, "next_points": 250},
        3: {"name": "Crítico Amateur", "min_points": 250, "next_points": 500},
        4: {"name": "Experto Cinematográfico", "min_points": 500, "next_points": 1000},
        5: {"name": "Maestro del Séptimo Arte", "min_points": 1000, "next_points": None}
    }
    
    @classmethod
    def validate_config(cls):
        """Validar configuración obligatoria"""
        if not cls.BOT_TOKEN:
            raise ValueError("❌ BOT_TOKEN no configurado")
        
        if not cls.ADMIN_IDS:
            raise ValueError("❌ ADMIN_IDS no configurado")
        
        # Crear directorios necesarios
        Path(cls.LOG_DIR).mkdir(exist_ok=True)
        Path(cls.BACKUP_DIR).mkdir(exist_ok=True)
        
        return True

# Hashtags semanales rotativos
WEEKLY_CHALLENGES = [
    "#peliculasdelosnoventas",
    "#cinelatinoamericano", 
    "#peliculasindependientes",
    "#cinedeautor",
    "#peliculasclasicas",
    "#cineeuropeo",
    "#peliculasdeculto",
    "#cineasiatico"
]

# Mensajes del bot
MESSAGES = {
    "welcome": """🎬 ¡Bienvenido al Bot de Películas!

🎯 **¿Qué puedes hacer aquí?**
• Comparte películas con hashtags (#pelicula)
• Participa en juegos de trivia
• Completa retos diarios y semanales
• Sube de nivel y desbloquea logros

📚 **Comandos principales:**
/help - Ver ayuda completa
/ranking - Top usuarios
/miperfil - Tu perfil y estadísticas
/reto - Ver reto del día

🎮 **Juegos disponibles:**
/cinematrivia - Trivia de películas
/adivinapelicula - Adivina por pistas
/emojipelicula - Adivina por emojis

¡Empieza compartiendo una película con #pelicula!""",
    
    "help": """📖 **AYUDA COMPLETA - Bot de Películas**

🏷️ **SISTEMA DE HASHTAGS**
• #pelicula - Comparte cualquier película (1 punto)
• #serie - Series de TV (1 punto)
• #documental - Documentales (1 punto)
• Hashtags semanales - ¡5 puntos extra!

🎯 **RETOS Y PUNTOS**
• /reto - Ver reto diario (10 puntos)
• Retos semanales rotativos (5 puntos)
• Primer post del día (bonus)
• Rachas de días consecutivos

🎮 **JUEGOS** (15 puntos por victoria)
• /cinematrivia - Preguntas de películas
• /adivinapelicula - Adivina por pistas
• /emojipelicula - Interpreta emojis
• /pista - Pedir ayuda en juego activo
• /rendirse - Abandonar juego actual

📊 **INFORMACIÓN**
• /ranking - Top 10 usuarios
• /miperfil - Tu perfil completo
• /estadisticasjuegos - Tus stats de juegos
• /topjugadores - Ranking de juegos

🔧 **ADMINISTRACIÓN** (solo admins)
• /addadmin - Agregar administrador
• /solicitudes - Ver solicitudes de grupos
• /aprobar - Autorizar grupo nuevo

💡 **TIPS**
• Usa hashtags en tus mensajes para ganar puntos
• Participa diariamente para mantener rachas
• Los juegos dan más puntos que los hashtags
• Completa retos semanales para bonus grandes""",

    "no_permissions": "❌ No tienes permisos para usar este comando",
    "group_not_authorized": "⛔ Este grupo no está autorizado. Un admin debe usar /solicitar para pedir autorización.",
    "game_timeout": "⏰ El juego ha expirado por inactividad",
    "invalid_hashtag": "❌ Hashtag no válido. Usa /help para ver los hashtags disponibles"
}
