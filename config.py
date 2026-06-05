import os
import sys
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPEN_ROUTER_KEY = os.getenv("OPEN_ROUTER_KEY")

DATASET_PATH = "dataset.json"


def validate_env() -> None:
    missing = [
        name for name, val in [
            ("TELEGRAM_TOKEN", TELEGRAM_TOKEN),
            ("GROQ_API_KEY", GROQ_API_KEY),
        ]
        if not val
    ]
    if missing:
        sys.exit(f"[ERROR] Variables de entorno faltantes: {', '.join(missing)}. Revisá el archivo .env")
