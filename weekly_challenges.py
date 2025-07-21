import os
import random
import logging
from datetime import datetime, timedelta
from db import get_connection
from tmdbv3api import TMDb, Genre, Discover, Movie

logger = logging.getLogger(__name__)

# Configura TMDB
tmdb = TMDb()
tmdb.api_key = os.getenv('TMDB_API_KEY')
tmdb.language = 'es-ES'

# Tipos de retos posibles
CHALLENGE_TYPES = {
    "genre": {
        "name": "Género",
        "values": ["Acción", "Comedia", "Drama", "Sci-Fi", "Fantasía"]
    },
    "director": {
        "name": "Director",
        "values": ["Christopher Nolan", "Quentin Tarantino", "Steven Spielberg"]
    },
    "decade": {
        "name": "Década",
        "values": ["1980s", "1990s", "2000s", "2010s"]
    }
}

def generate_new_challenge():
    """Genera un reto semanal único"""
    conn = get_connection()
    cursor = conn.cursor()

    # Obtener retos anteriores para evitar repeticiones recientes
    cursor.execute("SELECT challenge_type, challenge_value FROM weekly_challenges")
    past_challenges = cursor.fetchall()

    available_types = list(CHALLENGE_TYPES.keys())
    random.shuffle(available_types)

    for challenge_type in available_types:
        available_values = CHALLENGE_TYPES[challenge_type]["values"]
        used_values = [c[1] for c in past_challenges if c[0] == challenge_type][-4:]
        unused_values = [v for v in available_values if v not in used_values]

        if unused_values:
            challenge_value = random.choice(unused_values)
            start_date = datetime.now().strftime("%Y-%m-%d")
            end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

            cursor.execute("""
                INSERT INTO weekly_challenges (challenge_type, challenge_value, start_date, end_date)
                VALUES (?, ?, ?, ?)
            """, (challenge_type, challenge_value, start_date, end_date))

            cursor.execute("UPDATE weekly_challenges SET is_active = 0 WHERE id != ?", (cursor.lastrowid,))
            conn.commit()
            conn.close()

            return {
                "id": cursor.lastrowid,
                "type": challenge_type,
                "value": challenge_value,
                "start": start_date,
                "end": end_date
            }

    conn.close()
    return None

def get_current_challenge():
    """Obtiene el reto activo actual"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM weekly_challenges WHERE is_active = 1 LIMIT 1")
    challenge = cursor.fetchone()
    conn.close()
    return challenge

def get_challenge_text() -> str:
    """Devuelve el reto actual como texto HTML listo para enviar por Telegram"""
    reto = get_current_challenge()

    if not reto:
        return "⚠️ No hay ningún reto activo en este momento."

    tipo = reto["challenge_type"]
    valor = reto["challenge_value"]
    inicio = reto["start_date"]
    fin = reto["end_date"]

    tipo_str = {
        "genre": "🎭 Género",
        "director": "🎬 Director",
        "decade": "📽️ Década"
    }.get(tipo, tipo)

    mensaje = f"""🏆 <b>Reto Semanal Cinéfilo</b>

📅 <b>Del:</b> {inicio} <b>al</b> {fin}
{tipo_str}: <b>{valor}</b>

Participa viendo y comentando películas que cumplan este reto.  
¡Usa hashtags válidos y gana puntos extra! 🍿
"""
    return mensaje

async def check_challenge_completion(user_id: int, movie_id: int) -> bool:
    """Verifica si una película cumple con el reto actual"""
    challenge = get_current_challenge()
    if not challenge:
        return False

    movie = Movie().details(movie_id)

    if challenge["challenge_type"] == "genre":
        genres = [g["name"] for g in movie.genres]
        return challenge["challenge_value"] in genres

    elif challenge["challenge_type"] == "director":
        credits = Movie().credits(movie_id)
        directors = [c["name"] for c in credits["crew"] if c["job"] == "Director"]
        return challenge["challenge_value"] in directors

    elif challenge["challenge_type"] == "decade":
        release_year = movie.release_date[:4]
        target_decade = challenge["challenge_value"][:4]
        return release_year[:3] == target_decade[:3]

    return False
