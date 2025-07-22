# ====================================
# HANDLERS DE CALLBACKS (continuación)
# ====================================

async def handle_authorization_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar callbacks de botones de autorización"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.edit_message_text("❌ No tienes permisos para esta acción.")
        return
    
    data = query.data
    
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        if data.startswith("approve_"):
            parts = data.split("_")
            req_id = int(parts[1])
            chat_id = int(parts[2])
            
            # Obtener información de la solicitud
            cursor.execute("""
                SELECT chat_name, chat_type, requested_by, requester_username
                FROM authorization_requests 
                WHERE id = ?
            """, (req_id,))
            
            result = cursor.fetchone()
            if not result:
                await query.edit_message_text("❌ Solicitud no encontrada.")
                conn.close()
                return
            
            chat_name, chat_type, requested_by, requester_username = result
            
            # Autorizar chat
            if authorize_chat(chat_id, chat_name, chat_type, query.from_user.id):
                await query.edit_message_text(
                    f"✅ **Chat autorizado exitosamente**\n\n"
                    f"**Grupo:** {chat_name}\n"
                    f"**ID:** `{chat_id}`\n"
                    f"**Autorizado por:** @{query.from_user.username}",
                    parse_mode='Markdown'
                )
                
                # Notificar al solicitante si es posible
                try:
                    await context.bot.send_message(
                        chat_id=requested_by,
                        text=f"🎉 **¡Tu solicitud ha sido aprobada!**\n\n"
                             f"El grupo **{chat_name}** ahora está autorizado.\n"
                             f"¡Disfruta del bot! 🎬"
                    )
                except Exception as e:
                    logger.warning(f"No se pudo notificar al usuario {requested_by}: {e}")
                
            else:
                await query.edit_message_text("❌ Error autorizando el chat.")
                
        elif data.startswith("reject_"):
            parts = data.split("_")
            req_id = int(parts[1])
            chat_id = int(parts[2])
            
            # Obtener información de la solicitud
            cursor.execute("""
                SELECT chat_name, requested_by, requester_username
                FROM authorization_requests 
                WHERE id = ?
            """, (req_id,))
            
            result = cursor.fetchone()
            if not result:
                await query.edit_message_text("❌ Solicitud no encontrada.")
                conn.close()
                return
            
            chat_name, requested_by, requester_username = result
            
            # Marcar como rechazada
            cursor.execute("""
                UPDATE authorization_requests 
                SET status = 'rejected'
                WHERE id = ?
            """, (req_id,))
            
            # Log de la acción
            log_auth_action(cursor, "REQUEST_REJECTED", chat_id, query.from_user.id, 
                           f"Solicitud rechazada por {query.from_user.username}")
            
            conn.commit()
            
            await query.edit_message_text(
                f"❌ **Solicitud rechazada**\n\n"
                f"**Grupo:** {chat_name}\n"
                f"**ID:** `{chat_id}`\n"
                f"**Rechazado por:** @{query.from_user.username}",
                parse_mode='Markdown'
            )
            
            # Notificar al solicitante si es posible
            try:
                await context.bot.send_message(
                    chat_id=requested_by,
                    text=f"⚠️ **Tu solicitud ha sido rechazada**\n\n"
                         f"El grupo **{chat_name}** no fue autorizado.\n"
                         f"Contacta a los administradores para más información."
                )
            except Exception as e:
                logger.warning(f"No se pudo notificar al usuario {requested_by}: {e}")
                
        elif data == "refresh_requests":
            # Volver a mostrar las solicitudes
            await cmd_ver_solicitudes(update, context)
            await query.delete_message()
            return
            
        conn.close()
        
    except Exception as e:
        logger.error(f"Error procesando callback: {e}")
        await query.edit_message_text("❌ Error procesando la acción.")

# ====================================
# INICIALIZACIÓN DEL SISTEMA
# ====================================

def initialize_auth_system(application):
    """Registrar todos los handlers de autorización"""
    # Comandos de autorización
    application.add_handler(CommandHandler("solicitar", cmd_solicitar_autorizacion))
    application.add_handler(CommandHandler("aprobar", cmd_aprobar_grupo))
    application.add_handler(CommandHandler("revocar", cmd_revocar_grupo))
    application.add_handler(CommandHandler("solicitudes", cmd_ver_solicitudes))
    
    # Comandos administrativos
    application.add_handler(CommandHandler("addadmin", cmd_addadmin))
    application.add_handler(CommandHandler("removeadmin", cmd_removeadmin))
    application.add_handler(CommandHandler("listadmins", cmd_listadmins))
    application.add_handler(CommandHandler("chats", cmd_chats_autorizados))
    application.add_handler(CommandHandler("statsauth", cmd_stats_auth))
    
    # Handlers de callback
    application.add_handler(CallbackQueryHandler(handle_authorization_callback, pattern="^(approve|reject|refresh)_"))
    
    logger.info("✅ Sistema de autorización inicializado")

# ====================================
# EJECUCIÓN PARA PRUEBAS
# ====================================

if __name__ == "__main__":
    # Pruebas de la base de datos
    logging.basicConfig(level=logging.INFO)
    create_auth_tables()
    
    print("✅ Pruebas completadas. Sistema de autorización listo.")
