#!/usr/bin/env python3
"""
Script para resolver conflictos de bot de Telegram
Ejecutar antes de iniciar el bot principal
"""

import asyncio
import os
import logging
from telegram.ext import ApplicationBuilder
from telegram.error import Conflict, NetworkError

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def resolver_conflicto_bot():
    """Resuelve conflictos de getUpdates del bot"""
    
    # Cargar token
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        logger.error("❌ BOT_TOKEN no encontrado")
        return False
    
    logger.info("🔧 Iniciando resolución de conflicto...")
    
    try:
        # Crear aplicación temporal
        app = ApplicationBuilder().token(bot_token).build()
        
        # Paso 1: Eliminar webhook
        logger.info("📡 Eliminando webhook...")
        await app.bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook eliminado")
        
        # Paso 2: Obtener y descartar updates pendientes
        logger.info("🧹 Descartando updates pendientes...")
        try:
            updates = await app.bot.get_updates(timeout=1, limit=100)
            if updates:
                logger.info(f"📦 Encontrados {len(updates)} updates pendientes")
                # Marcar como procesados obteniendo con offset
                last_update_id = updates[-1].update_id
                await app.bot.get_updates(offset=last_update_id + 1, timeout=1)
                logger.info("✅ Updates pendientes descartados")
            else:
                logger.info("✅ No hay updates pendientes")
        except Conflict:
            logger.warning("⚠️ Conflicto detectado durante limpieza - esto es normal")
        except Exception as e:
            logger.warning(f"⚠️ Error limpiando updates: {e}")
        
        # Paso 3: Cerrar aplicación temporal
        await app.shutdown()
        logger.info("✅ Conflicto resuelto exitosamente")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error resolviendo conflicto: {e}")
        return False

async def verificar_bot_token():
    """Verifica que el token del bot sea válido"""
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        logger.error("❌ BOT_TOKEN no encontrado")
        return False
    
    try:
        app = ApplicationBuilder().token(bot_token).build()
        me = await app.bot.get_me()
        logger.info(f"✅ Bot verificado: @{me.username} ({me.first_name})")
        await app.shutdown()
        return True
    except Exception as e:
        logger.error(f"❌ Error verificando bot: {e}")
        return False

async def main():
    """Función principal"""
    logger.info("🤖 Resolvedor de Conflictos de Bot de Telegram")
    logger.info("=" * 50)
    
    # Verificar token
    if not await verificar_bot_token():
        logger.error("💥 Token inválido - abortando")
        return
    
    # Resolver conflicto
    if await resolver_conflicto_bot():
        logger.info("🎉 ¡Listo! Ahora puedes iniciar el bot principal")
    else:
        logger.error("💥 No se pudo resolver el conflicto")
    
    logger.info("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())