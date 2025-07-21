import sqlite3
import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from db import get_connection

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración - Administradores
ADMIN_IDS = {5548909327}  # Cambiar por tus user_ids de Telegram

# Roles disponibles
ROLES = {
    'admin': 'Administrador completo',
    'mod': 'Moderador (gestionar chats)',
    'user': 'Usuario normal'
}

def create_auth_tables():
    """Crear tablas para el sistema de autorización"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabla de chats autorizados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authorized_chats (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT,
            authorized_by INTEGER,
            authorized_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    """)
    
    # Tabla de solicitudes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            chat_title TEXT,
            requested_by INTEGER,
            requester_username TEXT,
            requested_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """)
    
    # Tabla de roles de usuario
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER PRIMARY KEY,
            role TEXT NOT NULL DEFAULT 'user',
            granted_by INTEGER,
            granted_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla de logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insertar admin principal si no existe
    for admin_id in ADMIN_IDS:
        cursor.execute("""
            INSERT OR IGNORE INTO user_roles (user_id, role) 
            VALUES (?, 'admin')
        """, (admin_id,))
    
    conn.commit()
    conn.close()
    logger.info("✅ Tablas de autorización creadas")

# ... [aquí irían todas las demás funciones del sistema de autorización]
# [las funciones que ya estaban definidas en tu archivo original]

# Comandos administrativos
async def cmd_solicitar_autorizacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Solicitar autorización para un grupo"""
    # Implementación de la función...

async def cmd_aprobar_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aprobar un grupo (solo administradores)"""
    # Implementación de la función...

async def cmd_ver_solicitudes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ver solicitudes pendientes (solo administradores)"""
    # Implementación de la función...

async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Agregar nuevo administrador"""
    # Implementación de la función...

async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remover administrador"""
    # Implementación de la función...

async def cmd_listadmins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listar administradores"""
    # Implementación de la función...

async def cmd_revocar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Revocar autorización de un grupo"""
    # Implementación de la función...

def setup_admin_list(admin_ids: list[int] = None):
    """Configurar lista de administradores iniciales"""
    if admin_ids:
        for admin_id in admin_ids:
            ADMIN_IDS.add(admin_id)
        logger.info(f"Administradores configurados: {ADMIN_IDS}")
