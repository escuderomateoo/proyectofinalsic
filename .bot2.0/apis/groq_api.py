import requests
from config import GROQ_API_KEY

GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'

def respuesta_groq(mensaje):
    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'

    }
    data = {
        'model': 'openai/gpt-oss-20b',
        'messages': [{'role': 'user', 'content': mensaje}]
    }
    try:
        resp= requests.post(GROQ_API_URL, headers=headers, json=data,timeout=20)
        if resp.status_code == 200:
            print("Conexion con groq exitosa")
            return resp.json()['choices'][0]['message']['content'].strip()
        else:
            return f"[Error de Groq] {resp.status_code}"
    except Exception as e:
        return f"[Error de conexion a Groq: {e}]"
        