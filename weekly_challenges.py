# weekly_challenges.py
import os
import random
from datetime import datetime, timedelta
import logging
from db import db_session  # Cambiar get_connection por db_session
from tmdbv3api import TMDb, Movie

logger = logging.getLogger(__name__)

# Configura TMDB (mantén esto igual)
tmdb = TMDb()
tmdb.api_key = os.getenv('TMDB_API_KEY')
tmdb.language = 'es-ES'

# [Mantén tus constantes CHALLENGE_TYPES]

def generate_new_challenge():
    """Genera un reto semanal único"""
    with db_session() as conn:  # Cambio aquí
        cursor = conn.cursor()
        
        # [Mantén el resto de la función igual]
        # Solo asegúrate de usar 'with db_session()' para todas las operaciones DB

def get_current_challenge():
    """Obtiene el reto activo actual"""
    with db_session() as conn:  # Cambio aquí
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM weekly_challenges WHERE is_active = 1 LIMIT 1"
        )
        return cursor.fetchone()

async def check_challenge_completion(user_id: int, movie_id: int):
    """Verifica si una película cumple con el reto actual"""
    challenge = get_current_challenge()
    if not challenge:
        return False
    
    # [Mantén el resto de la función igual]

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
