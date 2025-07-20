# handlers/achievements.py
import datetime
from db import add_achievement, get_user_stats

# Lista de logros predefinidos
ACHIEVEMENTS = [
    {
        "id": 1,
        "name": "🥇 Primer aporte",
        "description": "Tu primer mensaje con #aporte",
        "trigger": lambda stats: stats.get("hashtag_counts", {}).get("#aporte", 0) >= 1
    },
    {
        "id": 2,
        "name": "✍️ Crítico en camino",
        "description": "Has publicado 3 críticas",
        "trigger": lambda stats: stats.get("hashtag_counts", {}).get("#crítica", 0) >= 3
    },
    {
        "id": 3,
        "name": "📚 Cinéfilo activo",
        "description": "Participaste 5 días diferentes",
        "trigger": lambda stats: len(stats.get("active_days", set())) >= 5
    },
    {
        "id": 4,
        "name": "🔥 Retador constante",
        "description": "Completaste 3 retos diarios en una semana",
        "trigger": lambda stats: stats.get("daily_challenges_week", 0) >= 3
    },
    {
        "id": 5,
        "name": "🏆 Desafío maestro",
        "description": "Completaste el reto semanal y 3 diarios en una semana",
        "trigger": lambda stats: stats.get("weekly_challenge_done", False) and stats.get("daily_challenges_week", 0) >= 3
    }
]

def check_achievements(user_id: int, username: str, context, chat_id: int):
    """Verifica si un usuario ha desbloqueado nuevos logros"""
    stats = get_user_stats(user_id)
    nuevos_logros = []

    for logro in ACHIEVEMENTS:
        if logro["id"] not in stats.get("achievements", []):
            if logro["trigger"](stats):
                nuevos_logros.append(logro)
                add_achievement(user_id, logro["id"])

    for logro in nuevos_logros:
        context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🎉 *¡Nuevo logro desbloqueado!*\n\n"
                f"{logro['name']}\n{logro['description']}"
            ),
            parse_mode="Markdown"
        )
