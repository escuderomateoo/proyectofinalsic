from transformers import pipeline

# Carga el modelo solo una vez al inicio
print("Cargando el modelo de análisis de sentimiento en español...")
analizador_de_sentimiento = pipeline(
    "sentiment-analysis",
    model="finiteautomata/beto-sentiment-analysis"
)
print("Modelo cargado con éxito.")

def analizador_sentimiento(frase):
    resultados = analizador_de_sentimiento(frase)[0]
    sentimiento= resultados["label"]
    confianza =  resultados["score"]
    if sentimiento == "POS":
        emoji = "😊"  # positivo
    elif sentimiento == "NEG":
        emoji = "😞"  # negativo
    elif sentimiento == "NEU":
        emoji = "✋"  # neutral
    else:
        emoji = "❓"  # desconocido

    return f"Sentimiento: {sentimiento} {emoji}\nConfianza: {confianza:.2%}"
