from openai import OpenAI
from config import OPEN_ROUTER_KEY
import requests
OPEN_ROUTER_API_URL = "https://openrouter.ai/api/v1"
client = OpenAI(api_key=OPEN_ROUTER_KEY, base_url=OPEN_ROUTER_API_URL)

def respuesta_seek(mensaje):
    completion = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "<YOUR_SITE_URL>",  # Opcional
            "X-Title": "<YOUR_SITE_NAME>",      # Opcional
        },
        extra_body={},
        model="deepseek/deepseek-chat-v3.1:free",
        messages=[
            {
                "role": "user",
                "content": mensaje
            }
        ]
    )
    return completion.choices[0].message.content
