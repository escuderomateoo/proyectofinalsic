import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TELEGRAM_TOKEN
from core.dataset import cargar_dataset, buscar_en_dataset
from apis.groq_api import respuesta_groq
from apis.sentimiento import analizador_sentimiento
from apis.open_router_api import respuesta_seek

# Cargar dataset una sola vez
dataset = cargar_dataset()

bot = telebot.TeleBot(TELEGRAM_TOKEN)

ultimo_mensaje = {}  # guarda el texto de cada usuario para el callback


def enviar_mensaje_largo(bot, chat_id, texto):
    MAX_CHARS = 4000
    for i in range(0, len(texto), MAX_CHARS):
        trozo = texto[i : i + MAX_CHARS]
        bot.send_message(chat_id, trozo)


# -----------------------------
# 1. Comando /start y /help
# -----------------------------


@bot.message_handler(commands=["start", "help"])
def cmd_welcome(message):
    bot.send_chat_action(message.chat.id, "typing")
    time.sleep(1)
    bot.reply_to(
        message,
        (
            "¡Hola! Soy un bot IA 🤖.\n\n"
            "📌 Preguntame lo que quieras.\n"
            "📚 Si sé la respuesta, la saco de mi base de datos. /preguntas para ver la base 👀\n"
            "🧠 Si no, podés elegir si te responde ChatGPT o DeepSeek.\n"
            "❤️ También puedo analizar sentimientos con:\n"
            '`/sentimiento "tu frase"`'
        ),
        parse_mode="Markdown",
    )


# -----------------------------
# 2. Comando /sentimiento
# -----------------------------


@bot.message_handler(commands=["sentimiento"])
def cmd_sentimiento(message):
    texto = message.text
    if len(texto.split(" ", 1)) < 2:
        bot.reply_to(message, 'Usa: /sentimiento "tu frase"')
        return
    frase = texto.split(" ", 1)[1].strip('"')
    resultado = analizador_sentimiento(frase)
    bot.reply_to(message, resultado)


# -----------------------------
# 3. Comando /preguntas
# -----------------------------


@bot.message_handler(commands=["preguntas"])
def cmd_verbd(message):
    if not dataset:
        bot.reply_to(message, "La base de datos está vacía.")
        return

    preguntas = [f"- {item['pregunta']}" for item in dataset]
    texto = "Preguntas disponibles en la base de datos:\n" + "\n".join(preguntas)
    enviar_mensaje_largo(bot, message.chat.id, texto)


# -----------------------------
# 4. Handler general (con menú)
# -----------------------------


@bot.message_handler(func=lambda message: True)
def pedir_opcion(message):
    chat_id = message.chat.id
    texto = message.text

    # Primero probamos con el dataset
    respuesta = buscar_en_dataset(texto, dataset)
    if respuesta:
        bot.reply_to(message, respuesta)
        return

    # Si no está en el dataset, pedimos elección de IA
    ultimo_mensaje[chat_id] = texto

    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("🤖 ChatGPT", callback_data="chatgpt"),
        InlineKeyboardButton("🧠 DeepSeek", callback_data="deepseek"),
    )
    bot.send_message(
        chat_id,
        "No encontré nada en la base. ¿Con qué IA querés que te responda?",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: True)
def responder_callback(call):
    chat_id = call.message.chat.id
    texto_original = ultimo_mensaje.get(chat_id, "")

    if not texto_original:
        bot.send_message(chat_id, "No encontré el mensaje original.")
        return

    # Mostrar "escribiendo..." antes de responder
    bot.send_chat_action(chat_id, "typing")
    time.sleep(1)

    if call.data == "chatgpt":
        try:
            respuesta = respuesta_groq(texto_original)
            enviar_mensaje_largo(bot, chat_id, f"🤖 *ChatGPT dice:*\n{respuesta}")
        except Exception as e:
            bot.send_message(chat_id, "⚠️ Error al pedir respuesta a ChatGPT.")
            print(f"Error ChatGPT: {e}")

    elif call.data == "deepseek":
        try:
            respuesta = respuesta_seek(texto_original)
            enviar_mensaje_largo(bot, chat_id, f"🧠 *DeepSeek dice:*\n{respuesta}")
        except Exception as e:
            bot.send_message(chat_id, "⚠️ Error al pedir respuesta a DeepSeek.")
            print(f"Error DeepSeek: {e}")

    # Eliminamos el menú del chat
    bot.delete_message(chat_id, call.message.message_id)


# -----------------------------
# Ejecutar bot
# -----------------------------
if __name__ == "__main__":
    print("Bot iniciado ✅ Esperando mensajes...")
    bot.infinity_polling()
