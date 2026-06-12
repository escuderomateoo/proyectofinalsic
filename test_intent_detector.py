"""Tests de intent_detector.

Cubren, para cada intención, variantes con tildes, sin tildes, mayúsculas y
con errores ortográficos leves. Se ejecutan de forma aislada porque
``intent_detector`` no depende de ``main.py`` ni de la red.

    pytest test_intent_detector.py -v
"""

import pytest

from intent_detector import detectar_intencion


@pytest.mark.parametrize("texto,esperado", [
    # ── grafico_dolar ──────────────────────────────────────────────────────
    ("pasame el gráfico del dólar", "grafico_dolar"),
    ("mandame un grafico del dolar", "grafico_dolar"),
    ("quiero ver el grafico del dolar", "grafico_dolar"),
    ("mostrá el gráfico de los tipos de cambio", "grafico_dolar"),
    ("GRÁFICO DEL DÓLAR", "grafico_dolar"),
    ("graficá el dólar", "grafico_dolar"),

    # ── dolar ──────────────────────────────────────────────────────────────
    ("a cuánto está el dólar", "dolar"),
    ("cotización del dólar", "dolar"),
    ("precio del dolar hoy", "dolar"),
    ("como esta el dolar", "dolar"),
    ("cuánto vale el dólar", "dolar"),
    ("pasame el dolar", "dolar"),
    ("dólar hoy", "dolar"),
    ("tipos de cambio", "dolar"),

    # ── grafico_cripto (genérico, sin coin puntual) ────────────────────────
    ("pasame el gráfico de cripto", "grafico_cripto"),
    ("mostrá el gráfico de las criptos", "grafico_cripto"),
    ("graficá las criptomonedas", "grafico_cripto"),
    ("historial de las criptos", "grafico_cripto"),
    ("EVOLUCIÓN DE LAS CRIPTOS", "grafico_cripto"),

    # ── cripto (genérico) ──────────────────────────────────────────────────
    ("precio de las criptos", "cripto"),
    ("cómo están las criptomonedas", "cripto"),
    ("cotización de las criptos", "cripto"),
    ("a cuánto están las criptos", "cripto"),
    ("PRECIO DE LAS CRIPTOMONEDAS", "cripto"),

    # ── cripto_especifica ──────────────────────────────────────────────────
    ("precio del bitcoin", "cripto_especifica:btc"),
    ("cómo está el btc", "cripto_especifica:btc"),
    ("cuánto vale bitcoin", "cripto_especifica:btc"),
    ("cotizacion ethereum", "cripto_especifica:eth"),
    ("a cuánto está el ETH", "cripto_especifica:eth"),
    ("precio de solana", "cripto_especifica:sol"),
    ("cuánto vale doge", "cripto_especifica:doge"),

    # ── grafico_cripto_especifica ──────────────────────────────────────────
    ("gráfico de ethereum", "grafico_cripto_especifica:eth"),
    ("historial de eth", "grafico_cripto_especifica:eth"),
    ("evolución de ethereum", "grafico_cripto_especifica:eth"),
    ("gráfico de bitcoin", "grafico_cripto_especifica:btc"),
    ("graficá bitcoin", "grafico_cripto_especifica:btc"),

    # ── bcra ───────────────────────────────────────────────────────────────
    ("inflación argentina", "bcra"),
    ("datos del bcra", "bcra"),
    ("reservas del bcra", "bcra"),
    ("tasa de política monetaria", "bcra"),
    ("como esta la inflacion", "bcra"),
    ("indicadores macroeconómicos", "bcra"),
    ("inflacion mensual", "bcra"),

    # ── resumen ────────────────────────────────────────────────────────────
    ("resumen de mis gastos", "resumen"),
    ("cómo voy con los gastos", "resumen"),
    ("mis carpetas", "resumen"),
    ("mostrame los gastos", "resumen"),
    ("cuánto tengo en cada carpeta", "resumen"),
    ("mis finanzas", "resumen"),

    # ── grafico_gastos ─────────────────────────────────────────────────────
    ("gráfico de mis gastos", "grafico_gastos"),
    ("torta de gastos", "grafico_gastos"),
    ("distribución de gastos", "grafico_gastos"),
    ("graficá mis gastos", "grafico_gastos"),
    ("mostrá el gráfico de gastos", "grafico_gastos"),

    # ── comparar ───────────────────────────────────────────────────────────
    ("comparar bancos", "comparar"),
    ("quiero comparar bancos", "comparar"),
    ("qué banco es mejor", "comparar"),
    ("comparativa de bancos", "comparar"),
    ("ayudame a elegir banco", "comparar"),

    # ── mis_alertas ────────────────────────────────────────────────────────
    ("mis recordatorios", "mis_alertas"),
    ("qué alertas tengo", "mis_alertas"),
    ("mostrame los recordatorios", "mis_alertas"),
    ("mis alertas activas", "mis_alertas"),
    ("MIS ALERTAS", "mis_alertas"),

    # ── mis_centinelas ─────────────────────────────────────────────────────
    ("mis centinelas", "mis_centinelas"),
    ("mis alertas de precio", "mis_centinelas"),
    ("mostrame mis centinelas", "mis_centinelas"),
    ("alertas de precio", "mis_centinelas"),
    # Regresión: Whisper transcribe "sentinela" con S (seseo rioplatense).
    ("¿cuáles son mis sentinelas?", "mis_centinelas"),
    ("mis sentinelas", "mis_centinelas"),

    # ── mi_perfil ──────────────────────────────────────────────────────────
    ("mi perfil de sentimiento", "mi_perfil"),
    ("cómo está mi sentimiento", "mi_perfil"),
    ("mi historial emocional", "mi_perfil"),
    ("mi perfil", "mi_perfil"),
    ("MI PERFIL", "mi_perfil"),

    # ── convertir (con parámetros) ─────────────────────────────────────────
    ("convertí 500 dólares", "convertir:500:usd"),
    ("cuántos pesos son 500 usd", "convertir:500:usd"),
    ("pasame 500 usd a pesos", "convertir:500:usd"),
    ("convertir 500 dólares a pesos", "convertir:500:usd"),
    ("convertí 100000 pesos a dólares", "convertir:100000:ars"),
    ("cuantos pesos son 100.000 ars", "convertir:100000:ars"),
    ("pasame 100000 pesos a dolares", "convertir:100000:ars"),
    ("cuántos dólares son 100 mil pesos", "convertir:100000:ars"),

    # ── plazo_fijo (con parámetros) ────────────────────────────────────────
    ("simulá un plazo fijo de 50000 por 30 días", "plazo_fijo:50000:30"),
    ("cuánto gano con 100000 en un plazo fijo de 60 días", "plazo_fijo:100000:60"),
    ("rendimiento de un plazo fijo de 200000 a 30 días", "plazo_fijo:200000:30"),
    ("plazo fijo de 50000 a 30 dias", "plazo_fijo:50000:30"),
    ("plazo fijo de 100000 por 30 días al 97.5%", "plazo_fijo:100000:30:97.5"),

    # ── sentimiento (con parámetros) ───────────────────────────────────────
    ("analizá el sentimiento de: estoy muy feliz hoy", "sentimiento:estoy muy feliz hoy"),
    ("qué sentimiento tiene: me siento mal", "sentimiento:me siento mal"),
    ("analiza el sentimiento de me siento cansado", "sentimiento:me siento cansado"),

    # ── regresiones de uso real (errores ortográficos / fraseo natural) ─────
    ("me pasas el grafico de etherium ?", "grafico_cripto_especifica:eth"),
    ("historial de etherium", "grafico_cripto_especifica:eth"),
    ("precio de etherium", "cripto_especifica:eth"),
    ("me quiero comprar unas zapatillas y estan en 500 dolares, cuanto seria en pesos argentinos?",
     "convertir:500:usd"),
    ("cuanto es 500 dolares en pesos", "convertir:500:usd"),
    ("ayudame a elegit un banco", "comparar"),
    ("me comparas entre banco cordoba y bbva?", "comparar"),
    ("me pasas grafico de bircoin?", "grafico_cripto_especifica:btc"),
    ("precio de bircoin", "cripto_especifica:btc"),
    ("Quiero comprar unas zapatillas a 200 dólares, cuánto sería en pesos argentinos?",
     "convertir:200:usd"),
    ("200 dólares en pesos?", "convertir:200:usd"),
    ("que es el bitcoin?", None),

    # ── sin intención conocida ─────────────────────────────────────────────
    ("esto es un mensaje sin intención conocida xyz", None),
    ("hola, todo bien?", None),
    ("todo bien??", None),
    ("buen dia!", None),
    ("", None),
])
def test_detectar_intencion(texto, esperado):
    assert detectar_intencion(texto) == esperado


def test_grafico_dolar_tiene_prioridad_sobre_dolar():
    assert detectar_intencion("quiero el gráfico del dólar") == "grafico_dolar"


def test_cripto_especifica_tiene_prioridad_sobre_generica():
    # Nombrar un coin puntual gana sobre la mención genérica "cripto".
    assert detectar_intencion("precio de la cripto bitcoin") == "cripto_especifica:btc"


def test_convertir_anclado_al_monto_no_al_objetivo():
    # "cuántos pesos son 500 usd": el monto de origen es 500 usd, no pesos.
    assert detectar_intencion("cuántos pesos son 500 usd") == "convertir:500:usd"


def test_sol_sin_contexto_no_es_cripto():
    # "sol" debe requerir contexto de precio para interpretarse como Solana.
    assert detectar_intencion("hoy salió el sol") is None
