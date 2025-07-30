#!/usr/bin/env python3
"""
Script para recrear completamente las tablas de la base de datos
Úsalo cuando necesites empezar desde cero con una estructura limpia
"""

import os
import psycopg2
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    """Obtiene conexión a PostgreSQL"""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL no está configurada")
    return psycopg2.connect(DATABASE_URL)

def drop_all_tables():
    """Elimina TODAS las tablas existentes"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        logger.info("🗑️  Eliminando todas las tablas existentes...")
        
        # Lista de todas las tablas que queremos eliminar
        tables_to_drop = [
            'active_games',
            'active_trivias', 
            'authorized_chats',
            'auth_requests',
            'user_points',
            'user_ranking',
            'chat_config',
            'challenges'
        ]
        
        for table in tables_to_drop:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                logger.info(f"✅ Tabla '{table}' eliminada")
            except Exception as e:
                logger.warning(f"⚠️  Error eliminando tabla '{table}': {e}")
        
        conn.commit()
        logger.info("🎯 Todas las tablas eliminadas exitosamente")
        
    except Exception as e:
        logger.error(f"❌ Error eliminando tablas: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def create_fresh_tables():
    """Crea todas las tablas con la estructura correcta"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        logger.info("🔨 Creando tablas con estructura actualizada...")
        
        # === TABLA DE JUEGOS ACTIVOS ===
        cursor.execute("""
            CREATE TABLE active_games (
                chat_id BIGINT PRIMARY KEY,
                juego TEXT NOT NULL,
                respuesta TEXT NOT NULL,
                pistas TEXT,
                intentos INTEGER DEFAULT 0,
                started_by BIGINT NOT NULL,
                last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ Tabla 'active_games' creada")
        
        # === TABLA DE TRIVIAS ACTIVAS ===
        cursor.execute("""
            CREATE TABLE active_trivias (
                chat_id BIGINT PRIMARY KEY,
                pregunta TEXT NOT NULL,
                respuesta TEXT NOT NULL,
                start_time DOUBLE PRECISION NOT NULL,
                opciones TEXT,
                message_id BIGINT,
                inline_keyboard_message_id BIGINT
            )
        """)
        logger.info("✅ Tabla 'active_trivias' creada")
        
        # === TABLAS DE AUTORIZACIÓN ===
        cursor.execute("""
            CREATE TABLE authorized_chats (
                chat_id BIGINT PRIMARY KEY,
                chat_title TEXT,
                authorized_by BIGINT,
                authorized_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        """)
        logger.info("✅ Tabla 'authorized_chats' creada")
        
        cursor.execute("""
            CREATE TABLE auth_requests (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                chat_title TEXT,
                requested_by BIGINT NOT NULL,
                requester_username TEXT,
                requested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        """)
        logger.info("✅ Tabla 'auth_requests' creada")
        
        # === TABLAS DE USUARIOS Y PUNTOS ===
        cursor.execute("""
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
            )
        """)
        logger.info("✅ Tabla 'user_points' creada")
        
        cursor.execute("""
            CREATE TABLE user_ranking (
                user_id BIGINT NOT NULL,
                chat_id BIGINT NOT NULL,
                username TEXT,
                chat_name TEXT,
                total_points INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        logger.info("✅ Tabla 'user_ranking' creada")
        
        # === TABLA DE CONFIGURACIÓN DE CHATS ===
        cursor.execute("""
            CREATE TABLE chat_config (
                chat_id BIGINT PRIMARY KEY,
                chat_name TEXT,
                rankings_enabled BOOLEAN DEFAULT TRUE,
                challenges_enabled BOOLEAN DEFAULT TRUE
            )
        """)
        logger.info("✅ Tabla 'chat_config' creada")
        
        # === TABLA DE DESAFÍOS ===
        cursor.execute("""
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
            )
        """)
        logger.info("✅ Tabla 'challenges' creada")
        
        # === ÍNDICES PARA MEJORAR RENDIMIENTO ===
        logger.info("🔧 Creando índices...")
        
        cursor.execute("CREATE INDEX idx_user_points_user_chat ON user_points(user_id, chat_id)")
        cursor.execute("CREATE INDEX idx_user_points_created_at ON user_points(created_at)")
        cursor.execute("CREATE INDEX idx_user_ranking_total_points ON user_ranking(total_points DESC)")
        cursor.execute("CREATE INDEX idx_auth_requests_status ON auth_requests(status)")
        cursor.execute("CREATE INDEX idx_challenges_status ON challenges(status)")
        
        logger.info("✅ Índices creados")
        
        conn.commit()
        logger.info("🎉 ¡Base de datos recreada exitosamente!")
        
    except Exception as e:
        logger.error(f"❌ Error creando tablas: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def add_sample_data():
    """Añade datos de ejemplo para probar (opcional)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        logger.info("📊 Añadiendo datos de ejemplo...")
        
        # Autorizar un chat de ejemplo
        cursor.execute("""
            INSERT INTO authorized_chats (chat_id, chat_title, authorized_by, status)
            VALUES (-1001234567890, 'Chat de Prueba', 123456789, 'active')
            ON CONFLICT (chat_id) DO NOTHING
        """)
        
        # Configuración de chat de ejemplo
        cursor.execute("""
            INSERT INTO chat_config (chat_id, chat_name, rankings_enabled, challenges_enabled)
            VALUES (-1001234567890, 'Chat de Prueba', TRUE, TRUE)
            ON CONFLICT (chat_id) DO NOTHING
        """)
        
        conn.commit()
        logger.info("✅ Datos de ejemplo añadidos")
        
    except Exception as e:
        logger.error(f"❌ Error añadiendo datos de ejemplo: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def verify_tables():
    """Verifica que todas las tablas y columnas existan correctamente"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        logger.info("🔍 Verificando estructura de tablas...")
        
        # Verificar que las tablas existan
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        expected_tables = [
            'active_games', 'active_trivias', 'authorized_chats', 
            'auth_requests', 'user_points', 'user_ranking', 
            'chat_config', 'challenges'
        ]
        
        for table in expected_tables:
            if table in table_names:
                logger.info(f"✅ Tabla '{table}' existe")
                
                # Verificar columnas específicas problemáticas
                if table == 'active_games':
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'active_games'
                    """)
                    columns = [col[0] for col in cursor.fetchall()]
                    required_cols = ['respuesta', 'last_activity', 'pistas']
                    for col in required_cols:
                        if col in columns:
                            logger.info(f"  ✅ Columna '{col}' existe")
                        else:
                            logger.error(f"  ❌ Columna '{col}' NO existe")
                
                elif table == 'active_trivias':
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'active_trivias'
                    """)
                    columns = [col[0] for col in cursor.fetchall()]
                    if 'opciones' in columns:
                        logger.info(f"  ✅ Columna 'opciones' existe")
                    else:
                        logger.error(f"  ❌ Columna 'opciones' NO existe")
            else:
                logger.error(f"❌ Tabla '{table}' NO existe")
        
        logger.info("🎯 Verificación completada")
        
    except Exception as e:
        logger.error(f"❌ Error verificando tablas: {e}")
    finally:
        cursor.close()
        conn.close()

def main():
    """Función principal - Recrear base de datos completa"""
    try:
        logger.info("🚀 === RECREACIÓN COMPLETA DE BASE DE DATOS ===")
        
        # Paso 1: Eliminar tablas existentes
        drop_all_tables()
        
        # Paso 2: Crear tablas nuevas
        create_fresh_tables()
        
        # Paso 3: Añadir datos de ejemplo (opcional)
        add_sample_data()
        
        # Paso 4: Verificar que todo esté correcto
        verify_tables()
        
        logger.info("🎉 === RECREACIÓN COMPLETADA EXITOSAMENTE ===")
        logger.info("💡 El bot debería funcionar correctamente ahora")
        logger.info("🔄 Reinicia el bot para aplicar los cambios")
        
    except Exception as e:
        logger.error(f"💥 Error crítico durante la recreación: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if main():
        print("\n✅ ¡Base de datos recreada exitosamente!")
        print("🔄 Reinicia tu bot en Render para aplicar los cambios")
    else:
        print("\n❌ Error durante la recreación de la base de datos")
        print("🔍 Revisa los logs para más detalles")
