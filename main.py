import os
import time
import telebot
import json
import re
from dotenv import load_dotenv
from typing import Optional

# IMPORTACIONES DE APIS
from apis.filtrado_de_texto import filtrar_texto
from apis.groq_api_texto import get_groq_response
from apis.sentimiento import analizador_sentimiento
from apis.obtencion_de_base_de_datos import load_bank_data
from apis.groq_api_foto import describir_imagen, contexto_de_imagen
from apis.groq_api_audio import transcribe_voice_with_groq
from apis.groq_api_csv import guardar_comprobante_csv
from apis.groq_api_tarjeta import validar_luhn, mensaje_validacion_luhn
from apis.carpetas import cargar_carpetas, guardar_carpetas, crear_carpeta, ver_gasto, depositar, quitar
from config import TELEGRAM_TOKEN



load_dotenv()

if not TELEGRAM_TOKEN:
    raise ValueError("No se encuentra el Token de Telegram")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
ultima_imagen_por_chat = {}

# CARGA BASE DE DATOS DE BANCOS
bank_data = load_bank_data()


# COMANDOS DEL BOT


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


@bot.message_handler(commands=["crear"])
def cmd_crear_carpeta(message):
    partes = message.text.split()
    if len(partes) < 3:
        bot.reply_to(message, "Uso: /crear nombre dinero_inicial")
        return

    nombre = partes[1]
    try:
        dinero = float(partes[2])
    except ValueError:
        bot.reply_to(message, "⚠️ El dinero inicial debe ser un número.")
        return

    resultado = crear_carpeta(nombre, dinero)
    bot.reply_to(message, resultado)


@bot.message_handler(commands=["gasto"])
def cmd_ver_gasto(message):
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "Uso: /gasto nombre")
        return

    nombre = partes[1]
    resultado = ver_gasto(nombre)
    bot.reply_to(message, resultado)


@bot.message_handler(commands=["resumen", "resumen_gastos"])
def cmd_resumen(message):
    """Devuelve un resumen de todas las carpetas y el total de dinero."""
    carpetas = cargar_carpetas()
    if not carpetas:
        bot.reply_to(message, "No hay carpetas registradas.")
        return

    lineas = []
    total = 0.0
    # Ordenamos por dinero descendente para mostrar primero las carpetas con mayor monto
    try:
        items = sorted(carpetas.items(), key=lambda x: float(x[1].get("dinero", 0)), reverse=True)
    except Exception:
        items = carpetas.items()

    for nombre, datos in items:
        dinero = float(datos.get("dinero", 0)) if isinstance(datos, dict) else 0.0
        lineas.append(f"- {nombre}: ${dinero:.2f}")
        total += dinero

    lineas.append(f"\nTotal: ${total:.2f}")
    mensaje = "Resumen de carpetas:\n" + "\n".join(lineas)
    bot.reply_to(message, mensaje)


@bot.message_handler(commands=["depositar"])
def cmd_depositar(message):
    partes = message.text.split()
    # El comando espera: /depositar destino monto 
    if len(partes) < 3:
        bot.reply_to(message, "Uso: /depositar destino monto")
        return

    destino = partes[1]
    try:
        monto = float(partes[2])
    except ValueError:
        bot.reply_to(message, "⚠️ El monto debe ser un número.")
        return

    # Delegamos la lógica al módulo de carpetas
    resultado = depositar(destino, monto)
    bot.reply_to(message, resultado)

@bot.message_handler(commands=["quitar"])
def cmd_quitar(message):
    partes = message.text.split()
    # El comando espera: /quitar destino monto
    if len(partes) < 3:
        bot.reply_to(message, "Uso: /quitar destino monto")
        return
    destino = partes[1]
    try:
        monto = float(partes[2])
    except ValueError:
        bot.reply_to(message, "⚠️ El monto debe ser un número.")
        return
    
    # Delegamos la lógica al módulo de carpetas
    resultado = quitar(destino, monto)
    bot.reply_to(message, resultado)


# MENSAJES DE TEXTO (PASA A GROQ SI NO ES UN COMANDO)


@bot.message_handler(content_types=["text"])
def handle_text_message(message: telebot.types.Message):
    if not bank_data:
        bot.reply_to(
            message, "Error cargando los datos de los bancos. Intente más tarde."
        )
        return

    # Si es un comando tipo "/algo", se ignora acá
    if message.text.startswith("/"):
        return

    # Detección de número de tarjeta (Luhn) 
    user_message_raw = message.text
    patron_tarjeta = re.search(r'([\d\s-]{11,23})', user_message_raw)
    if patron_tarjeta:
        mensaje_validacion_luhn(patron_tarjeta, bot, message)
        return

    # Contexto de imagen 
    user_input = filtrar_texto(message.text)
    contexto_imagen = ultima_imagen_por_chat.get(message.chat.id)
    contexto = contexto_de_imagen(contexto_imagen, message, user_input, ultima_imagen_por_chat)
    if contexto:
        user_input = contexto

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



# AUDIO Y FOTO


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
    bot.reply_to(message, response or "Error al procesar tu consulta.")


@bot.message_handler(content_types=["photo"])
def handle_foto(message):
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}"

        bot.reply_to(message, "🧠 Analizando la imagen...")
        descripcion = describir_imagen(file_url)
        ultima_imagen_por_chat[message.chat.id] = descripcion

        # Si detecta comprobante o transferencia
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
                f"}}"
            )

            respuesta_groq = get_groq_response(prompt, bank_data)

            try:
                comprobante_data = json.loads(respuesta_groq)
                guardar_comprobante_csv(comprobante_data)

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
                bot.reply_to(message, "⚠️ No pude interpretar los datos del comprobante.")
        else:
            bot.reply_to(message, f"🖼️ Descripción:\n\n{descripcion}")

    except Exception as e:
        bot.reply_to(message, f"❌ Error al procesar la imagen: {str(e)}")



# CALLBACKS DE BOTONES


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    call.text = call.data
    respuesta = get_groq_response(filtrar_texto(call.text), bank_data)
    bot.send_chat_action(call.message.chat.id, "typing")
    bot.send_message(call.message.chat.id, respuesta)



# MAIN LOOP


if __name__ == "__main__":
    if bank_data:
        print("Bot bancario iniciado con Groq, Whisper y comandos de usuario 💬")
        while True:
            try:
                bot.polling(none_stop=True, interval=0, timeout=20)
            except Exception as e:
                print(f"Error en el bot: {str(e)}")
                print("Reiniciando...")
                time.sleep(5)
    else:
        print("Error: No se pudo cargar el archivo dataset.json. El bot no se iniciará.")
