# utils.py
import os
import logging
import requests
import json
from dotenv import load_dotenv # ¡Asegúrate de tener instalada la librería python-dotenv! (pip install python-dotenv)

logger = logging.getLogger(__name__)

# --- FUNCIÓN: load_env ---
def load_env():
    """Carga las variables de entorno desde el archivo .env."""
    # Esto busca el .env en la raíz del proyecto, fuera de donde se ejecuta el script en Render
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        logger.info("Variables de entorno cargadas desde .env")
    else:
        logger.warning("Archivo .env no encontrado. Asegúrate de configurar las variables de entorno directamente en Render.")

# --- OTRAS FUNCIONES (Ejemplos, asegúrate de que tus implementaciones sean correctas) ---

async def get_random_meme_url() -> str:
    """Obtiene una URL de meme aleatorio."""
    try:
        response = requests.get("https://meme-api.com/gimme")
        response.raise_for_status() # Lanza excepción para errores HTTP
        data = response.json()
        return data.get("url", "No se pudo obtener un meme en este momento.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al obtener meme: {e}")
        return "Lo siento, no pude obtener un meme ahora."

async def get_crypto_price(symbol: str) -> str:
    """Obtiene el precio de una criptomoneda."""
    try:
        # Ejemplo con CoinGecko API (puede requerir clave o cambiar URL)
        # La API gratuita de CoinGecko puede tener límites de tasa.
        response = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={symbol.lower()}&vs_currencies=usd")
        response.raise_for_status()
        data = response.json()
        if data and symbol.lower() in data and 'usd' in data[symbol.lower()]:
            price = data[symbol.lower()]['usd']
            return f"El precio actual de {symbol.upper()} es: ${price:,.2f} USD"
        return f"No se pudo encontrar el precio para {symbol.upper()}."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al obtener precio de criptomoneda {symbol}: {e}")
        return "Lo siento, no pude obtener el precio de la criptomoneda en este momento."

async def fetch_weather(city: str) -> str:
    """Obtiene el clima de una ciudad. Requiere una API Key de OpenWeatherMap."""
    OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY')
    if not OPENWEATHER_API_KEY:
        return "Error: La API Key de OpenWeatherMap no está configurada en las variables de entorno."
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=es"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if data.get('cod') == 200:
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            description = data['weather'][0]['description']
            city_name = data['name']
            country = data['sys']['country']
            return (f"Clima en {city_name}, {country}: {description.capitalize()}. "
                    f"Temperatura: {temp}°C (sensación térmica: {feels_like}°C).")
        else:
            return f"No se encontró el clima para {city}. Código de error: {data.get('cod', 'N/A')}."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al obtener clima para {city}: {e}")
        return "Lo siento, no pude obtener el clima en este momento."

async def get_exchange_rate(from_currency: str, to_currency: str) -> str:
    """Obtiene la tasa de cambio entre dos monedas."""
    # Ejemplo con API de ExchangeRate-API (requiere clave gratuita)
    # REGISTRATE EN https://www.exchangerate-api.com/ para obtener tu KEY
    EXCHANGE_RATE_API_KEY = os.environ.get('EXCHANGE_RATE_API_KEY')
    if not EXCHANGE_RATE_API_KEY:
        return "Error: La API Key de ExchangeRate-API no está configurada en las variables de entorno."
        
    try:
        url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_RATE_API_KEY}/latest/{from_currency.upper()}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if data.get('result') == 'success' and to_currency.upper() in data.get('conversion_rates', {}):
            rate = data['conversion_rates'][to_currency.upper()]
            return f"1 {from_currency.upper()} = {rate:.4f} {to_currency.upper()}"
        else:
            return f"No se pudo obtener la tasa de cambio entre {from_currency.upper()} y {to_currency.upper()}."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al obtener tasa de cambio para {from_currency}/{to_currency}: {e}")
        return "Lo siento, no pude obtener la tasa de cambio en este momento."

async def get_youtube_video_info(url: str) -> str:
    """Obtiene información básica de un video de YouTube."""
    # Requiere la librería 'yt-dlp' instalada (pip install yt-dlp)
    # y que youtube-dl esté disponible en el PATH (puede ser complejo en Render)
    # CONSIDERACIÓN: Para despliegues simples, es mejor usar una API dedicada o web scrapping con un servicio externo.
    # El uso directo de yt-dlp en Render puede requerir configuración adicional.
    # Alternativa: Usar la API de YouTube Data v3 (requiere API Key de Google)
    try:
        from yt_dlp import YoutubeDL
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'extract_flat': True,
            'force_generic_extractor': True,
            'dump_single_json': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'N/A')
            uploader = info.get('uploader', 'N/A')
            duration = info.get('duration_string', 'N/A')
            views = info.get('view_count', 'N/A')
            
            views_str = f"{views:,}" if isinstance(views, int) else views
            
            return (f"🎥 **Info de YouTube:**\n"
                    f"Título: {title}\n"
                    f"Autor: {uploader}\n"
                    f"Duración: {duration}\n"
                    f"Vistas: {views_str}")
    except ImportError:
        return "Error: La librería 'yt-dlp' no está instalada o no se puede importar."
    except Exception as e:
        logger.error(f"Error al obtener info de YouTube para {url}: {e}")
        return "Lo siento, no pude obtener información del video de YouTube."

async def get_joke() -> str:
    """Obtiene un chiste aleatorio."""
    try:
        # Ejemplo con JokeAPI o Chuck Norris API
        response = requests.get("https://v2.jokeapi.dev/joke/Any?blacklistFlags=racist,sexist,explicit&type=single")
        response.raise_for_status()
        data = response.json()
        if data.get('type') == 'single':
            return data.get('joke', 'No pude encontrar un chiste.')
        return "No pude encontrar un chiste de tipo 'single'."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al obtener chiste: {e}")
        return "Lo siento, no pude obtener un chiste en este momento."

async def get_random_fact() -> str:
    """Obtiene un dato curioso aleatorio."""
    try:
        # Ejemplo con API de Random Fact (puede no ser estable o requerir clave)
        # O usar una API como numbersapi.com
        response = requests.get("https://uselessfacts.jsph.pl/random.json?language=en") # Puedes buscar una en español
        response.raise_for_status()
        data = response.json()
        return data.get('text', 'No pude obtener un dato curioso.')
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al obtener dato curioso: {e}")
        return "Lo siento, no pude obtener un dato curioso en este momento."
