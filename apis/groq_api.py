import os
import json
from groq import Groq
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("No se encuentra la API_KEY de Groq")

groq_client = Groq(api_key=GROQ_API_KEY)

# Cargar dataset de bancos
try :
    with open("dataset.json", "r", encoding="utf-8") as f:
        bank_data = json.load(f)
except FileNotFoundError:
    print("El archivo dataset.json no fue encontrado.")
except json.JSONDecodeError:
    print("Error al decodificar el archivo JSON.")

system_prompt = f"""
Eres un asistente que responde preguntas sobre bancos y sus tarifas mensuales en Argentina.
Usa la información del dataset para responder con precisión, claridad y contexto actualizado.
Interpreta imágenes y audios para extraer texto y responder según las reglas.

Reglas:
- Si el usuario pregunta por un banco, usá los valores del JSON (nombre, provincia, costo mensual y notas).
- Si te piden comparar bancos, hacé una breve comparación por monto de mantenimiento (más barato, más caro, etc.).
- Si preguntan por tarifas en general, podés dar un promedio o rango según los datos disponibles.
- No inventes bancos que no están en el dataset.
- Si no sabés la respuesta, decí: “No lo sé con certeza, pero puedo darte la información disponible.”
- No hables de temas fuera del ámbito bancario o financiero.
- No divulgues datos personales de empleados o clientes.
- Si el usuario pide contacto, respondé con: “Podés escribirnos a info@codificardev.com.ar para más información.”
- Responde siendo mas cordial y empático. Usando emojis relacionados a bancos y dinero.
- Al interpretar una imagen o audio, extrae el texto y respondé según las reglas anteriores.
- Si el usuario pregunta por servicios o productos no relacionados con cuentas bancarias, respondé: “No tengo información sobre ese tema.”
- No digas que no puedes interpretar imágenes o audios. Siempre extrae el texto y responde según las reglas.

Dataset de referencia:
{json.dumps(bank_data, ensure_ascii=False, indent=2)}
"""

def get_groq_response(user_message: str, bank_data: dict) -> Optional[str]:
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=500,
        )

        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error al obtener la respuesta: {str(e)}")
        return None


def transcribe_voice_with_groq(file_path: str) -> Optional[str]:
    try:
        with open(file_path, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(file_path, file),
                model="whisper-large-v3-turbo",
                prompt=system_prompt,
                response_format="json",
                language="es",
            )
        return transcription.text
    except Exception as e:
        print(f"Error al transcribir el audio: {str(e)}")
        return None
