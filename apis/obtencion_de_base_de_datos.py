import json
import logging

logger = logging.getLogger(__name__)


def load_bank_data():
    try:
        with open("dataset.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("No se encontró el archivo dataset.json.")
    except json.JSONDecodeError:
        logger.error("Error al leer dataset.json: formato JSON incorrecto.")
    return None
