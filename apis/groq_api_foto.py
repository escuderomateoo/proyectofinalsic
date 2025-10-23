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

def contexto_de_imagen(contexto_imagen,message,user_input,ultima_imagen_por_chat):
    def es_relacionado_a_imagen(texto: str) -> bool:
        palabras_clave = [
            "imagen", "foto", "en la imagen", "parece", "ves", "es eso", 
            "quién es", "qué es", "está en la foto", "colores", "objeto", "animal"
        ]
        texto_lower = texto.lower()
        return any(palabra in texto_lower for palabra in palabras_clave)

    # si el mensaje parece relacionado, agregamos el contexto
    if contexto_imagen and es_relacionado_a_imagen(user_input):
        user_input = f"""Esta es una descripción previa de una imagen enviada por el usuario:\n\"{contexto_imagen}\"\n\nLuego el usuario escribió:\n\"{user_input}\"\n\nResponde en base a
        -Si el usuario pregunta algo relacionado con la imagen, respondé en base a la descripción de la imagen y el texto del usuario.
        -Si el usuario no pregunta nada relacionado con la imagen, respondé solo en base al texto del usuario.
        -Si el usuario cambia de tema y no pregunta nada relacionado con la imagen, no hagas mención a la imagen en tu respuesta.
        -Nunca digas que no podes procesar el mensaje del usuario.
        """
        return user_input
    else:
        # limpia el contexto si ya no se está usando
        ultima_imagen_por_chat.pop(message.chat.id, None)
        return 