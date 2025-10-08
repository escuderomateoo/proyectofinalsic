import telebot
import os
import json
from groq import Groq
from typing import Optional
import time
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

# Entorno de variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("No se encuentra el Token de Telegram")
if not GROQ_API_KEY:
    raise ValueError("No se encuentra su API_KEY de Groq")

# Instancias
bot = telebot.TeleBot(TELEGRAM_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)


def load_bank_data():
    try:
        with open("dataset.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: No se encontró el archivo dataset.json")
        return None
    except json.JSONDecodeError:
        print("Error al leer el archivo dataset.json. El formato JSON es incorrecto.")
        return None
    except Exception as e:
        print(f"Error desconocido al cargar el archivo dataset.json: {str(e)}")
        return None


bank_data = load_bank_data()


def get_groq_response(user_message: str) -> Optional[str]:
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


def transcribe_voice_with_groq(message: telebot.types.Message) -> Optional[str]:
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


@bot.message_handler(commands=["start"])
def welcome_message(message: telebot.types.Message):
    if not bank_data:
        bot.reply_to(message, "Error cargando datos de los bancos.")
        return

    welcome_message = (
        "💰 ¡Hola! Soy el bot informativo sobre bancos en Argentina.\n"
        "Podés consultarme tarifas, costos de mantenimiento o comparar entidades."
    )
    bot.reply_to(message, welcome_message)


@bot.message_handler(content_types=["text"])
def handle_text_message(message: telebot.types.Message):
    if not bank_data:
        bot.reply_to(
            message, "Error cargando los datos de los bancos. Intente más tarde."
        )
        return
    bot.send_chat_action(message.chat.id, "typing")
    response = get_groq_response(message.text)
    if response:
        bot.reply_to(message, response)
    else:
        bot.reply_to(
            message,
            "❌ Lo siento, hubo un error al procesar tu consulta.\n"
            "Podés escribirnos a info@codificardev.com.ar para más información.",
        )


@bot.message_handler(content_types=["voice"])
def handle_voice_message(message: telebot.types.Message):
    if not bank_data:
        bot.reply_to(message, "Error cargando datos de bancos. Intente más tarde.")
        return

    bot.send_chat_action(message.chat.id, "typing")
    transcription = transcribe_voice_with_groq(message)
    if not transcription:
        bot.reply_to(message, "❌ No pude transcribir el audio. Probá de nuevo.")
        return

    response = get_groq_response(transcription)
    if response:
        bot.reply_to(message, response)
    else:
        bot.reply_to(
            message,
            "❌ Ocurrió un error al procesar tu consulta.\n"
            "Podés escribirnos a info@codificardev.com.ar para más información.",
        )


if __name__ == "__main__":
    if bank_data:
        print("Bot bancario iniciado con Groq y Whisper...")
        while True:
            try:
                bot.polling(none_stop=True, interval=0, timeout=20)
            except Exception as e:
                print(f"Error en el bot: {str(e)}")
                print("Reiniciando...")
                time.sleep(5)
    else:
        print(
            "Error: No se pudo cargar el archivo dataset.json. El bot no se iniciará."
        )
