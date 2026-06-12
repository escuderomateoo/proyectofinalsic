import os
import time
import signal
import threading
import logging
import logging.handlers
import numpy as np
import telebot
import json
import re
from collections import defaultdict
from time import monotonic
from datetime import datetime
from dotenv import load_dotenv

# ── Logging (primero que todo, para capturar errores de startup) ──────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            "bot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger(__name__)

# ── Validación de env y DB antes de cargar el modelo BERT (fail fast) ────────
from config import TELEGRAM_TOKEN, validate_env
validate_env()

import db
from db import init_db
init_db()

# ── Importaciones del bot ─────────────────────────────────────────────────────
from apis.sentimiento import EstadoDelChat, analizador_sentimiento
from apis.filtrado_de_texto import filtrar_texto
from apis.groq_api_texto import get_groq_response, RATE_LIMIT
from apis.obtencion_de_base_de_datos import load_bank_data
from apis.groq_api_foto import describir_imagen, contexto_de_imagen
from apis.groq_api_audio import transcribe_voice_with_groq
from apis.groq_api_csv import guardar_comprobante_csv
from apis.groq_api_tarjeta import validar_luhn, mensaje_validacion_luhn
from apis.carpetas import (
    handle_crear,
    handle_eliminar,
    handle_gasto,
    handle_depositar,
    handle_quitar,
    handle_transferir,
    handle_resumen,
)
from apis.graficos import generar_grafico_gastos, generar_grafico_sentimiento, generar_grafico_cripto, generar_grafico_dolar, generar_grafico_centinela
from apis.alertas import parsear_alerta, proxima_fecha_mensual
from apis.rag import init_rag, buscar_contexto
from apis.cotizaciones import (
    obtener_dolar, formatear_dolar,
    obtener_cripto, formatear_cripto, CRIPTO_ALIAS, TOP_5,
    obtener_bcra, obtener_cripto_historico,
    obtener_tasa_plazo_fijo,
    _contexto_dolar_texto, _contexto_cripto_texto, _contexto_inflacion_texto,
)
from apis.comparador import (
    menu_principal, menu_provincias, menu_bancos,
    resultado_baratos, resultado_gratis, resultado_provincia, resultado_comparacion,
)
from intent_detector import detectar_intencion
from watchers import parsear_watcher, cumple, describir_condicion, parsear_cancelacion
from briefing import parsear_briefing

load_dotenv()

bot = telebot.TeleBot(TELEGRAM_TOKEN)
bank_data = load_bank_data()
init_rag()

# ── Estado por usuario ────────────────────────────────────────────────────────
ultima_imagen_por_chat: dict[int, str] = {}
chat_workers: dict[int, EstadoDelChat] = {}
conversation_history: dict[int, list] = defaultdict(list)
comparador_state: dict[int, dict] = {}  # {chat_id: {"paso": 1, "banco1": idx}}

# ── Rate limiting ─────────────────────────────────────────────────────────────
_rate_timestamps: dict[int, list[float]] = defaultdict(list)
RATE_LIMIT_MAX = 10     # mensajes máximos
RATE_LIMIT_WINDOW = 60  # por ventana de N segundos
MAX_HISTORY = 10        # últimos N mensajes del historial (5 intercambios)

MSG_RATE_LIMIT = (
    "⏳ Alcanzamos el límite de consultas a la IA por ahora.\n"
    "Probá de nuevo en un rato 🙏 (los comandos de mercado, cotizaciones y "
    "gastos siguen funcionando normalmente)."
)


# ── Enriquecimiento dinámico de contexto ─────────────────────────────────────

_KW_DOLAR = {"dolar","dólar","blue","oficial","mep","ccl","cambio","cotizacion",
              "cotización","divisas","billete","moneda","peso","ars","usd"}
_KW_CRIPTO = {"bitcoin","btc","ethereum","eth","cripto","crypto","criptomoneda",
              "solana","sol","binance","bnb","usdt","tether","cardano","xrp","doge"}
_KW_INFLACION = {"inflacion","inflación","ipc","precios","bcra","indec",
                 "canasta","tarifas","poder adquisitivo"}


def _enriquecer_contexto(texto: str) -> str:
    palabras = set(texto.lower().split())
    secciones = []

    # 1. Datos de mercado en tiempo real
    contextos_live = []
    if palabras & _KW_DOLAR:
        ctx = _contexto_dolar_texto()
        if ctx:
            contextos_live.append(ctx)
    if palabras & _KW_CRIPTO:
        ctx = _contexto_cripto_texto()
        if ctx:
            contextos_live.append(ctx)
    if palabras & _KW_INFLACION:
        ctx = _contexto_inflacion_texto()
        if ctx:
            contextos_live.append(ctx)
    if contextos_live:
        secciones.append(
            "[DATOS DE MERCADO EN TIEMPO REAL]\n" + "\n\n".join(contextos_live)
        )

    # 2. Conocimiento de documentos (RAG semántico)
    ctx_docs = buscar_contexto(texto)
    if ctx_docs:
        secciones.append("[CONOCIMIENTO BASE — fragmentos relevantes]\n" + ctx_docs)

    if not secciones:
        return texto

    return "\n\n".join(secciones) + "\n\n[CONSULTA DEL USUARIO]\n" + texto


def is_rate_limited(chat_id: int) -> bool:
    now = monotonic()
    ts = _rate_timestamps[chat_id]
    _rate_timestamps[chat_id] = [t for t in ts if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_timestamps[chat_id]) >= RATE_LIMIT_MAX:
        logger.warning("Rate limit alcanzado para chat %d", chat_id)
        return True
    _rate_timestamps[chat_id].append(now)
    return False


def get_or_create_worker(chat_id: int) -> EstadoDelChat:
    if chat_id not in chat_workers:
        chat_workers[chat_id] = EstadoDelChat(chat_id)
    return chat_workers[chat_id]


def add_to_history(chat_id: int, role: str, content: str) -> None:
    history = conversation_history[chat_id]
    history.append({"role": role, "content": content})
    if len(history) > MAX_HISTORY:
        conversation_history[chat_id] = history[-MAX_HISTORY:]


def enviar_md(chat_id: int, texto: str, reply_to: telebot.types.Message | None = None) -> None:
    """Envía un mensaje en Markdown, con fallback a texto plano si el parser falla.

    El Markdown legacy de Telegram rompe ante guiones bajos sueltos (típico de
    los nombres de comando como /cancelar_centinela) o asteriscos sin cerrar.
    Si eso pasa, reintenta sin formato para que la acción no se reporte como
    fallida cuando en realidad se completó.
    """
    try:
        if reply_to is not None:
            bot.reply_to(reply_to, texto, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, texto, parse_mode="Markdown")
    except Exception as e:
        logger.warning("Markdown inválido, reenvío en texto plano: %s", e)
        if reply_to is not None:
            bot.reply_to(reply_to, texto)
        else:
            bot.send_message(chat_id, texto)


# ── Comandos ──────────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def welcome_message(message: telebot.types.Message):
    chat_id = message.chat.id
    chat_workers[chat_id] = EstadoDelChat(chat_id)
    conversation_history[chat_id] = []

    IKB = telebot.types.InlineKeyboardButton
    menu = telebot.types.InlineKeyboardMarkup(row_width=2)
    menu.add(
        IKB("💵 Dólar en vivo",      callback_data="menu:dolar"),
        IKB("🪙 Cripto",             callback_data="menu:cripto"),
        IKB("🏛 Datos BCRA",         callback_data="menu:bcra"),
        IKB("🏦 Comparar bancos",    callback_data="menu:comparar"),
        IKB("💱 Convertir moneda",   callback_data="menu:convertir"),
        IKB("🏦 Plazo fijo",         callback_data="menu:plazo_fijo"),
    )
    menu.add(IKB("📋 Ver todos los comandos", callback_data="menu:ayuda"))

    bot.reply_to(
        message,
        "💰 *¡Bienvenido a BankRanks Argentina!*\n\n"
        "Soy tu asistente financiero inteligente. Puedo ayudarte con:\n"
        "• Tarifas y comparativa de bancos\n"
        "• Cotizaciones del dólar y cripto en tiempo real\n"
        "• Análisis de comprobantes de transferencia\n"
        "• Recordatorios y gestión de gastos\n"
        "• 🚨 Centinelas: te aviso cuando el dólar o una cripto cruzan un precio\n"
        "• 🌅 Resumen financiero diario a la hora que elijas (/briefing)\n\n"
        "También podés escribirme cualquier consulta bancaria o financiera 👇",
        parse_mode="Markdown",
        reply_markup=menu,
    )
    logger.info("Usuario %d inició sesión", chat_id)


@bot.message_handler(commands=["ayuda", "help"])
def cmd_ayuda(message: telebot.types.Message):
    texto = (
        "📋 Comandos disponibles:\n\n"
        "💬 Generales\n"
        "/start — Iniciar o reiniciar la conversación\n"
        "/ayuda — Mostrar este mensaje\n\n"
        "🏦 Bancario\n"
        "Enviá cualquier pregunta sobre bancos y tarifas en Argentina\n"
        "/comparar — Wizard interactivo para comparar bancos\n\n"
        "💱 Mercados en tiempo real\n"
        "/dolar — Cotizaciones del dólar (blue, MEP, CCL...)\n"
        "/grafico_dolar — Gráfico comparativo de cotizaciones\n"
        "/cripto [moneda] — Precios cripto (BTC, ETH, SOL...)\n"
        "/grafico_cripto [moneda] — Historial 7 días de una cripto\n"
        "/bcra — Inflación, reservas y tasas del BCRA\n"
        "/convertir monto usd|ars — Convertir entre dólar y pesos\n"
        "/plazo_fijo monto dias [tna%] — Simular rendimiento de PF\n\n"
        "💼 Gestión de gastos\n"
        "/crear nombre monto — Crear una carpeta de gastos\n"
        "/depositar nombre monto — Sumar dinero a una carpeta\n"
        "/quitar nombre monto — Restar dinero de una carpeta\n"
        "/eliminar nombre — Eliminar una carpeta\n"
        "/gasto nombre — Ver saldo de una carpeta\n"
        "/resumen — Ver todas las carpetas\n"
        "/grafico_gastos — Gráfico de torta de tus gastos\n"
        "/analizar_gastos — Consejos de IA sobre tus gastos\n\n"
        "🔬 Análisis\n"
        "/sentimiento \"frase\" — Analizar el tono de un texto\n"
        "/mi_perfil — Ver tu perfil de sentimiento con gráfico\n\n"
        "⏰ Recordatorios\n"
        "/recordar [mensaje] en X minutos/horas — Programar alerta\n"
        "/recordar [mensaje] a las HH:MM — Alerta a hora exacta\n"
        "/recordar [mensaje] el dia X — Recordatorio mensual\n"
        "/mis_alertas — Ver tus recordatorios activos\n"
        "/cancelar_alerta [id] — Cancelar un recordatorio\n\n"
        "🚨 Centinelas de precio\n"
        'Escribime: "avisame cuando el blue supere los 1500"\n'
        '          "notificame si bitcoin baja de 60000"\n'
        "Te aviso solo, con un gráfico, apenas se cumple\n"
        "/mis_centinelas — Ver tus centinelas activos\n"
        "/cancelar_centinela [id] — Cancelar un centinela\n\n"
        "🌅 Resumen financiero diario\n"
        "/briefing — Ver el resumen ahora (dólar, cripto, inflación)\n"
        "/briefing HH:MM — Recibirlo todos los días a esa hora\n"
        '          o decime: "mandame el resumen diario a las 9"\n'
        "/briefing off — Desactivarlo\n\n"
        "📎 También podés enviar:\n"
        "• Imágenes o comprobantes de transferencia\n"
        "• Mensajes de voz"
    )
    bot.reply_to(message, texto)


@bot.message_handler(commands=["mi_perfil"])
def cmd_mi_perfil(message: telebot.types.Message):
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, "typing")

    datos = db.obtener_notas_usuario(chat_id)

    if not datos:
        bot.reply_to(
            message,
            "📊 Aún no tengo datos suficientes tuyos.\n"
            "Enviá al menos 5 mensajes al bot para que pueda analizar tu perfil.",
        )
        return

    notas = [d["nota"] for d in datos]
    total = len(notas)
    promedio = sum(notas) / total

    # Tendencia: compara primera mitad vs segunda mitad
    if total >= 4:
        mid = total // 2
        p1 = sum(notas[:mid]) / mid
        p2 = sum(notas[mid:]) / (total - mid)
        if p2 > p1 + 0.3:
            tendencia = "📈 Mejorando"
        elif p2 < p1 - 0.3:
            tendencia = "📉 Bajando"
        else:
            tendencia = "➡️ Estable"
    else:
        tendencia = "➡️ Estable"

    estrellas = "⭐" * round(promedio)

    if promedio >= 4:
        evaluacion = "Sos un usuario con tono muy positivo. El bot aprecia tu buena onda 😊"
    elif promedio >= 3:
        evaluacion = "Tenés un tono neutro y equilibrado. Consultas claras y directas."
    else:
        evaluacion = "Parece que algunas consultas te generaron frustración. ¡Estamos para ayudarte!"

    texto = (
        f"👤 *Tu perfil en BankRanks*\n\n"
        f"📊 *Estadísticas:*\n"
        f"• Mensajes analizados: {total}\n"
        f"• Sentimiento promedio: {estrellas} ({promedio:.1f}/5)\n"
        f"• Tendencia: {tendencia}\n\n"
        f"🔍 *Evaluación:*\n{evaluacion}"
    )

    bot.reply_to(message, texto, parse_mode="Markdown")

    if total >= 3:
        bot.send_chat_action(chat_id, "upload_photo")
        try:
            imagen = generar_grafico_sentimiento(notas)
            bot.send_photo(chat_id, imagen, caption="📈 Evolución de tu sentimiento en el tiempo")
        except Exception as e:
            logger.error("Error generando gráfico de sentimiento para chat %d: %s", chat_id, e)


@bot.message_handler(commands=["analizar_gastos"])
def cmd_analizar_gastos(message: telebot.types.Message):
    chat_id = message.chat.id
    carpetas = db.listar_carpetas()

    if not carpetas:
        bot.reply_to(message,
            "No tenés carpetas creadas todavía.\n"
            "Usá /crear nombre monto para empezar a registrar tus gastos."
        )
        return

    bot.send_chat_action(chat_id, "typing")

    total = sum(c["dinero"] for c in carpetas)
    detalle = "\n".join(
        f"- {c['nombre']}: ${c['dinero']:,.2f} ({c['dinero']/total*100:.1f}%)"
        for c in carpetas
    )

    prompt = (
        f"Sos un asesor financiero personal para usuarios argentinos. "
        f"El usuario tiene registrados los siguientes gastos por categoría:\n\n"
        f"{detalle}\n\n"
        f"Total: ${total:,.2f}\n\n"
        f"Analizá su distribución de gastos y dales 3 recomendaciones concretas y personalizadas "
        f"para optimizar su presupuesto. Sé directo, amigable y usá ejemplos con los números reales del usuario. "
        f"No inventes categorías que no están en la lista. Respondé en español."
    )

    response = get_groq_response(prompt, bank_data, max_tokens=1000)

    if response == RATE_LIMIT:
        bot.reply_to(message, MSG_RATE_LIMIT)
    elif response:
        bot.reply_to(message, f"💡 *Análisis de tus gastos*\n\n{response}", parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ No pude generar el análisis. Intentá de nuevo.")


@bot.message_handler(commands=["comparar"])
def cmd_comparar(message: telebot.types.Message):
    comparador_state.pop(message.chat.id, None)
    bot.send_message(
        message.chat.id,
        "🏦 *Comparador de bancos*\n¿Qué querés buscar?",
        reply_markup=menu_principal(),
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["sentimiento"])
def cmd_sentimiento(message: telebot.types.Message):
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        bot.reply_to(message, 'Usá: /sentimiento "tu frase"')
        return
    frase = parts[1].strip('"')
    nota, confianza = analizador_sentimiento(frase)
    estrellas = "⭐" * nota
    bot.reply_to(message, f"Sentimiento: {estrellas} ({nota}/5)\nConfianza: {confianza:.0%}")


@bot.message_handler(commands=["crear"])
def cmd_crear_carpeta(message: telebot.types.Message):
    partes = message.text.split()
    if len(partes) < 3:
        bot.reply_to(message, "Uso: /crear nombre dinero_inicial")
        return
    try:
        float(partes[2])
    except ValueError:
        bot.reply_to(message, "⚠️ El dinero inicial debe ser un número.")
        return
    bot.reply_to(message, handle_crear(message.text))


@bot.message_handler(commands=["gasto"])
def cmd_ver_gasto(message: telebot.types.Message):
    if len(message.text.split()) < 2:
        bot.reply_to(message, "Uso: /gasto nombre")
        return
    bot.reply_to(message, handle_gasto(message.text))


@bot.message_handler(commands=["resumen", "resumen_gastos"])
def cmd_resumen(message: telebot.types.Message):
    bot.reply_to(message, handle_resumen(message.text))


@bot.message_handler(commands=["grafico_gastos", "grafico"])
def cmd_grafico_gastos(message: telebot.types.Message):
    chat_id = message.chat.id
    carpetas = db.listar_carpetas()
    activas = [c for c in carpetas if c["dinero"] > 0]

    if not carpetas:
        bot.reply_to(message, "No tenés carpetas creadas. Usá /crear nombre monto para empezar.")
        return
    if not activas:
        bot.reply_to(message, "Todas tus carpetas están en $0. Usá /depositar para agregar dinero.")
        return

    bot.send_chat_action(chat_id, "upload_photo")
    try:
        imagen = generar_grafico_gastos(activas)
        total = sum(c["dinero"] for c in activas)
        caption = f"💼 {len(activas)} categorías · Total: ${total:,.2f}"
        bot.send_photo(chat_id, imagen, caption=caption)
    except Exception as e:
        logger.error("Error generando gráfico para chat %d: %s", chat_id, e)
        bot.reply_to(message, "❌ No pude generar el gráfico. Intentá de nuevo.")


@bot.message_handler(commands=["depositar"])
def cmd_depositar(message: telebot.types.Message):
    partes = message.text.split()
    if len(partes) < 3:
        bot.reply_to(message, "Uso: /depositar destino monto")
        return
    try:
        float(partes[2])
    except ValueError:
        bot.reply_to(message, "⚠️ El monto debe ser un número.")
        return
    bot.reply_to(message, handle_depositar(message.text))


@bot.message_handler(commands=["eliminar"])
def cmd_eliminar(message: telebot.types.Message):
    if len(message.text.split()) < 2:
        bot.reply_to(message, "Uso: /eliminar nombre")
        return
    bot.reply_to(message, handle_eliminar(message.text))


@bot.message_handler(commands=["quitar"])
def cmd_quitar(message: telebot.types.Message):
    partes = message.text.split()
    if len(partes) < 3:
        bot.reply_to(message, "Uso: /quitar destino monto")
        return
    try:
        float(partes[2])
    except ValueError:
        bot.reply_to(message, "⚠️ El monto debe ser un número.")
        return
    bot.reply_to(message, handle_quitar(message.text))


# ── Cotizaciones ─────────────────────────────────────────────────────────────

@bot.message_handler(commands=["dolar"])
def cmd_dolar(message: telebot.types.Message):
    bot.send_chat_action(message.chat.id, "typing")
    datos = obtener_dolar()
    if not datos:
        bot.reply_to(message, "❌ No pude obtener las cotizaciones en este momento. Intentá de nuevo en unos segundos.")
        return
    bot.reply_to(message, formatear_dolar(datos), parse_mode="Markdown")


@bot.message_handler(commands=["cripto"])
def cmd_cripto(message: telebot.types.Message):
    bot.send_chat_action(message.chat.id, "typing")
    partes = message.text.split()
    if len(partes) >= 2:
        alias = partes[1].lower()
        coin_id = CRIPTO_ALIAS.get(alias)
        if not coin_id:
            bot.reply_to(
                message,
                f"❌ No conozco '{partes[1]}'.\n\n"
                "Monedas disponibles: BTC, ETH, SOL, BNB, USDT, ADA, XRP, DOGE",
            )
            return
        coins = [coin_id]
    else:
        coins = TOP_5

    datos = obtener_cripto(coins)
    if not datos:
        bot.reply_to(message, "❌ No pude obtener los precios en este momento. Intentá de nuevo en unos segundos.")
        return
    bot.reply_to(message, formatear_cripto(datos, coins), parse_mode="Markdown")


@bot.message_handler(commands=["bcra"])
def cmd_bcra(message: telebot.types.Message):
    bot.send_chat_action(message.chat.id, "typing")
    texto = obtener_bcra()
    bot.reply_to(message, texto, parse_mode="Markdown")


@bot.message_handler(commands=["grafico_cripto"])
def cmd_grafico_cripto(message: telebot.types.Message):
    chat_id = message.chat.id
    partes = message.text.split()

    alias = partes[1].lower() if len(partes) >= 2 else "btc"
    coin_id = CRIPTO_ALIAS.get(alias)
    if not coin_id:
        bot.reply_to(message, f"❌ No conozco '{partes[1]}'.\nMonedas: BTC, ETH, SOL, BNB, USDT, ADA, XRP, DOGE")
        return

    from apis.cotizaciones import _CRIPTO_INFO
    emoji, nombre, ticker = _CRIPTO_INFO.get(coin_id, ("●", coin_id.capitalize(), coin_id.upper()))

    bot.send_chat_action(chat_id, "upload_photo")
    historico = obtener_cripto_historico(coin_id, days=7)
    if not historico or len(historico) < 2:
        bot.reply_to(message, "❌ No pude obtener el historial. Intentá de nuevo.")
        return

    buf = generar_grafico_cripto(historico, nombre, ticker, dias=7)
    bot.send_photo(chat_id, buf, caption=f"📈 Historial 7 días — {nombre} ({ticker})")


@bot.message_handler(commands=["grafico_dolar"])
def cmd_grafico_dolar(message: telebot.types.Message):
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, "upload_photo")
    datos = obtener_dolar()
    if not datos:
        bot.reply_to(message, "❌ No pude obtener las cotizaciones. Intentá de nuevo.")
        return
    buf = generar_grafico_dolar(datos)
    bot.send_photo(chat_id, buf, caption="💵 Comparativa de cotizaciones del dólar")


@bot.message_handler(commands=["convertir"])
def cmd_convertir(message: telebot.types.Message):
    partes = message.text.split()
    if len(partes) < 3:
        bot.reply_to(
            message,
            "Uso:\n"
            "/convertir 500 usd  →  cuánto son en ARS (por tipo de cambio)\n"
            "/convertir 100000 ars  →  cuántos USD podés comprar",
        )
        return
    try:
        monto = float(partes[1].replace(",", "").replace("$", ""))
    except ValueError:
        bot.reply_to(message, "❌ El monto debe ser un número. Ejemplo: /convertir 500 usd")
        return
    moneda = partes[2].lower()
    if moneda not in ("usd", "ars"):
        bot.reply_to(message, "❌ La moneda debe ser USD o ARS.")
        return

    bot.send_chat_action(message.chat.id, "typing")
    datos = obtener_dolar()
    if not datos:
        bot.reply_to(message, "❌ No pude obtener las cotizaciones. Intentá de nuevo.")
        return

    datos_dict = {d["casa"]: d for d in datos}
    orden  = ["oficial", "blue", "bolsa", "contadoconliqui", "cripto", "tarjeta"]
    emojis = {"oficial": "🏦", "blue": "💵", "bolsa": "📈",
              "contadoconliqui": "💹", "cripto": "🔒", "tarjeta": "💳"}
    nombres = {"oficial": "Oficial", "blue": "Blue", "bolsa": "MEP",
               "contadoconliqui": "CCL", "cripto": "Cripto", "tarjeta": "Tarjeta"}

    if moneda == "usd":
        lineas = [f"💱 *{monto:,.2f} USD → ARS*\n_(vendiendo USD al tipo compra)_\n"]
        for casa in orden:
            d = datos_dict.get(casa)
            if not d:
                continue
            tasa = d.get("compra") or 0
            if not tasa:
                continue
            lineas.append(f"{emojis.get(casa,'')} {nombres.get(casa):<10} ${monto * tasa:>12,.2f}")
    else:
        lineas = [f"💱 *${monto:,.0f} ARS → USD*\n_(comprando USD al tipo venta)_\n"]
        for casa in orden:
            d = datos_dict.get(casa)
            if not d:
                continue
            tasa = d.get("venta") or 0
            if not tasa:
                continue
            lineas.append(f"{emojis.get(casa,'')} {nombres.get(casa):<10} USD {monto / tasa:>9,.2f}")

    bot.reply_to(message, "\n".join(lineas), parse_mode="Markdown")


@bot.message_handler(commands=["plazo_fijo"])
def cmd_plazo_fijo(message: telebot.types.Message):
    USO = (
        "📋 Uso: /plazo_fijo capital dias [tna]\n\n"
        "  capital = monto a invertir (ej: 100000)\n"
        "  dias    = duración del plazo (ej: 30)\n"
        "  tna     = tasa anual % opcional (ej: 97.5)\n\n"
        "Ejemplos:\n"
        "/plazo_fijo 100000 30\n"
        "/plazo_fijo 500000 60 97.5"
    )
    partes = message.text.split()
    if len(partes) < 3:
        bot.reply_to(message, USO)
        return

    try:
        capital = float(partes[1].replace(",", "").replace("$", ""))
        dias = int(partes[2])
    except ValueError:
        bot.reply_to(message, f"❌ Capital o días inválidos.\n\n{USO}")
        return

    if capital <= 0 or dias <= 0:
        bot.reply_to(message, "❌ El capital y los días deben ser mayores a 0.")
        return

    if len(partes) >= 4:
        try:
            tna = float(partes[3].replace(",", ".").replace("%", ""))
            fuente = "TNA indicada"
        except ValueError:
            bot.reply_to(message, f"❌ TNA inválida. Usá un número, ej: 97.5\n\n{USO}")
            return
    else:
        bot.send_chat_action(message.chat.id, "typing")
        tna = obtener_tasa_plazo_fijo()
        fuente = "TNA promedio de mercado"

    try:
        ganancia = capital * (tna / 100) / 365 * dias
        total    = capital + ganancia
        tea      = ((1 + tna / 100 / 365) ** 365 - 1) * 100

        bot.reply_to(
            message,
            f"🏦 *Simulador de Plazo Fijo*\n\n"
            f"💰 Capital inicial:    ${capital:>14,.2f}\n"
            f"📅 Plazo:              {dias} días\n"
            f"📈 TNA:                {tna:.2f}%  ({fuente})\n"
            f"📊 TEA equivalente:    {tea:.2f}%\n\n"
            f"💵 Ganancia bruta:     ${ganancia:>14,.2f}\n"
            f"💎 Total a cobrar:     ${total:>14,.2f}",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("Error en plazo_fijo: %s", e)
        bot.reply_to(message, "❌ Error al calcular. Verificá los datos e intentá de nuevo.")


# ── Alertas / Recordatorios ───────────────────────────────────────────────────

@bot.message_handler(commands=["recordar"])
def cmd_recordar(message: telebot.types.Message):
    partes = message.text.split(" ", 1)
    if len(partes) < 2:
        bot.reply_to(
            message,
            "⏰ Usá uno de estos formatos:\n\n"
            "/recordar pagar alquiler en 5 minutos\n"
            "/recordar reunion en 2 horas\n"
            "/recordar pagar tarjeta a las 15:30\n"
            "/recordar pagar servicio el dia 10  ← se repite cada mes",
        )
        return
    try:
        mensaje, fecha, recurrente, dia_mes = parsear_alerta(partes[1])
        db.crear_alerta(message.chat.id, mensaje, fecha, recurrente, dia_mes)
        tipo = "🔁 Mensual" if recurrente else "🔔 Una vez"
        fecha_str = fecha.strftime("%d/%m/%Y a las %H:%M")
        bot.reply_to(
            message,
            f"✅ Recordatorio guardado\n"
            f"📅 {fecha_str}  |  {tipo}\n"
            f"💬 {mensaje}",
        )
    except ValueError as e:
        bot.reply_to(message, f"❌ {e}")


@bot.message_handler(commands=["mis_alertas"])
def cmd_mis_alertas(message: telebot.types.Message):
    alertas = db.listar_alertas_usuario(message.chat.id)
    if not alertas:
        bot.reply_to(message, "No tenés recordatorios pendientes.")
        return
    lineas = ["⏰ *Tus recordatorios:*\n"]
    for a in alertas:
        fecha_str = a["fecha_hora"][:16].replace("T", " ")
        tipo = "🔁 Mensual" if a["recurrente"] else "🔔 Una vez"
        lineas.append(f"[{a['id']}] {tipo}\n   📅 {fecha_str}\n   💬 {a['mensaje']}")
    bot.reply_to(message, "\n\n".join(lineas), parse_mode="Markdown")


@bot.message_handler(commands=["cancelar_alerta"])
def cmd_cancelar_alerta(message: telebot.types.Message):
    partes = message.text.split()
    if len(partes) < 2 or not partes[1].isdigit():
        bot.reply_to(message, "Usá: /cancelar_alerta <id>\nVer IDs con /mis_alertas")
        return
    eliminado = db.cancelar_alerta_usuario(int(partes[1]), message.chat.id)
    bot.reply_to(message, "✅ Recordatorio cancelado." if eliminado else "❌ No encontré ese recordatorio.")


# ── Centinelas de precio ──────────────────────────────────────────────────────

def _simbolo_moneda(clase: str) -> str:
    return "USD " if clase == "cripto" else "$"


def _snapshot_precios(watchers: list[dict]) -> dict[tuple[str, str], float]:
    """Precio actual de cada (clase, activo) presente en ``watchers``.

    Hace como mucho una llamada al dólar y una a cripto (batch), sin importar
    cuántos centinelas haya, para no saturar las APIs en cada tick.
    """
    precios: dict[tuple[str, str], float] = {}

    if any(w["clase"] == "dolar" for w in watchers):
        datos = obtener_dolar()
        if datos:
            for d in datos:
                valor = d.get("venta") or d.get("compra")
                if valor:
                    precios[("dolar", d["casa"])] = float(valor)

    coins = sorted({w["activo"] for w in watchers if w["clase"] == "cripto"})
    if coins:
        datos = obtener_cripto(coins)
        if datos:
            for c in coins:
                info = datos.get(c)
                if info and info.get("usd") is not None:
                    precios[("cripto", c)] = float(info["usd"])

    return precios


def _notificar_disparo(chat_id: int, w: dict, precio: float) -> None:
    """Avisa al usuario que su centinela se cumplió y manda el gráfico del cruce."""
    simbolo = _simbolo_moneda(w["clase"])
    verbo = "superó" if w["op"] == ">=" else "bajó de"
    enviar_md(
        chat_id,
        "🚨 *¡Centinela disparado!*\n"
        f"{w['emoji']} *{w['nombre']}* {verbo} el umbral de {simbolo}{w['umbral']:,.2f}\n"
        f"📍 Precio actual: {simbolo}{precio:,.2f}",
    )
    try:
        bot.send_chat_action(chat_id, "upload_photo")
        historico = (
            obtener_cripto_historico(w["activo"], days=7)
            if w["clase"] == "cripto" else None
        )
        buf = generar_grafico_centinela(
            w["nombre"], w["emoji"], precio, w["umbral"], w["op"], historico
        )
        bot.send_photo(chat_id, buf)
    except Exception as e:
        logger.error("Error generando gráfico de centinela para chat %d: %s", chat_id, e)


def _crear_watcher_desde_texto(message: telebot.types.Message, w: dict) -> None:
    """Guarda un centinela parseado y confirma, mostrando el precio actual."""
    chat_id = message.chat.id
    simbolo = _simbolo_moneda(w["clase"])

    precio = _snapshot_precios([w]).get((w["clase"], w["activo"]))
    wid = db.crear_watcher(
        chat_id, w["clase"], w["activo"], w["nombre"], w["emoji"], w["op"], w["umbral"]
    )
    logger.info("Centinela %d creado para chat %d: %r", wid, chat_id, w)

    cond = describir_condicion(w["op"], w["umbral"], w["clase"])
    lineas = [
        "🔔 *Centinela activado*",
        f"{w['emoji']} *{w['nombre']}*",
        f"Te aviso apenas {cond}.",
    ]
    if precio is not None:
        lineas.append(f"📍 Precio ahora: {simbolo}{precio:,.2f}")
        if cumple(w["op"], precio, w["umbral"]):
            lineas.append("\n⚡ _Ya se cumple ahora mismo: te lo confirmo en unos segundos._")
    lineas.append(f"\n🆔 Centinela #{wid} · lo reviso cada 30s")
    lineas.append(f"Cancelalo con `/cancelar_centinela {wid}`")
    enviar_md(chat_id, "\n".join(lineas))


def _cancelar_watcher_desde_texto(message: telebot.types.Message, pedido: dict) -> None:
    """Cancela centinelas según un pedido en lenguaje natural ya parseado."""
    chat_id = message.chat.id
    watchers = db.listar_watchers_usuario(chat_id)
    if not watchers:
        bot.reply_to(message, "No tenés centinelas de precio activos para cancelar.")
        return

    tipo = pedido["tipo"]

    if tipo == "todos":
        for w in watchers:
            db.eliminar_watcher(w["id"])
        bot.reply_to(message, f"✅ Cancelé tus {len(watchers)} centinelas de precio.")
        return

    if tipo == "id":
        ok = db.cancelar_watcher_usuario(pedido["id"], chat_id)
        bot.reply_to(
            message,
            f"✅ Centinela #{pedido['id']} cancelado."
            if ok else f"❌ No encontré el centinela #{pedido['id']}. Mirá /mis_centinelas.",
        )
        return

    if tipo == "activo":
        coincidencias = [
            w for w in watchers
            if w["clase"] == pedido["clase"] and w["activo"] == pedido["activo"]
        ]
        if not coincidencias:
            bot.reply_to(message, f"No tenés centinelas de {pedido['nombre']}.")
            return
        for w in coincidencias:
            db.eliminar_watcher(w["id"])
        plural = "centinela" if len(coincidencias) == 1 else "centinelas"
        bot.reply_to(message, f"✅ Cancelé {len(coincidencias)} {plural} de {pedido['nombre']}.")
        return

    # tipo == "generico": quiere cancelar pero no aclaró cuál.
    if len(watchers) == 1:
        w = watchers[0]
        db.eliminar_watcher(w["id"])
        bot.reply_to(message, f"✅ Cancelé tu centinela de {w['nombre']}.")
        return
    lineas = ["Tenés varios centinelas, ¿cuál querés cancelar?\n"]
    for w in watchers:
        cond = describir_condicion(w["op"], w["umbral"], w["clase"])
        lineas.append(f"#{w['id']} — {w['emoji']} {w['nombre']} ({cond})")
    lineas.append('\nDecime, por ej.: "cancelá el centinela 2" o "cancelá el del blue".')
    bot.reply_to(message, "\n".join(lineas))


@bot.message_handler(commands=["mis_centinelas"])
def cmd_mis_centinelas(message: telebot.types.Message):
    watchers = db.listar_watchers_usuario(message.chat.id)
    if not watchers:
        bot.reply_to(
            message,
            "No tenés centinelas de precio activos.\n\n"
            'Probá escribiéndome: "avisame cuando el blue supere los 1500"',
        )
        return
    lineas = ["🔔 *Tus centinelas de precio:*\n"]
    for w in watchers:
        cond = describir_condicion(w["op"], w["umbral"], w["clase"])
        lineas.append(f"`#{w['id']}` {w['emoji']} {w['nombre']} — {cond}")
    lineas.append("\nCancelá uno con `/cancelar_centinela <id>`")
    enviar_md(message.chat.id, "\n".join(lineas), reply_to=message)


@bot.message_handler(commands=["cancelar_centinela"])
def cmd_cancelar_centinela(message: telebot.types.Message):
    partes = message.text.split()
    if len(partes) < 2 or not partes[1].isdigit():
        bot.reply_to(message, "Usá: /cancelar_centinela <id>\nVer IDs con /mis_centinelas")
        return
    ok = db.cancelar_watcher_usuario(int(partes[1]), message.chat.id)
    bot.reply_to(message, "✅ Centinela cancelado." if ok else "❌ No encontré ese centinela.")


@bot.message_handler(commands=["probar_centinela"])
def cmd_probar_centinela(message: telebot.types.Message):
    """Fuerza el disparo de un centinela para probarlo sin esperar al mercado.

    Usa un precio simulado (el que pase el usuario, o el umbral si no lo pasa) y
    NO elimina el centinela: la condición real sigue armada para el cruce de
    verdad.
    """
    partes = message.text.split()
    if len(partes) < 2 or not partes[1].isdigit():
        bot.reply_to(
            message,
            "Usá: /probar_centinela <id> [precio]\n"
            "Fuerza el disparo para probarlo. Ver IDs con /mis_centinelas",
        )
        return

    wid = int(partes[1])
    w = next((x for x in db.listar_watchers_usuario(message.chat.id) if x["id"] == wid), None)
    if not w:
        bot.reply_to(message, "❌ No encontré ese centinela. Ver IDs con /mis_centinelas")
        return

    if len(partes) >= 3:
        try:
            precio = float(partes[2].replace(",", ".").replace("$", ""))
        except ValueError:
            bot.reply_to(message, "❌ El precio simulado debe ser un número. Ej: /probar_centinela 3 1500")
            return
    else:
        precio = w["umbral"]

    bot.send_message(message.chat.id, "🧪 Simulando el disparo (el centinela sigue activo)...")
    _notificar_disparo(message.chat.id, w, precio)


# ── Briefing diario (resumen financiero) ──────────────────────────────────────

def _componer_briefing(chat_id: int, datos_dolar: list[dict] | None) -> str:
    """Arma el texto del resumen financiero: dólar, cripto, inflación y centinelas."""
    from apis.cotizaciones import _CRIPTO_INFO

    partes = [f"🌅 *Tu resumen financiero* — {datetime.now().strftime('%d/%m/%Y')}"]

    if datos_dolar:
        dd = {d["casa"]: d for d in datos_dolar}
        of, bl = dd.get("oficial"), dd.get("blue")
        sub = ["\n💵 *Dólar*"]
        if of and of.get("venta"):
            sub.append(f"   Oficial: ${of['venta']:,.2f}")
        if bl and bl.get("venta"):
            sub.append(f"   Blue: ${bl['venta']:,.2f}")
        if of and bl and of.get("venta") and bl.get("venta"):
            brecha = (bl["venta"] - of["venta"]) / of["venta"] * 100
            sub.append(f"   Brecha blue/oficial: {brecha:.1f}%")
        if len(sub) > 1:
            partes.append("\n".join(sub))

    datos_cr = obtener_cripto(["bitcoin", "ethereum"])
    if datos_cr:
        sub = ["\n🪙 *Cripto (USD)*"]
        for cid in ("bitcoin", "ethereum"):
            info = datos_cr.get(cid)
            if not info:
                continue
            _, nom, tk = _CRIPTO_INFO.get(cid, ("", cid, cid.upper()))
            precio = info.get("usd", 0)
            cambio = info.get("usd_24h_change") or 0
            flecha = "↑" if cambio >= 0 else "↓"
            sub.append(f"   {nom} ({tk}): ${precio:,.2f}  {flecha} {cambio:+.1f}%")
        if len(sub) > 1:
            partes.append("\n".join(sub))

    inf = _contexto_inflacion_texto()
    if inf:
        partes.append(f"\n📊 {inf}")

    watchers = db.listar_watchers_usuario(chat_id)
    if watchers:
        sub = [f"\n🔔 *Tus centinelas ({len(watchers)})*"]
        for w in watchers:
            cond = describir_condicion(w["op"], w["umbral"], w["clase"])
            sub.append(f"   {w['emoji']} {w['nombre']} — {cond}")
        partes.append("\n".join(sub))

    partes.append("\n_Que tengas un buen día 👋_")
    return "\n".join(partes)


def _enviar_briefing(chat_id: int) -> None:
    """Envía el resumen financiero (texto + gráfico del dólar) a un usuario."""
    datos_dolar = obtener_dolar()
    enviar_md(chat_id, _componer_briefing(chat_id, datos_dolar))
    if datos_dolar:
        try:
            bot.send_chat_action(chat_id, "upload_photo")
            bot.send_photo(chat_id, generar_grafico_dolar(datos_dolar))
        except Exception as e:
            logger.error("Error generando gráfico del briefing para chat %d: %s", chat_id, e)


def _activar_briefing(message: telebot.types.Message, hora: str) -> None:
    """Programa el resumen diario a una hora. Si ya pasó hoy, arranca mañana."""
    chat_id = message.chat.id
    ahora = datetime.now()
    ya_paso = ahora.strftime("%H:%M") >= hora
    db.guardar_briefing(chat_id, hora, ahora.strftime("%Y-%m-%d") if ya_paso else None)
    cuando = "mañana" if ya_paso else "hoy"
    enviar_md(
        chat_id,
        f"✅ Activé tu *resumen financiero diario* a las {hora}.\n"
        f"El primero te llega *{cuando}* a esa hora.\n\n"
        "Podés verlo ahora mismo con /briefing 👀",
        reply_to=message,
    )


def _despachar_briefing(message: telebot.types.Message, brief: dict) -> None:
    accion = brief["accion"]
    if accion == "activar":
        _activar_briefing(message, brief["hora"])
    elif accion == "desactivar":
        ok = db.eliminar_briefing(message.chat.id)
        bot.reply_to(message, "✅ Desactivé tu resumen diario." if ok else "No tenías un resumen diario activo.")
    else:  # "ahora"
        bot.send_chat_action(message.chat.id, "typing")
        _enviar_briefing(message.chat.id)


@bot.message_handler(commands=["briefing"])
def cmd_briefing(message: telebot.types.Message):
    partes = message.text.split()
    if len(partes) == 1:
        bot.send_chat_action(message.chat.id, "typing")
        _enviar_briefing(message.chat.id)
        return

    arg = partes[1].lower()
    if arg in ("off", "desactivar", "cancelar", "baja"):
        ok = db.eliminar_briefing(message.chat.id)
        bot.reply_to(message, "✅ Desactivé tu resumen diario." if ok else "No tenías un resumen diario activo.")
        return

    m = re.match(r"^(\d{1,2})(?::(\d{2}))?$", arg)
    if not m:
        bot.reply_to(
            message,
            "Usá:\n/briefing — verlo ahora\n/briefing HH:MM — activarlo diario\n/briefing off — desactivarlo",
        )
        return
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        bot.reply_to(message, "❌ Hora inválida. Ej: /briefing 09:00")
        return
    _activar_briefing(message, f"{h:02d}:{mi:02d}")


# ── Mensajes de texto ─────────────────────────────────────────────────────────

# Intenciones simples → handler de comando equivalente.
_INTENT_SIMPLES = {
    "grafico_dolar":  cmd_grafico_dolar,
    "dolar":          cmd_dolar,
    "grafico_cripto": cmd_grafico_cripto,
    "cripto":         cmd_cripto,
    "bcra":           cmd_bcra,
    "resumen":        cmd_resumen,
    "grafico_gastos": cmd_grafico_gastos,
    "comparar":       cmd_comparar,
    "mis_alertas":    cmd_mis_alertas,
    "mi_perfil":      cmd_mi_perfil,
    "mis_centinelas": cmd_mis_centinelas,
}


def _despachar_intencion(intencion: str, message: telebot.types.Message) -> None:
    """Ejecuta el comando correspondiente a una intención detectada.

    Los handlers de comandos parsean ``message.text`` para leer sus argumentos,
    así que reconstruimos el texto del comando equivalente (ej. "/convertir 500
    usd") y lo asignamos antes de invocarlos.
    """
    if intencion in _INTENT_SIMPLES:
        message.text = "/" + intencion
        _INTENT_SIMPLES[intencion](message)
        return

    if intencion.startswith("convertir:"):
        _, monto, moneda = intencion.split(":")
        message.text = f"/convertir {monto} {moneda}"
        cmd_convertir(message)
        return

    if intencion.startswith("plazo_fijo:"):
        partes = intencion.split(":")
        message.text = "/plazo_fijo " + " ".join(partes[1:])
        cmd_plazo_fijo(message)
        return

    if intencion.startswith("cripto_especifica:"):
        ticker = intencion.split(":")[1]
        message.text = f"/cripto {ticker}"
        cmd_cripto(message)
        return

    if intencion.startswith("grafico_cripto_especifica:"):
        ticker = intencion.split(":")[1]
        message.text = f"/grafico_cripto {ticker}"
        cmd_grafico_cripto(message)
        return

    if intencion.startswith("sentimiento:"):
        frase = intencion.split(":", 1)[1]
        message.text = f'/sentimiento "{frase}"'
        cmd_sentimiento(message)
        return


@bot.message_handler(content_types=["text"])
def handle_text_message(message: telebot.types.Message):
    chat_id = message.chat.id

    if is_rate_limited(chat_id):
        bot.reply_to(message, "⏳ Estás enviando mensajes muy rápido. Esperá un momento.")
        return

    worker = get_or_create_worker(chat_id)
    worker.agregar_mensaje(message.text)
    worker.devolucion()

    if not bank_data:
        bot.reply_to(message, "Error cargando los datos de los bancos. Intente más tarde.")
        return

    if message.text.startswith("/"):
        return

    # Centinela de precio: "avisame cuando el blue supere los 1500". Va antes de
    # detectar_intencion porque la frase menciona "dólar"/"bitcoin" y, si no,
    # la interceptaría la intención de cotización simple.
    watcher = parsear_watcher(message.text)
    if watcher:
        try:
            _crear_watcher_desde_texto(message, watcher)
        except Exception as e:
            logger.error("Error creando centinela para chat %d: %s", chat_id, e)
            bot.reply_to(message, "❌ No pude crear el centinela. Intentá de nuevo.")
        return

    # Cancelación de centinela en lenguaje natural ("cancelá el del blue").
    # Va antes de detectar_intencion porque la frase nombra el activo (dólar,
    # bitcoin) y, si no, la interceptaría la intención de cotización.
    cancelacion = parsear_cancelacion(message.text)
    if cancelacion:
        try:
            _cancelar_watcher_desde_texto(message, cancelacion)
        except Exception as e:
            logger.error("Error cancelando centinela para chat %d: %s", chat_id, e)
            bot.reply_to(message, "❌ No pude cancelar el centinela. Intentá de nuevo.")
        return

    # Briefing diario ("mandame el resumen diario a las 9").
    brief = parsear_briefing(message.text)
    if brief:
        try:
            _despachar_briefing(message, brief)
        except Exception as e:
            logger.error("Error en briefing para chat %d: %s", chat_id, e)
            bot.reply_to(message, "❌ No pude procesar el resumen. Intentá de nuevo.")
        return

    # Detección de intención en lenguaje natural (antes de cualquier llamada a la IA)
    intencion = detectar_intencion(message.text)
    if intencion:
        logger.info("Intención detectada para chat %d: %s", chat_id, intencion)
        try:
            _despachar_intencion(intencion, message)
        except Exception as e:
            logger.error("Error despachando intención %r para chat %d: %s", intencion, chat_id, e)
            bot.reply_to(message, "❌ Hubo un error al procesar tu pedido. Intentá de nuevo.")
        return

    # Detección de tarjeta (Luhn)
    patron_tarjeta = re.search(r"([\d\s-]{11,23})", message.text)
    if patron_tarjeta:
        mensaje_validacion_luhn(patron_tarjeta, bot, message)
        return

    user_input = filtrar_texto(message.text)

    # Contexto de imagen previa
    contexto_imagen = ultima_imagen_por_chat.get(chat_id)
    contexto = contexto_de_imagen(contexto_imagen, message, user_input, ultima_imagen_por_chat)
    if contexto:
        user_input = contexto

    bot.send_chat_action(chat_id, "typing")
    history = conversation_history[chat_id]
    user_input_enriquecido = _enriquecer_contexto(user_input)
    response = get_groq_response(user_input_enriquecido, bank_data, history)

    if response == RATE_LIMIT:
        bot.reply_to(message, MSG_RATE_LIMIT)
    elif response:
        add_to_history(chat_id, "user", user_input)
        add_to_history(chat_id, "assistant", response)
        bot.reply_to(message, response)
    else:
        bot.reply_to(
            message,
            "Lo siento, hubo un error al procesar tu consulta.\n"
            "Podés escribirnos a bankratebot@samsung.com para más información.",
        )


# ── Audio y foto ──────────────────────────────────────────────────────────────

# Frases con las que Whisper "rellena" audio en silencio/ruido (vienen de los
# subtítulos de YouTube con los que se entrenó). Si la transcripción es solo
# esto, casi seguro el usuario no dijo nada útil.
_TRANSCRIPCIONES_BASURA = (
    "gracias por ver el video",
    "gracias por ver el vídeo",
    "gracias por ver",
    "subtitulos realizados por",
    "subtítulos realizados por",
    "subtitulado por",
    "amara.org",
    "comunidad de amara",
    "no olvides suscribirte",
    "suscribete al canal",
    "suscríbete al canal",
)


def _transcripcion_es_ruido(texto: str) -> bool:
    t = texto.strip().lower()
    return any(frase in t for frase in _TRANSCRIPCIONES_BASURA)


@bot.message_handler(content_types=["voice"])
def handle_voice_message(message: telebot.types.Message):
    chat_id = message.chat.id

    if is_rate_limited(chat_id):
        bot.reply_to(message, "⏳ Estás enviando mensajes muy rápido. Esperá un momento.")
        return

    if not bank_data:
        bot.reply_to(message, "Error cargando datos de bancos. Intente más tarde.")
        return

    bot.send_chat_action(chat_id, "typing")

    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    temp_file = f"temp_voice_{chat_id}.ogg"

    with open(temp_file, "wb") as f:
        f.write(downloaded_file)

    transcripcion_cruda = transcribe_voice_with_groq(temp_file)
    os.remove(temp_file)

    if not transcripcion_cruda or not transcripcion_cruda.strip():
        bot.reply_to(message, "No pude transcribir el audio. Probá de nuevo.")
        return

    # Whisper alucina frases de subtítulos de YouTube cuando el audio está en
    # silencio, es muy corto o tiene ruido ("gracias por ver el video",
    # "subtítulos por Amara.org"...). Las descartamos en vez de mandárselas al LLM.
    if _transcripcion_es_ruido(transcripcion_cruda):
        logger.info("Audio descartado como ruido/alucinación: %r", transcripcion_cruda)
        bot.reply_to(
            message,
            "🤔 No te llegué a escuchar bien (el audio salió muy corto o con ruido).\n"
            "Probá de nuevo hablando claro y un poco más fuerte 🎤",
        )
        return

    # Le mostramos al usuario qué entendió: la transcripción es lossy (Whisper
    # puede alucinar con audio corto o con ruido) y sin esto es imposible saber
    # por qué un pedido por voz no se interpretó como esperábamos.
    bot.reply_to(message, f"🎤 Entendí: «{transcripcion_cruda.strip()}»")

    # Centinela de precio dictado por voz. Se parsea sobre la transcripción
    # CRUDA (igual que el texto usa message.text sin filtrar), porque
    # filtrar_texto elimina stopwords ("cuando", "el", "de"...) y mutila la frase.
    watcher = parsear_watcher(transcripcion_cruda)
    if watcher:
        message.text = transcripcion_cruda
        try:
            _crear_watcher_desde_texto(message, watcher)
        except Exception as e:
            logger.error("Error creando centinela por voz para chat %d: %s", chat_id, e)
            bot.reply_to(message, "❌ No pude crear el centinela. Intentá de nuevo.")
        return

    cancelacion = parsear_cancelacion(transcripcion_cruda)
    if cancelacion:
        try:
            _cancelar_watcher_desde_texto(message, cancelacion)
        except Exception as e:
            logger.error("Error cancelando centinela por voz para chat %d: %s", chat_id, e)
            bot.reply_to(message, "❌ No pude cancelar el centinela. Intentá de nuevo.")
        return

    brief = parsear_briefing(transcripcion_cruda)
    if brief:
        message.text = transcripcion_cruda
        try:
            _despachar_briefing(message, brief)
        except Exception as e:
            logger.error("Error en briefing por voz para chat %d: %s", chat_id, e)
            bot.reply_to(message, "❌ No pude procesar el resumen. Intentá de nuevo.")
        return

    # Intención en lenguaje natural por voz (cotizaciones, listar centinelas,
    # gráficos...), igual que el flujo de texto. Los handlers leen message.text.
    message.text = transcripcion_cruda
    intencion = detectar_intencion(transcripcion_cruda)
    if intencion:
        logger.info("Intención por voz para chat %d: %s", chat_id, intencion)
        try:
            _despachar_intencion(intencion, message)
        except Exception as e:
            logger.error("Error despachando intención por voz %r para chat %d: %s", intencion, chat_id, e)
            bot.reply_to(message, "❌ Hubo un error al procesar tu pedido. Intentá de nuevo.")
        return

    # Para el resto (consulta libre a la IA) sí usamos el texto filtrado.
    transcription = filtrar_texto(transcripcion_cruda)

    worker = get_or_create_worker(chat_id)
    worker.agregar_mensaje(transcription)
    worker.devolucion()

    history = conversation_history[chat_id]
    response = get_groq_response(transcription, bank_data, history)

    if response == RATE_LIMIT:
        bot.reply_to(message, MSG_RATE_LIMIT)
    elif response:
        add_to_history(chat_id, "user", transcription)
        add_to_history(chat_id, "assistant", response)
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "Error al procesar tu consulta.")


@bot.message_handler(content_types=["photo"])
def handle_foto(message: telebot.types.Message):
    chat_id = message.chat.id

    if is_rate_limited(chat_id):
        bot.reply_to(message, "⏳ Estás enviando mensajes muy rápido. Esperá un momento.")
        return

    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}"

        bot.reply_to(message, "🧠 Analizando la imagen...")
        descripcion = describir_imagen(file_url)
        ultima_imagen_por_chat[chat_id] = descripcion

        if any(p in descripcion.lower() for p in ["comprobante", "transferencia", "pago"]):
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
                bot.send_message(chat_id, resumen, parse_mode="Markdown")

            except json.JSONDecodeError:
                bot.reply_to(message, "⚠️ No pude interpretar los datos del comprobante.")
        else:
            bot.reply_to(message, f"🖼️ Descripción:\n\n{descripcion}")

    except Exception as e:
        logger.error("Error al procesar foto de chat %d: %s", chat_id, e)
        bot.reply_to(message, f"❌ Error al procesar la imagen: {str(e)}")


# ── Callbacks del comparador ──────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: call.data.startswith("cmp:"))
def callback_comparador(call: telebot.types.CallbackQuery):
    chat_id = call.message.chat.id
    data = call.data
    bancos = bank_data["bank_data"]

    def editar(texto, markup=None):
        bot.edit_message_text(
            texto, chat_id, call.message.message_id,
            reply_markup=markup, parse_mode="Markdown",
        )

    if data == "cmp:menu":
        comparador_state.pop(chat_id, None)
        editar("🏦 *Comparador de bancos*\n¿Qué querés buscar?", menu_principal())

    elif data == "cmp:baratos":
        editar(resultado_baratos(bancos))

    elif data == "cmp:gratis":
        editar(resultado_gratis(bancos))

    elif data == "cmp:prov":
        editar("📍 *Seleccioná una provincia:*", menu_provincias())

    elif data.startswith("cmp:p:"):
        code = data.split("cmp:p:")[1]
        editar(resultado_provincia(bancos, code))

    elif data == "cmp:dos":
        comparador_state[chat_id] = {"paso": 1}
        editar("⚖️ *Seleccioná el primer banco:*", menu_bancos(bancos))

    elif data.startswith("cmp:b:"):
        idx = int(data.split("cmp:b:")[1])
        estado = comparador_state.get(chat_id, {})

        if estado.get("paso") == 1:
            comparador_state[chat_id] = {"paso": 2, "banco1": idx}
            editar(
                f"✅ *{bancos[idx]['bank']}* seleccionado.\n\nAhora elegí el segundo banco:",
                menu_bancos(bancos, excluir_idx=idx),
            )
        elif estado.get("paso") == 2:
            idx1 = estado["banco1"]
            comparador_state.pop(chat_id, None)
            editar(resultado_comparacion(bancos, idx1, idx))
        else:
            bot.answer_callback_query(call.id, "Usá /comparar para empezar.")

    bot.answer_callback_query(call.id)


# ── Callbacks del menú de inicio ─────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: call.data.startswith("menu:"))
def callback_menu(call: telebot.types.CallbackQuery):
    chat_id = call.message.chat.id
    accion = call.data.split("menu:")[1]
    bot.answer_callback_query(call.id)

    if accion == "dolar":
        bot.send_chat_action(chat_id, "typing")
        datos = obtener_dolar()
        bot.send_message(chat_id,
            formatear_dolar(datos) if datos else "❌ No pude obtener las cotizaciones.",
            parse_mode="Markdown")

    elif accion == "cripto":
        bot.send_chat_action(chat_id, "typing")
        datos = obtener_cripto(TOP_5)
        bot.send_message(chat_id,
            formatear_cripto(datos, TOP_5) if datos else "❌ No pude obtener los precios.",
            parse_mode="Markdown")

    elif accion == "bcra":
        bot.send_chat_action(chat_id, "typing")
        bot.send_message(chat_id, obtener_bcra(), parse_mode="Markdown")

    elif accion == "comparar":
        from apis.comparador import menu_principal
        bot.send_message(chat_id, "🏦 *Comparador de bancos*\n¿Qué querés buscar?",
                         reply_markup=menu_principal(), parse_mode="Markdown")

    elif accion == "convertir":
        bot.send_message(chat_id,
            "💱 *Convertidor de moneda*\n\n"
            "Usá el comando:\n"
            "/convertir 500 usd  →  cuánto son en ARS\n"
            "/convertir 100000 ars  →  cuántos USD podés comprar",
            parse_mode="Markdown")

    elif accion == "plazo_fijo":
        bot.send_message(chat_id,
            "🏦 *Simulador de Plazo Fijo*\n\n"
            "Usá el comando:\n"
            "/plazo_fijo 100000 30  →  simulación a TNA de mercado\n"
            "/plazo_fijo 100000 30 97.5  →  con TNA específica",
            parse_mode="Markdown")

    elif accion == "ayuda":
        cmd_ayuda(call.message)


# ── Callbacks de botones ──────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call: telebot.types.CallbackQuery):
    chat_id = call.message.chat.id
    user_input = filtrar_texto(call.data)
    history = conversation_history[chat_id]
    bot.send_chat_action(chat_id, "typing")
    respuesta = get_groq_response(user_input, bank_data, history)
    if respuesta == RATE_LIMIT:
        bot.send_message(chat_id, MSG_RATE_LIMIT)
        return
    if respuesta:
        add_to_history(chat_id, "user", user_input)
        add_to_history(chat_id, "assistant", respuesta)
    bot.send_message(chat_id, respuesta or "Error al procesar tu consulta.")


def _chequear_watchers():
    """Revisa los centinelas de precio contra los valores en vivo.

    Cada centinela es de un solo disparo: una vez que se cumple, se notifica
    con su gráfico y se elimina para no repetir el aviso.
    """
    watchers = db.listar_watchers()
    if not watchers:
        return
    precios = _snapshot_precios(watchers)
    for w in watchers:
        precio = precios.get((w["clase"], w["activo"]))
        if precio is None:
            continue
        if cumple(w["op"], precio, w["umbral"]):
            try:
                _notificar_disparo(w["codigo_chat"], w, precio)
            except Exception as e:
                logger.error("Error notificando centinela %d: %s", w["id"], e)
            finally:
                db.eliminar_watcher(w["id"])


def _chequear_briefings():
    """Envía los resúmenes diarios cuya hora llegó y no se mandaron hoy."""
    briefings = db.listar_briefings()
    if not briefings:
        return
    ahora = datetime.now()
    hoy = ahora.strftime("%Y-%m-%d")
    hhmm = ahora.strftime("%H:%M")
    for b in briefings:
        if b["ultimo_envio"] == hoy or hhmm < b["hora"]:
            continue
        try:
            _enviar_briefing(b["codigo_chat"])
        except Exception as e:
            logger.error("Error enviando briefing a %d: %s", b["codigo_chat"], e)
        finally:
            db.marcar_briefing_enviado(b["codigo_chat"], hoy)


def _scheduler():
    while True:
        try:
            for alerta in db.obtener_alertas_pendientes():
                try:
                    bot.send_message(
                        alerta["codigo_chat"],
                        f"⏰ *Recordatorio:*\n{alerta['mensaje']}",
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    logger.error("Error enviando alerta %d: %s", alerta["id"], e)
                finally:
                    if alerta["recurrente"] and alerta["dia_mes"]:
                        db.reprogramar_alerta(alerta["id"], proxima_fecha_mensual(alerta["dia_mes"]))
                    else:
                        db.eliminar_alerta(alerta["id"])
        except Exception as e:
            logger.error("Error en scheduler (alertas): %s", e)

        try:
            _chequear_watchers()
        except Exception as e:
            logger.error("Error en scheduler (centinelas): %s", e)

        try:
            _chequear_briefings()
        except Exception as e:
            logger.error("Error en scheduler (briefings): %s", e)

        time.sleep(30)


# ── Main loop ─────────────────────────────────────────────────────────────────

_detener = False


def _handle_sigint(signum, frame):
    # telebot atrapa el KeyboardInterrupt internamente y bot.polling() retorna
    # sin propagar la excepción, así que no alcanza con un except. Capturamos la
    # señal nosotros, marcamos la bandera y frenamos el polling explícitamente.
    global _detener
    _detener = True
    logger.info("Ctrl+C recibido. Cerrando el bot...")
    bot.stop_polling()


if __name__ == "__main__":
    if not bank_data:
        logger.critical("No se pudo cargar dataset.json. El bot no se iniciará.")
    else:
        signal.signal(signal.SIGINT, _handle_sigint)
        threading.Thread(target=_scheduler, daemon=True).start()
        logger.info("Bot bancario iniciado con Groq, Whisper y comandos de usuario 💬")
        while not _detener:
            try:
                bot.polling(none_stop=True, interval=0, timeout=20)
            except Exception as e:
                if _detener:
                    break
                logger.error("Error en polling: %s. Reiniciando en 5 segundos...", e)
                time.sleep(5)
        logger.info("Bot detenido. ¡Hasta luego! 👋")
