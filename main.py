import os
import json
import time
import telebot
from dotenv import load_dotenv
from typing import Optional
from apis.groq_api import get_groq_response, transcribe_voice_with_groq

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError("No se encuentra el Token de Telegram")

bot = telebot.TeleBot(TELEGRAM_TOKEN)


def load_bank_data():
    try:
        with open("dataset.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: No se encontró el archivo dataset.json")
    except json.JSONDecodeError:
        print("Error al leer dataset.json. Formato JSON incorrecto.")
    return None


bank_data = load_bank_data()


@bot.message_handler(commands=["start"])
def welcome_message(message: telebot.types.Message):
    if not bank_data:
        bot.reply_to(message, "Error cargando datos de los bancos.")
        return

    bot.reply_to(
        message,
        "💰 ¡Hola! Soy el bot informativo sobre bancos en Argentina.\n"
        "Podés consultarme tarifas, costos de mantenimiento o comparar entidades.",
    )


@bot.message_handler(content_types=["text"])
def handle_text_message(message: telebot.types.Message):
    if not bank_data:
        bot.reply_to(
            message, "Error cargando los datos de los bancos. Intente más tarde."
        )
        return

    bot.send_chat_action(message.chat.id, "typing")
    response = get_groq_response(message.text, bank_data)

    if response:
        bot.reply_to(message, response)
    else:
        bot.reply_to(
            message,
            "Lo siento, hubo un error al procesar tu consulta.\n"
            "Podés escribirnos a info@codificardev.com.ar para más información.",
        )


@bot.message_handler(content_types=["voice"])
def handle_voice_message(message: telebot.types.Message):
    if not bank_data:
        bot.reply_to(message, "Error cargando datos de bancos. Intente más tarde.")
        return

    bot.send_chat_action(message.chat.id, "typing")

    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    temp_file = "temp_voice.ogg"

    with open(temp_file, "wb") as f:
        f.write(downloaded_file)

    transcription = transcribe_voice_with_groq(temp_file)
    os.remove(temp_file)

    if not transcription:
        bot.reply_to(message, "No pude transcribir el audio. Probá de nuevo.")
        return

    response = get_groq_response(transcription, bank_data)

    if response:
        bot.reply_to(message, response)
    else:
        bot.reply_to(
            message,
            "Ocurrió un error al procesar tu consulta.\n"
            "Podés escribirnos a info@agushermosodev.com.ar para más información.",
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
