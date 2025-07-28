# ====================================
# CONFIGURACIÓN DEL BOT DE PELÍCULAS
# ====================================

# OBLIGATORIO: Token del bot de Telegram
# Obténlo de @BotFather
BOT_TOKEN=8057941462:AAF8T-ryrPZ41XF9ySLqjphZT0EPCKhuCM8

# OBLIGATORIO: IDs de administradores (separados por comas)
# Para obtener tu ID, envía un mensaje a @userinfobot
ADMIN_IDS=5548909327,5436009474

# ====================================
# CONFIGURACIÓN DE BASE DE DATOS
# ====================================

# Ruta del archivo de base de datos
DB_PATH=puntum.db

# Directorio para respaldos automáticos
BACKUP_DIR=backups

# ====================================
# CONFIGURACIÓN DE DESARROLLO
# ====================================

# Modo desarrollo (1 = desarrollo, 0 = producción)
DEVELOPMENT=1

# Modo debug para logs detallados (1 = activado, 0 = desactivado)
DEBUG=0

# ====================================
# CONFIGURACIÓN DE PRODUCCIÓN
# ====================================

# Puerto para webhook (solo producción)
PORT=8000

# URL externa del webhook (Render, Heroku, etc.)
RENDER_EXTERNAL_URL=https://tu-app.render.com

# ====================================
# CONFIGURACIÓN DE JUEGOS
# ====================================

# Tiempo límite para juegos en segundos (300 = 5 minutos)
GAME_TIMEOUT=300

# Máximo número de pistas por juego
MAX_HINTS=3

# ====================================
# CONFIGURACIÓN AVANZADA (OPCIONAL)
# ====================================

# Intervalo de respaldo automático en horas
BACKUP_INTERVAL=24

# Días para mantener logs antiguos
LOG_RETENTION_DAYS=30

# Límite de mensajes por usuario por minuto
RATE_LIMIT=10
