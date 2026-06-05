import logging
from groq import Groq
from typing import Optional
from config import GROQ_API_KEY
from apis.groq_api_texto import system_prompt

logger = logging.getLogger(__name__)

if not GROQ_API_KEY:
    raise ValueError("No se encuentra la API_KEY de Groq")

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
        logger.error("Error al transcribir audio: %s", e)
        return None
