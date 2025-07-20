from db import get_top10
from telegram import Update
import datetime
import random

# Frases cinematográficas para el ranking
RANKING_PHRASES = [
    "🥇 {winner} se lleva la Palma de Oro esta semana",
    "🎬 {winner} protagoniza este ranking como si fuera Marlon Brando",
    "🏆 {winner} domina la cartelera con {points} puntos",
    "⭐ {winner} brilla más que las luces de Hollywood",
    "🎭 {winner} actúa como si fuera el último día en Cannes"
]

CLOSING_PHRASES = [
    "📽️ ¡Que el show continúe la próxima semana!",
    "🎞️ El séptimo arte nunca descansa...",
    "🎪 ¡Lights, camera, action para una nueva semana!",
    "🎨 El cine es pasión, y ustedes lo demuestran cada día",
    "🎯 Próximo capítulo: domingo que viene, misma hora"
]

async def cmd_ranking(update: Update, context):
    """Comando manual para mostrar ranking actual"""
    print(f"[DEBUG] Comando /ranking ejecutado por {update.effective_user.first_name}")
    print(f"[DEBUG] Chat ID: {update.effective_chat.id}")
    
    try:
        # Debug de la función get_top10
        print("[DEBUG] Llamando a get_top10()...")
        top = get_top10()
        print(f"[DEBUG] Resultado de get_top10(): {top}")
        print(f"[DEBUG] Tipo de dato: {type(top)}")
        print(f"[DEBUG] Longitud: {len(top) if top else 'None'}")
        
        if not top:
            print("[DEBUG] No hay datos - enviando mensaje de no participantes")
            await update.message.reply_text("📝 Aún no hay participantes. ¡Sé el primero en usar hashtags!")
            return
        
        print("[DEBUG] Construyendo mensaje del ranking...")
        msg = "🎬 *TOP 10 CINÉFILOS ACTUALES*\n\n"
        
        # Iterar sobre los datos correctamente
        for i, (username, points, level) in enumerate(top, 1):
            print(f"[DEBUG] Procesando posición {i}: {username} - {points} pts - nivel {level}")
            
            # Emojis según posición
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = "🎭"
            
            # Agregar línea al mensaje
            msg += f"{emoji} {i}. {username} - {points} pts\n"
        
        msg += f"\n📅 Próximo ranking oficial: {get_next_sunday()}"
        
        print(f"[DEBUG] Mensaje construido: {msg[:200]}...")  # Solo primeros 200 chars
        print("[DEBUG] Enviando mensaje...")
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        print("[DEBUG] Mensaje enviado exitosamente")
        
    except Exception as e:
        print(f"[ERROR] Error en cmd_ranking: {e}")
        print(f"[ERROR] Tipo de error: {type(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        
        # Enviar mensaje de error al usuario
        await update.message.reply_text(
            f"❌ Error al obtener el ranking: {str(e)}\n"
            "Contacta al administrador si persiste el problema."
        )

async def ranking_job(context):
    """Job que se ejecuta automáticamente cada domingo a las 20:00"""
    try:
        print("[INFO] Ejecutando ranking_job semanal")
        
        # Obtener chat_id desde job_data
        chat_id = context.job.data if hasattr(context.job, 'data') and context.job.data else None
        
        if not chat_id:
            print("[ERROR] No hay chat_id configurado para ranking automático")
            return
        
        top = get_top10()
        if not top:
            await context.bot.send_message(
                chat_id=chat_id,
                text="📝 Esta semana no hubo participación. ¡Anímense con los hashtags!"
            )
            return
        
        # Crear mensaje épico del ranking
        winner_data = top[0]  # Primer lugar
        winner = winner_data[0]  # username
        winner_points = winner_data[1]  # points
        
        # Frase aleatoria para el ganador
        winner_phrase = random.choice(RANKING_PHRASES).format(
            winner=winner, 
            points=winner_points
        )
        
        msg = f"🎬 *RANKING SEMANAL OFICIAL*\n"
        msg += f"📅 Semana del {get_last_week_range()}\n\n"
        msg += f"{winner_phrase}\n\n"
        msg += "🏆 *TOP 10 DE LA SEMANA:*\n\n"
        
        for i, (username, points, level) in enumerate(top, 1):
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = "🎭"
            
            msg += f"{emoji} {i}. {username} - {points} pts\n"
        
        msg += f"\n{random.choice(CLOSING_PHRASES)}"
        
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
        print(f"[INFO] Ranking semanal enviado a chat {chat_id}")
        
        # Opcional: Reset de puntos semanales (descomentar si quieres ranking semanal real)
        # reset_weekly_points()
        
    except Exception as e:
        print(f"[ERROR] en ranking_job: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")

def get_next_sunday():
    """Obtiene la fecha del próximo domingo"""
    today = datetime.date.today()
    days_ahead = 6 - today.weekday()  # Domingo es 6
    if days_ahead <= 0:  # Si hoy es domingo
        days_ahead += 7
    next_sunday = today + datetime.timedelta(days_ahead)
    return next_sunday.strftime("%d/%m/%Y")

def get_last_week_range():
    """Obtiene el rango de la semana pasada"""
    today = datetime.date.today()
    last_sunday = today - datetime.timedelta(days=today.weekday() + 1)
    last_saturday = last_sunday + datetime.timedelta(days=6)
    return f"{last_sunday.strftime('%d/%m')} - {last_saturday.strftime('%d/%m')}"

def reset_weekly_points():
    """Reinicia puntos semanales (opcional - usar solo si quieres ranking semanal real)"""
    from db import get_connection
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET points = 0")
        conn.commit()
        conn.close()
        print("[INFO] Puntos semanales reiniciados")
    except Exception as e:
        print(f"[ERROR] al reiniciar puntos: {e}")
