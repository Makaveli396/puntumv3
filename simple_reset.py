#!/usr/bin/env python3
"""
Script simplificado para recrear tablas - Sin dependencias externas
Este script genera comandos SQL que puedes ejecutar directamente en Render
"""

import os

def generate_reset_sql():
    """Genera el SQL completo para recrear las tablas"""
    
    sql = """
-- ====================================================
-- SCRIPT DE RECREACIÓN COMPLETA DE BASE DE DATOS
-- Ejecutar en el panel de PostgreSQL de Render
-- ====================================================

-- 1. ELIMINAR TODAS LAS TABLAS EXISTENTES
DROP TABLE IF EXISTS active_games CASCADE;
DROP TABLE IF EXISTS active_trivias CASCADE;
DROP TABLE IF EXISTS authorized_chats CASCADE;
DROP TABLE IF EXISTS auth_requests CASCADE;
DROP TABLE IF EXISTS user_points CASCADE;
DROP TABLE IF EXISTS user_ranking CASCADE;
DROP TABLE IF EXISTS chat_config CASCADE;
DROP TABLE IF EXISTS challenges CASCADE;

-- 2. CREAR TABLAS CON ESTRUCTURA CORRECTA

-- Tabla de juegos activos (con todas las columnas necesarias)
CREATE TABLE active_games (
    chat_id BIGINT PRIMARY KEY,
    juego TEXT NOT NULL,
    respuesta TEXT NOT NULL,
    pistas TEXT,
    intentos INTEGER DEFAULT 0,
    started_by BIGINT NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de trivias activas (con columna 'opciones')
CREATE TABLE active_trivias (
    chat_id BIGINT PRIMARY KEY,
    pregunta TEXT NOT NULL,
    respuesta TEXT NOT NULL,
    start_time DOUBLE PRECISION NOT NULL,
    opciones TEXT,
    message_id BIGINT,
    inline_keyboard_message_id BIGINT
);

-- Tablas de autorización
CREATE TABLE authorized_chats (
    chat_id BIGINT PRIMARY KEY,
    chat_title TEXT,
    authorized_by BIGINT,
    authorized_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active'
);

CREATE TABLE auth_requests (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    chat_title TEXT,
    requested_by BIGINT NOT NULL,
    requester_username TEXT,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending'
);

-- Tablas de usuarios y puntos
CREATE TABLE user_points (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    username TEXT,
    chat_name TEXT,
    points_gained INTEGER NOT NULL,
    reason TEXT,
    message_id BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_ranking (
    user_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    username TEXT,
    chat_name TEXT,
    total_points INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, chat_id)
);

-- Tabla de configuración de chats
CREATE TABLE chat_config (
    chat_id BIGINT PRIMARY KEY,
    chat_name TEXT,
    rankings_enabled BOOLEAN DEFAULT TRUE,
    challenges_enabled BOOLEAN DEFAULT TRUE
);

-- Tabla de desafíos
CREATE TABLE challenges (
    id SERIAL PRIMARY KEY,
    challenger_id BIGINT NOT NULL,
    challengee_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    message_id BIGINT,
    status TEXT DEFAULT 'pending',
    type TEXT,
    data TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. CREAR ÍNDICES PARA MEJORAR RENDIMIENTO
CREATE INDEX idx_user_points_user_chat ON user_points(user_id, chat_id);
CREATE INDEX idx_user_points_created_at ON user_points(created_at);
CREATE INDEX idx_user_ranking_total_points ON user_ranking(total_points DESC);
CREATE INDEX idx_auth_requests_status ON auth_requests(status);
CREATE INDEX idx_challenges_status ON challenges(status);

-- 4. INSERTAR DATOS DE EJEMPLO (OPCIONAL)
-- Descomenta las siguientes líneas si quieres datos de prueba:

/*
INSERT INTO authorized_chats (chat_id, chat_title, authorized_by, status)
VALUES (-1001234567890, 'Chat de Prueba', 123456789, 'active')
ON CONFLICT (chat_id) DO NOTHING;

INSERT INTO chat_config (chat_id, chat_name, rankings_enabled, challenges_enabled)
VALUES (-1001234567890, 'Chat de Prueba', TRUE, TRUE)
ON CONFLICT (chat_id) DO NOTHING;
*/

-- ====================================================
-- VERIFICACIÓN (Ejecutar después para confirmar)
-- ====================================================

-- Verificar que las tablas existan
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;

-- Verificar columnas problemáticas de active_games
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'active_games'
ORDER BY column_name;

-- Verificar columnas problemáticas de active_trivias  
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'active_trivias'
ORDER BY column_name;

-- ====================================================
-- FIN DEL SCRIPT
-- ====================================================
"""
    
    return sql

def save_sql_to_file():
    """Guarda el SQL en un archivo"""
    sql = generate_reset_sql()
    
    filename = "database_reset.sql"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(sql)
    
    print(f"✅ Archivo '{filename}' creado exitosamente!")
    print("\n🔧 INSTRUCCIONES:")
    print("1. Abre tu dashboard de Render")
    print("2. Ve a tu servicio PostgreSQL")
    print("3. Busca la opción 'Connect' o 'Query'")
    print("4. Copia y pega el contenido de 'database_reset.sql'")
    print("5. Ejecuta el script")
    print("6. Reinicia tu bot en Render")
    print("\n📁 Archivo guardado en:", os.path.abspath(filename))

def main():
    """Función principal"""
    print("🚀 === GENERADOR DE SCRIPT SQL PARA RECREAR BASE DE DATOS ===\n")
    
    try:
        save_sql_to_file()
        
        print("\n🎯 ALTERNATIVE: Si tienes acceso directo a psql:")
        print("psql $DATABASE_URL < database_reset.sql")
        
        print("\n🔍 VERIFICACIÓN:")
        print("Después de ejecutar el script, los siguientes comandos deberían funcionar:")
        print("• /miperfil")
        print("• /ranking") 
        print("• /reto")
        print("• /cinematrivia")
        print("• /adivinapelicula")
        
        return True
        
    except Exception as e:
        print(f"❌ Error generando archivo SQL: {e}")
        return False

if __name__ == "__main__":
    if main():
        print("\n🎉 ¡Listo! Sigue las instrucciones para aplicar los cambios.")
    else:
        print("\n💥 Error generando el script.")
