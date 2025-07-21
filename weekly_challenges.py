import random
from datetime import datetime, timedelta
from db import get_connection
import logging
from tmdbv3api import TMDb, Genre, Discover

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
    
    # 1. Obtener retos anteriores para evitar repeticiones
    cursor.execute("SELECT challenge_type, challenge_value FROM weekly_challenges")
    past_challenges = cursor.fetchall()
    
    # 2. Seleccionar tipo de reto no repetido recientemente
    available_types = list(CHALLENGE_TYPES.keys())
    random.shuffle(available_types)
    
    for challenge_type in available_types:
        available_values = CHALLENGE_TYPES[challenge_type]["values"]
        
        # Filtrar valores ya usados (últimas 4 semanas)
        used_values = [c[1] for c in past_challenges if c[0] == challenge_type][-4:]
        unused_values = [v for v in available_values if v not in used_values]
        
        if unused_values:
            challenge_value = random.choice(unused_values)
            
            # 3. Guardar nuevo reto
            start_date = datetime.now().strftime("%Y-%m-%d")
            end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            
            cursor.execute(
                """INSERT INTO weekly_challenges 
                (challenge_type, challenge_value, start_date, end_date)
                VALUES (?, ?, ?, ?)""",
                (challenge_type, challenge_value, start_date, end_date)
            )
            
            # Desactivar retos anteriores
            cursor.execute(
                "UPDATE weekly_challenges SET is_active = 0 WHERE id != ?",
                (cursor.lastrowid,)
            )
            
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
    cursor.execute(
        "SELECT * FROM weekly_challenges WHERE is_active = 1 LIMIT 1"
    )
    challenge = cursor.fetchone()
    conn.close()
    return challenge

async def check_challenge_completion(user_id: int, movie_id: int):
    """Verifica si una película cumple con el reto actual"""
    challenge = get_current_challenge()
    if not challenge:
        return False
    
    # Obtener detalles de la película desde TMDB
    movie = Movie().details(movie_id)
    
    # Verificar según tipo de reto
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