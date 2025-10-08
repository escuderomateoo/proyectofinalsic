import json
import os
from typing import Optional
from groq import Groq
import telebot


def get_groq_response(
    user_message: str, bank_data: dict, groq_client: Groq
) -> Optional[str]:
    try:
        system_prompt = f"""
Eres un asistente que responde preguntas sobre bancos y sus tarifas mensuales en Argentina.
Usa la información del dataset para responder con precisión, claridad y contexto actualizado.

Reglas:
- Si el usuario pregunta por un banco, usá los valores del JSON (nombre, provincia, costo mensual y notas).
- Si el valor aparece como "Desconocido", respondé que el banco no publica un valor único y depende del tipo de cuenta o paquete.
- Si te piden comparar bancos, hacé una breve comparación por monto de mantenimiento (más barato, más caro, etc.).
- Si preguntan por tarifas en general, podés dar un promedio o rango según los datos disponibles.
- No inventes bancos que no están en el dataset.
- Si no sabés la respuesta, decí: “No lo sé con certeza, pero puedo darte la información disponible.”
- No hables de temas fuera del ámbito bancario o financiero.
- Si detectás insultos o spam, respondé: “Nuestro bot no puede procesar ese mensaje.”
- Horario de atención: 9 a 18 hs. Si el mensaje llega fuera de ese horario, respondé: “Estamos fuera de horario. Te responderemos pronto.”
- No divulgues datos personales de empleados o clientes.
- Si el usuario pide contacto, respondé con: “Podés escribirnos a info@codificardev.com.ar para más información.”

Dataset de referencia:
{json.dumps(bank_data, ensure_ascii=False, indent=2)}
"""
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


def transcribe_voice_with_groq(
    bot: telebot.TeleBot, message: telebot.types.Message, groq_client: Groq
) -> Optional[str]:
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        temp_file = "temp_voice.ogg"

        with open(temp_file, "wb") as f:
            f.write(downloaded_file)

        with open(temp_file, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(temp_file, file),
                model="whisper-large-v3-turbo",
                prompt="Consulta sobre bancos y tarifas",
                response_format="json",
                language="es",
            )

        os.remove(temp_file)
        return transcription.text

    except Exception as e:
        print(f"Error al transcribir el audio: {str(e)}")
        return None
