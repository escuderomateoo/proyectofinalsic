import os
from dotenv import load_dotenv
from groq import Groq
from apis.groq_api_texto import system_prompt

# Cargar variables del entorno
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("No se encuentra la API_KEY de Groq")

# Inicializar cliente Groq
groq_client = Groq(api_key=GROQ_API_KEY)


def describir_imagen(file_url: str) -> str:
    """
    Envía una imagen al modelo de visión de Groq y devuelve una descripción en español.
    """
    try:

        response = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe en español lo que ves en esta imagen de forma detallada.",
                        },
                        {"type": "image_url", "image_url": {"url": file_url}},
                    ],
                },
            ],
        )

        descripcion = response.choices[0].message.content
        return (
            descripcion.strip() if descripcion else "No pude generar una descripción."
        )
    except Exception as e:
        return f"⚠️ Error al describir la imagen: {e}"
