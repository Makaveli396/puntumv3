# generador_trivia.py
import os
import random
import requests

# CORREGIDO: Obtener la clave API de una variable de entorno llamada 'TMDB_API_KEY'
TMDB_API_KEY = os.environ.get('TMDB_API_KEY')
API_BASE = 'https://api.themoviedb.org/3'

def obtener_pelicula_aleatoria():
    # Se añade un manejo de error básico y se verifica la API_KEY
    if not TMDB_API_KEY:
        raise ValueError("TMDB_API_KEY no está configurada como variable de entorno.")
    
    page = random.randint(1, 20)
    url = f"{API_BASE}/movie/popular?api_key={TMDB_API_KEY}&language=es-ES&page={page}"
    res = requests.get(url)
    res.raise_for_status() # Lanza una excepción para errores HTTP
    data = res.json()
    if not data['results']:
        raise ValueError("No se encontraron películas populares en la página.")
    return random.choice(data['results'])

def obtener_creditos(movie_id):
    if not TMDB_API_KEY:
        raise ValueError("TMDB_API_KEY no está configurada como variable de entorno.")
    
    url = f"{API_BASE}/movie/{movie_id}/credits?api_key={TMDB_API_KEY}&language=es-ES"
    res = requests.get(url)
    res.raise_for_status()
    return res.json()

def pregunta_anio(pelicula):
    return (
        f"¿En qué año se estrenó la película '{pelicula['title']}'?",
        pelicula['release_date'][:4]
    )

def pregunta_director(pelicula):
    creditos = obtener_creditos(pelicula['id'])
    director = next((c['name'] for c in creditos['crew'] if c['job'] == 'Director'), None)
    if director:
        return (
            f"¿Quién dirigió la película '{pelicula['title']}'?",
            director
        )
    return None

def pregunta_actor_principal(pelicula):
    creditos = obtener_creditos(pelicula['id'])
    if creditos['cast']:
        actor = creditos['cast'][0]['name']
        return (
            f"¿Quién es el actor o actriz principal de '{pelicula['title']}'?",
            actor
        )
    return None

def pregunta_genero(pelicula):
    # Nota: para obtener géneros, la película debe venir de una llamada con 'append_to_response=genres'
    # o de un endpoint que ya los incluya, como 'movie/{id}'. 'popular' no los incluye directamente.
    # Por ahora, esta función podría no funcionar si la película viene de 'popular'.
    # Si quieres que funcione, necesitarías hacer otra llamada a movie/{id} para obtener detalles completos.
    # O, puedes filtrar los géneros que ya conoces de la API de TMDB.
    generos = [g["name"] for g in pelicula.get("genres", [])]
    if generos:
        return (
            f"¿Cuál es uno de los géneros de la película '{pelicula['title']}'?",
            generos[0]
        )
    return None

def pregunta_sinopsis(pelicula):
    overview = pelicula.get('overview')
    titulo = pelicula['title']
    if overview:
        return (
            f"¿A qué película corresponde esta sinopsis?\n\n\"{overview[:200]}...\"",
            titulo
        )
    return None

def generar_pregunta():
    """
    Devuelve una tupla (pregunta, respuesta) eligiendo aleatoriamente el tipo de pregunta.
    """
    try:
        pelicula = obtener_pelicula_aleatoria()
    except Exception as e:
        # Manejo de errores si la API falla o no hay películas
        print(f"Error al obtener película aleatoria: {e}")
        return ("Lo siento, no pude generar una pregunta de película en este momento. Intenta más tarde.", "Error")

    funciones = [
        pregunta_anio,
        pregunta_director,
        pregunta_actor_principal,
        pregunta_sinopsis
        # Si quieres más tipos, agrégalos aquí
    ]
    random.shuffle(funciones)  # Trata de variar el tipo
    for funcion in funciones:
        try:
            resultado = funcion(pelicula)
            if resultado:  # Solo retorna preguntas válidas
                return resultado
        except Exception as e:
            # Si una función de pregunta falla (ej. no encuentra director)
            print(f"Error al generar pregunta con {funcion.__name__}: {e}")
            continue
            
    # Como fallback, si todas las funciones específicas fallan o no encuentran datos, pregunta el año
    # Asegúrate de que esta última opción siempre tenga datos válidos.
    return pregunta_anio(pelicula)
