import json


def cargar_dataset():
    try:
        with open("dataset.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error al cargar dataset: {e}")
        return {}


def buscar_en_dataset(texto, dataset):
    for banco in dataset.get("bancos", []):
        if banco["nombre"].lower() in texto.lower():
            return (
                f"🏦 Banco: {banco['nombre']}\n"
                f"📍 Provincia: {banco['provincia']}\n"
                f"💸 Costo mensual: {banco['costo_mensual']}\n"
                f"📝 Notas: {banco['notas']}"
            )
    return None
