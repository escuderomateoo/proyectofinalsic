import os
import time
import telebot
import json
import re
from apis.filtrado_de_texto import filtrar_texto
from dotenv import load_dotenv
from typing import Optional
from apis.groq_api_texto import get_groq_response
from apis.sentimiento import analizador_sentimiento
from config import TELEGRAM_TOKEN
from apis.obtencion_de_base_de_datos import load_bank_data
from apis.groq_api_foto import describir_imagen
from apis.groq_api_foto import contexto_de_imagen
from apis.groq_api_audio import transcribe_voice_with_groq
from apis.groq_api_csv import guardar_comprobante_csv
from apis.groq_api_tarjeta import validar_luhn
from apis.groq_api_tarjeta import mensaje_validacion_luhn



from groq import Groq 

load_dotenv()

if not TELEGRAM_TOKEN:
    raise ValueError("No se encuentra el Token de Telegram")

ultima_imagen_por_chat = {}

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Traigo la base de datos
bank_data = load_bank_data()


@bot.message_handler(commands=["start"])
def welcome_message(message: telebot.types.Message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row_width = 2
    for preguntas in bank_data["faqs"]:
        markup.add(
            telebot.types.InlineKeyboardButton(
                preguntas["question"], callback_data=preguntas["question"]
            )
        )
    bot.reply_to(
        message,
        "💰 ¡Hola! Soy el bot informativo sobre bancos en Argentina.\n"
        "Podés consultarme tarifas, costos de mantenimiento o comparar entidades.",
    )
    bot.send_message(message.chat.id, "Preguntas frecuentes:", reply_markup=markup)


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
    
    ##comprobacion de tarjeta Luhn
    #Vuelvo el mensaje a texto plano
    user_message_raw = message.text

    #patron para buscar un numero que parezca de tarjeta (13 a 19 digitos)
    patron_tarjeta = re.search(r'([\d\s-]{11,23})', user_message_raw)

    #Devuelve si la tarjeta es o no real
    mensaje_validacion_luhn(patron_tarjeta,bot,message)

    ##Agregar Contexto para seguir describiendo la imagen    
    #Parte para que el contexto de la imagen se quede almacenado en el bot
    user_input = filtrar_texto(message.text)

    contexto_imagen = ultima_imagen_por_chat.get(message.chat.id)

    #funcion auxiliar para detectar si hay relación con la imagen
    contexto = contexto_de_imagen(contexto_imagen,message,user_input,ultima_imagen_por_chat)
    if contexto:
        user_input=contexto

    bot.send_chat_action(message.chat.id, "typing")
    response = get_groq_response(user_input, bank_data)

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
        #obtener la foto con mayor resolución
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}"

        bot.reply_to(message, "🧠 Analizando la imagen...")

        #llamar a la función que describe la imagen
        descripcion = describir_imagen(file_url)
        ultima_imagen_por_chat[message.chat.id] = descripcion

        #si detecta que es un comprobante o transferencia, hace la extracción directa
        if any(palabra in descripcion.lower() for palabra in ["comprobante", "transferencia", "pago"]):
            bot.reply_to(message, "📄 Es un comprobante. Extrayendo los datos...")

            prompt = (
                f"Extrae los datos del comprobante mostrado en la siguiente descripción de imagen.\n\n"
                f"{descripcion}\n\n"
                f"Devolvé la información SOLO en formato JSON puro con el siguiente formato exacto:\n\n"
                f"{{\n"
                f'  "Monto": "valor",\n'
                f'  "Fecha y hora": "valor",\n'
                f'  "Número de operación": "valor",\n'
                f'  "Nombre, CUIT/CUIL y CVU del remitente": "valor",\n'
                f'  "Nombre, CUIT/CUIL y CVU del destinatario": "valor"\n'
                f"}}\n\n"
                f"No incluyas explicaciones ni texto adicional, solo el JSON."
            )

            respuesta_groq = get_groq_response(prompt, bank_data)

            try:
                # intentar interpretar la respuesta como JSON
                comprobante_data = json.loads(respuesta_groq)

                # guardar los datos con pandas
                guardar_comprobante_csv(comprobante_data)

                # Enviar el resumen directamente
                resumen = (
                    "📄 *Resumen de la transferencia* 🤑\n"
                    f"*Monto:* {comprobante_data.get('Monto')}\n"
                    f"*Fecha y hora:* {comprobante_data.get('Fecha y hora')}\n"
                    f"*Número de operación:* {comprobante_data.get('Número de operación')}\n\n"
                    "*Información del remitente* 👉\n"
                    f"{comprobante_data.get('Nombre, CUIT/CUIL y CVU del remitente')}\n\n"
                    "*Información del destinatario* 💼\n"
                    f"{comprobante_data.get('Nombre, CUIT/CUIL y CVU del destinatario')}"
                )

                bot.send_message(message.chat.id, resumen, parse_mode="Markdown")

            except json.JSONDecodeError:
                bot.reply_to(message, "⚠️ No pude interpretar los datos del comprobante como JSON válido.")
                print("Respuesta Groq:", respuesta_groq)

        else:
            #si no es comprobante, solo describe la imagen normalmente
            bot.reply_to(message, f"🖼️ Descripción:\n\n{descripcion}")

    except Exception as e:
        bot.reply_to(message, f"❌ Error al procesar la imagen: {str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    call.text = call.data
    respuesta = get_groq_response(filtrar_texto(call.text), bank_data)
    bot.send_chat_action(call.message.chat.id, "typing")
    bot.send_message(call.message.chat.id, respuesta)

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
