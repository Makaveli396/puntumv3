# ====================================
# CONFIGURACIÓN DEL BOT DE PELÍCULAS
# ====================================

# OBLIGATORIO: Token del bot de Telegram
# Obténlo de @BotFather
BOT_TOKEN=8057941462:AAF8T-ryrPZ41XF9ySLqjphZT0EPCKhuCM8

# OBLIGATORIO: IDs de administradores (separados por comas)
# Para obtener tu ID, envía un mensaje a @userinfobot
ADMIN_IDS=5548909327,5436009474

# OPCIONAL: Clave API de TMDB para preguntas de trivia avanzadas
# Regístrate en https://www.themoviedb.org/settings/api
TMDB_API_KEY=17bb8342bff5717c23c85b661d8bb512

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