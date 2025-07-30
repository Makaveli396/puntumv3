# db.py - Versión corregida para el manejo de conexiones

import sqlite3
from datetime import datetime
import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    """Obtiene una conexión a la base de datos."""
    if DATABASE_URL:
        # Entorno de producción (Render)
        return psycopg2.connect(DATABASE_URL)
    else:
        # Entorno local
        return sqlite3.connect("puntum.db")

def create_games_tables():
    """Crea las tablas necesarias para el sistema de juegos."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Tabla para juegos activos
        if DATABASE_URL: # PostgreSQL
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS active_games (
                    chat_id BIGINT PRIMARY KEY,
                    juego TEXT,
                    respuesta TEXT,
                    pistas TEXT,
                    intentos INTEGER,
                    started_by BIGINT,
                    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )"""
            )
        else: # SQLite
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS active_games (
                    chat_id INTEGER PRIMARY KEY,
                    juego TEXT,
                    respuesta TEXT,
                    pistas TEXT,
                    intentos INTEGER,
                    started_by INTEGER,
                    last_activity TEXT
                )"""
            )
        
        # Tabla para trivias activas
        if DATABASE_URL: # PostgreSQL
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS active_trivias (
                    chat_id BIGINT PRIMARY KEY,
                    pregunta TEXT,
                    respuesta TEXT,
                    start_time DOUBLE PRECISION,
                    opciones TEXT,
                    message_id BIGINT,
                    inline_keyboard_message_id BIGINT
                )"""
            )
        else: # SQLite
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS active_trivias (
                    chat_id INTEGER PRIMARY KEY,
                    pregunta TEXT,
                    respuesta TEXT,
                    start_time REAL,
                    opciones TEXT,
                    message_id INTEGER,
                    inline_keyboard_message_id INTEGER
                )"""
            )
        conn.commit()
        print("✅ Tablas de juegos creadas exitosamente")
    except Exception as e:
        print(f"Error al crear tablas de juegos: {e}")
        conn.rollback()
    finally:
        conn.close()

def create_auth_tables():
    """Crear tablas para el sistema de autorización"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if DATABASE_URL: # PostgreSQL
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS authorized_chats (
                    chat_id BIGINT PRIMARY KEY,
                    chat_title TEXT,
                    authorized_by BIGINT,
                    authorized_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auth_requests (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT,
                    chat_title TEXT,
                    requested_by BIGINT,
                    requester_username TEXT,
                    requested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                )
            """)
        else: # SQLite
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS authorized_chats (
                    chat_id INTEGER PRIMARY KEY,
                    chat_title TEXT,
                    authorized_by INTEGER,
                    authorized_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """)
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
        conn.commit()
        print("✅ Tablas de autorización creadas exitosamente")
    except Exception as e:
        print(f"Error al crear tablas de autorización: {e}")
        conn.rollback()
    finally:
        conn.close()

def create_user_tables():
    """Crea las tablas necesarias para el seguimiento de puntos de usuario."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if DATABASE_URL: # PostgreSQL
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS user_points (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    username TEXT,
                    chat_name TEXT,
                    points_gained INTEGER NOT NULL,
                    reason TEXT,
                    message_id BIGINT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS user_ranking (
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    username TEXT,
                    chat_name TEXT,
                    total_points INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, chat_id)
                )"""
            )
            # Tabla para configuración de chats
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS chat_config (
                    chat_id BIGINT PRIMARY KEY,
                    chat_name TEXT,
                    rankings_enabled BOOLEAN DEFAULT TRUE,
                    challenges_enabled BOOLEAN DEFAULT TRUE
                )"""
            )
        else: # SQLite
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS user_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    username TEXT,
                    chat_name TEXT,
                    points_gained INTEGER NOT NULL,
                    reason TEXT,
                    message_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS user_ranking (
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    username TEXT,
                    chat_name TEXT,
                    total_points INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, chat_id)
                )"""
            )
            # Tabla para configuración de chats
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS chat_config (
                    chat_id INTEGER PRIMARY KEY,
                    chat_name TEXT,
                    rankings_enabled INTEGER DEFAULT 1,
                    challenges_enabled INTEGER DEFAULT 1
                )"""
            )
        conn.commit()
        print("✅ Tablas de usuario creadas exitosamente")
    except Exception as e:
        print(f"Error al crear tablas de usuario: {e}")
        conn.rollback()
    finally:
        conn.close()

# El resto de las funciones permanecen igual...
# (add_points, get_top_users, etc. - no las incluyo aquí para mantener el código conciso)