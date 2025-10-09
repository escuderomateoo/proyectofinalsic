import os
from dotenv import load_dotenv

# Cargar variables del archivo .env en el entorno
load_dotenv()

# Claves/API Tokens
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
OPEN_ROUTER_KEY = os.getenv('OPEN_ROUTER_KEY')

# Rutas de archivos locales
DATASET_PATH = 'dataset.json'
