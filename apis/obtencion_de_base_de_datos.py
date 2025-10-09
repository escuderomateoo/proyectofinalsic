import json


def load_bank_data():
    try:
        with open("dataset.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: No se encontró el archivo dataset.json")
    except json.JSONDecodeError:
        print("Error al leer dataset.json. Formato JSON incorrecto.")
    return None
