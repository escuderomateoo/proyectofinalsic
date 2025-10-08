# HOLA DEJE TODO COMENTADO POR QUE ALGO NO FUNCIONA, EN MAIN.PY SI SU ARCHIVO .ENV CONTIENE LOS TOKENS DE GROK Y TLG DEBERIA FUNCIONAR,
# import time
# import telebot
# from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
# from config import TELEGRAM_TOKEN
# from core.dataset import cargar_dataset, buscar_en_dataset
# from apis.groq_api import get_groq_response, transcribe_voice_with_groq
# from apis.sentimiento import analizador_sentimiento
# from apis.open_router_api import respuesta_seek

# # Cargar dataset una sola vez
# bank_data = cargar_dataset()

# bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ultimo_mensaje = {}  # guarda el texto de cada usuario para el callback


# def enviar_mensaje_largo(bot, chat_id, texto):
#     MAX_CHARS = 4000
#     for i in range(0, len(texto), MAX_CHARS):
#         trozo = texto[i : i + MAX_CHARS]
#         bot.send_message(chat_id, trozo)


# # -----------------------------
# # 1. Comando /start y /help
# # -----------------------------


# @bot.message_handler(commands=["start", "help"])
# def cmd_welcome(message):
#     bot.send_chat_action(message.chat.id, "typing")
#     time.sleep(1)
#     bot.reply_to(
#         message,
#         (
#             "¡Hola! Soy un bot IA 🤖.\n\n"
#             "📌 Preguntame lo que quieras.\n"
#             "📚 Si sé la respuesta, la saco de mi base de datos. /preguntas para ver la base 👀\n"
#             "🧠 Si no, podés elegir si te responde ChatGPT o DeepSeek.\n"
#             "❤️ También puedo analizar sentimientos con:\n"
#             '`/sentimiento "tu frase"`'
#         ),
#         parse_mode="Markdown",
#     )


# # -----------------------------
# # 2. Comando /sentimiento
# # -----------------------------


# @bot.message_handler(commands=["sentimiento"])
# def cmd_sentimiento(message):
#     texto = message.text
#     if len(texto.split(" ", 1)) < 2:
#         bot.reply_to(message, 'Usa: /sentimiento "tu frase"')
#         return
#     frase = texto.split(" ", 1)[1].strip('"')
#     resultado = analizador_sentimiento(frase)
#     bot.reply_to(message, resultado)


# ## -----------------------------
# # 2. Handler General
# # -----------------------------

# bot.message_handler(commands=["start"])


# def welcome_message(message: telebot.types.Message):
#     if not bank_data:
#         bot.reply_to(message, "Error cargando datos de los bancos.")
#         return

#     welcome_message = (
#         "💰 ¡Hola! Soy el bot informativo sobre bancos en Argentina.\n"
#         "Podés consultarme tarifas, costos de mantenimiento o comparar entidades."
#     )
#     bot.reply_to(message, welcome_message)


# @bot.message_handler(content_types=["text"])
# def handle_text_message(message: telebot.types.Message):
#     if not bank_data:
#         bot.reply_to(
#             message, "Error cargando los datos de los bancos. Intente más tarde."
#         )
#         return
#     bot.send_chat_action(message.chat.id, "typing")
#     response = get_groq_response(message.text)
#     if response:
#         bot.reply_to(message, response)
#     else:
#         bot.reply_to(
#             message,
#             "❌ Lo siento, hubo un error al procesar tu consulta.\n"
#             "Podés escribirnos a info@codificardev.com.ar para más información.",
#         )


# @bot.message_handler(content_types=["voice"])
# def handle_voice_message(message: telebot.types.Message):
#     if not bank_data:
#         bot.reply_to(message, "Error cargando datos de bancos. Intente más tarde.")
#         return

#     bot.send_chat_action(message.chat.id, "typing")
#     transcription = transcribe_voice_with_groq(message)
#     if not transcription:
#         bot.reply_to(message, "❌ No pude transcribir el audio. Probá de nuevo.")
#         return

#     response = get_groq_response(transcription)
#     if response:
#         bot.reply_to(message, response)
#     else:
#         bot.reply_to(
#             message,
#             "❌ Ocurrió un error al procesar tu consulta.\n"
#             "Podés escribirnos a info@codificardev.com.ar para más información.",
#         )


# # -----------------------------
# # Ejecutar bot
# # -----------------------------
# if __name__ == "__main__":
#     print("Bot iniciado ✅ Esperando mensajes...")
#     bot.infinity_polling()
