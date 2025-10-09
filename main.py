import os
import time
import telebot
from apis.filtrado_de_texto import filtrar_texto
from dotenv import load_dotenv
from typing import Optional
from apis.groq_api import get_groq_response, transcribe_voice_with_groq
from apis.sentimiento import analizador_sentimiento
from apis.config import TELEGRAM_TOKEN
from apis.obtencion_de_base_de_datos import load_bank_data
from apis.foto import describir_imagen

load_dotenv()

if not TELEGRAM_TOKEN:
    raise ValueError("No se encuentra el Token de Telegram")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

#Traigo la base de datos
bank_data = load_bank_data()

@bot.message_handler(commands=["start"])
def welcome_message(message: telebot.types.Message):

    bot.reply_to(
        message,
        "💰 ¡Hola! Soy el bot informativo sobre bancos en Argentina.\n"
        "Podés consultarme tarifas, costos de mantenimiento o comparar entidades.",
    )

@bot.message_handler(commands=["sentimiento"])
def cmd_sentimiento(message):
    texto = message.text
    if len(texto.split(" ", 1)) < 2:
        bot.reply_to(message, 'Usa: /sentimiento "tu frase"')
        return
    frase = texto.split(" ", 1)[1].strip('"')
    resultado = analizador_sentimiento(frase)
    bot.reply_to(message, resultado)

@bot.message_handler(content_types=["text"])
def handle_text_message(message: telebot.types.Message):
    if not bank_data:
        bot.reply_to(
            message, "Error cargando los datos de los bancos. Intente más tarde."
        )
        return

    bot.send_chat_action(message.chat.id, "typing")
    response = get_groq_response(filtrar_texto(message.text), bank_data)

    if response:
        bot.reply_to(message, response)
    else:
        bot.reply_to(
            message,
            "Lo siento, hubo un error al procesar tu consulta.\n"
            "Podés escribirnos a info@agushermoso.com.ar para más información.",
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

    transcription = filtrar_texto(transcribe_voice_with_groq(temp_file))
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


@bot.message_handler(content_types=["photo"])
def handle_foto(message):
    try:
        #obtener foto con la mayor resolucion
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}"
        
        bot.reply_to(message, "Analizando la imagen, en segundos te envio la descripción!")

        #llamo a la funcion que describe la imagen
        descripcion = describir_imagen(file_url)
        bot.reply_to(message, f"Descripción:\n\n{descripcion}")
    
    except Exception as e:
        bot.reply_to(message, f"Error al procesar la imagen: {str(e)}")

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
