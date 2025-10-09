import os
from dotenv import load_dotenv
from groq import Groq
from typing import Optional
from apis.groq_api_texto import system_prompt

# Cargar variables del entorno
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("No se encuentra la API_KEY de Groq")

# Inicializar cliente Groq
groq_client = Groq(api_key=GROQ_API_KEY)


def transcribe_voice_with_groq(file_path: str) -> Optional[str]:
    try:
        with open(file_path, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(file_path, file),
                model="whisper-large-v3-turbo",
                prompt="Consulta sobre bancos y tarifas",
                response_format="json",
                language="es",
            )
        return transcription.text
    except Exception as e:
        print(f"Error al transcribir el audio: {str(e)}")
        return None
