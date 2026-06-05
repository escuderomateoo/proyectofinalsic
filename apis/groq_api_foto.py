import logging
from groq import Groq
from config import GROQ_API_KEY
from apis.groq_api_texto import system_prompt

logger = logging.getLogger(__name__)

if not GROQ_API_KEY:
    raise ValueError("No se encuentra la API_KEY de Groq")

groq_client = Groq(api_key=GROQ_API_KEY)


def describir_imagen(file_url: str) -> str:
    try:
        response = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe en español lo que ves en esta imagen de forma detallada."},
                        {"type": "image_url", "image_url": {"url": file_url}},
                    ],
                },
            ],
        )
        descripcion = response.choices[0].message.content
        return descripcion.strip() if descripcion else "No pude generar una descripción."
    except Exception as e:
        logger.error("Error al describir imagen: %s", e)
        return f"⚠️ Error al describir la imagen: {e}"


def contexto_de_imagen(contexto_imagen, message, user_input, ultima_imagen_por_chat):
    palabras_clave = [
        "imagen", "foto", "en la imagen", "parece", "ves", "es eso",
        "quién es", "qué es", "está en la foto", "colores", "objeto", "animal",
    ]

    if contexto_imagen and any(p in user_input.lower() for p in palabras_clave):
        return (
            f"Esta es una descripción previa de una imagen enviada por el usuario:\n\"{contexto_imagen}\"\n\n"
            f"Luego el usuario escribió:\n\"{user_input}\"\n\n"
            f"Respondé en base a:\n"
            f"- Si el usuario pregunta algo relacionado con la imagen, respondé en base a la descripción y el texto.\n"
            f"- Si no pregunta sobre la imagen, respondé solo en base al texto.\n"
            f"- Si cambia de tema, no hagas mención a la imagen.\n"
            f"- Nunca digas que no podés procesar el mensaje."
        )
    else:
        ultima_imagen_por_chat.pop(message.chat.id, None)
        return None
