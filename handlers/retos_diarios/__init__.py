from datetime import datetime

def get_today_challenge():
    # Reto diario por día de la semana
    weekday = datetime.now().weekday()

    retos = [
        {"keywords": ["terror", "miedo"], "bonus_points": 5},
        {"hashtag": "#recomendación", "bonus_points": 4, "min_words": 30},
        {"keywords": ["Oscar", "ganadora"], "bonus_points": 6},
        {"hashtag": "#reseña", "bonus_points": 7, "min_words": 50},
        {"keywords": ["animación", "dibujos"], "bonus_points": 5},
        {"keywords": ["blanco y negro"], "bonus_points": 5},
        {"hashtag": "#debate", "bonus_points": 6, "min_words": 20}
    ]

    return retos[weekday % len(retos)]