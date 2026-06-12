"""Detección de intención en lenguaje natural para BankRanks Argentina.

Este módulo traduce frases naturales en español rioplatense al nombre del
comando que debería ejecutarse (el mismo nombre que usa ``main.py``, sin la
``/``). Permite que el usuario escriba "a cuánto está el dólar" en lugar de
``/dolar``.

Diseño:
    * Módulo PURO: no importa nada de ``main.py`` ni del resto del proyecto,
      para poder testearlo de forma aislada con pytest.
    * Todo el matching es por regex case-insensitive y con tildes opcionales
      (``d[oó]lar`` matchea tanto "dólar" como "dolar").
    * Las intenciones con parámetros (convertir, plazo fijo, cripto puntual,
      sentimiento) tienen prioridad sobre las genéricas. "grafico_dolar" tiene
      prioridad sobre "dolar" y "grafico_cripto" sobre "cripto".

La función pública es :func:`detectar_intencion`.
"""

from __future__ import annotations

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)


# ── Helpers de normalización ──────────────────────────────────────────────────

def _quitar_tildes(texto: str) -> str:
    """Devuelve ``texto`` sin tildes (para comparaciones laxas internas)."""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _norm_monto(crudo: str, multiplicador: str | None = None) -> int:
    """Normaliza un número con separadores de miles a entero.

    Soporta puntos o comas como separadores de miles ("100.000" -> 100000) y
    multiplicadores en palabra ("100 mil" -> 100000).
    """
    valor = int(crudo.replace(".", "").replace(",", ""))
    if multiplicador:
        m = _quitar_tildes(multiplicador.lower())
        if m.startswith("mil"):
            valor *= 1_000
        elif m.startswith("millon") or m.startswith("palo"):
            valor *= 1_000_000
    return valor


# ── Tickers de criptomonedas ───────────────────────────────────────────────────
# Cada entrada mapea el ticker normalizado a un patrón que cubre nombre completo
# y abreviatura. Se usan \b para evitar falsos positivos dentro de otras palabras.
_TICKERS: list[tuple[str, str]] = [
    # Cubre errores ortográficos frecuentes: bircoin, bitcoing, bitcon.
    ("btc",  r"\b(?:bitcoin|bitcoint|bitcoing|bircoin|bitcon|btc)\b"),
    # Cubre errores ortográficos frecuentes: etherium, etereum, ethereum.
    ("eth",  r"\b(?:ethereum|etherium|ethereum|etereum|ether|eth)\b"),
    ("sol",  r"\b(?:solana|sol)\b"),
    ("bnb",  r"\b(?:binance|bnb)\b"),
    ("ada",  r"\b(?:cardano|ada)\b"),
    ("xrp",  r"\b(?:ripple|xrp)\b"),
    ("doge", r"\b(?:dogecoin|doge)\b"),
    ("usdt", r"\b(?:tether|usdt)\b"),
]


def _detectar_ticker(texto: str) -> str | None:
    """Devuelve el primer ticker (btc, eth, ...) mencionado, o ``None``."""
    for ticker, patron in _TICKERS:
        if re.search(patron, texto, re.IGNORECASE):
            return ticker
    return None


# ── Patrones de palabras clave ─────────────────────────────────────────────────
# "Gráfico" y sinónimos. Cubre: gráfico/grafico, graficá/grafica/graficar,
# historial, evolución y (para gastos) torta/distribución.
_RE_GRAFICO = re.compile(
    r"gr[áa]fic|grafic[aá]r?|graficar|historial|evoluci[óo]n", re.IGNORECASE
)

# Contexto que confirma que una mención de moneda/cripto es una consulta de
# precio (evita que "salió el sol" se interprete como la cripto SOL).
_RE_CONTEXTO_CRIPTO = re.compile(
    r"precio|cotizaci[óo]n|cu[áa]nto\s+vale|c[óo]mo\s+est[áa]|a\s+cu[áa]nto|"
    r"gr[áa]fic|historial|evoluci[óo]n|cripto|crypto|criptomoneda|valor",
    re.IGNORECASE,
)

# Cripto genérica (sin un coin puntual): "criptos", "criptomonedas", "crypto".
_RE_CRIPTO_GENERICA = re.compile(
    r"\bcripto\w*|\bcrypto\b|criptomoneda", re.IGNORECASE
)

# Dólar / tipos de cambio.
_RE_DOLAR = re.compile(r"d[óo]lar|tipos?\s+de\s+cambio", re.IGNORECASE)

# BCRA / inflación / macro.
_RE_BCRA = re.compile(
    r"inflaci[óo]n|\bbcra\b|reservas|tasa\s+de\s+pol[íi]tica\s+monetaria|"
    r"pol[íi]tica\s+monetaria|indicadores?\s+macro|\bindec\b",
    re.IGNORECASE,
)

# Gráfico de gastos (torta / distribución de gastos).
_RE_GRAFICO_GASTOS = re.compile(
    r"(?:gr[áa]fic\w*|graficá|grafica|torta|distribuci[óo]n)[^.\n]*\bgastos?\b",
    re.IGNORECASE,
)

# Resumen de gastos / carpetas / finanzas.
_RE_RESUMEN = re.compile(
    r"resumen\s+de\s+(?:mis\s+)?gastos|mis\s+gastos|c[óo]mo\s+voy\s+con\s+los\s+gastos|"
    r"mis\s+carpetas|mostr[aá]\w*\s+(?:los\s+|me\s+)?(?:los\s+)?gastos|"
    r"cu[áa]nto\s+tengo\s+en\s+cada\s+carpeta|mis\s+finanzas|\blos\s+gastos\b",
    re.IGNORECASE,
)

# Comparar bancos. Acepta palabras intermedias ("comparas entre banco X y Y")
# y variantes/typos de "elegir" (elegir, elegit, elejir).
_RE_COMPARAR = re.compile(
    r"compar\w*.*\bbancos?\b|"
    r"qu[ée]\s+banco\s+(?:es\s+)?mejor|"
    r"mejor\s+banco|"
    r"ele[gj]\w*\s+(?:un\s+)?banco",
    re.IGNORECASE,
)

# Centinelas de precio activos. Se chequea ANTES que mis_alertas porque
# "mis alertas de precio" contiene "mis alertas".
_RE_MIS_CENTINELAS = re.compile(
    r"mis\s+[cs]entinelas|mis\s+alertas\s+de\s+precio|alertas?\s+de\s+precio|"
    r"mis\s+watchers",
    re.IGNORECASE,
)

# Recordatorios / alertas activas.
_RE_MIS_ALERTAS = re.compile(
    r"mis\s+recordatorios|mis\s+alertas|alertas\s+activas|"
    r"(?:qu[ée]\s+)?alertas\s+tengo|(?:los\s+)?recordatorios",
    re.IGNORECASE,
)

# Perfil de sentimiento propio.
_RE_MI_PERFIL = re.compile(
    r"mi\s+perfil|mi\s+sentimiento|mi\s+historial\s+emocional|"
    r"c[óo]mo\s+est[áa]\s+mi\s+sentimiento",
    re.IGNORECASE,
)

# Análisis de sentimiento de una frase: extrae el texto a analizar.
_RE_SENTIMIENTO = re.compile(
    r"(?:analiz[áa]r?\s+(?:el\s+)?sentimiento\s+de|"
    r"qu[ée]\s+sentimiento\s+tiene)\s*:?\s*(.+)",
    re.IGNORECASE | re.DOTALL,
)

# Conversión de moneda: señales de intención de conversión. Cubre verbos
# explícitos (convertí, pasame, cambiar) y fraseos naturales como
# "cuánto sería en pesos" o un objetivo del tipo "a/en pesos|dólares".
_RE_CONVERTIR_TRIGGER = re.compile(
    r"convert[ií]r?|pas[aá](?:me|r)?\b|cambiar|"
    r"cu[áa]ntos?\s+(?:pesos|d[óo]lares|usd|ars)\s+son|"
    r"cu[áa]nto\s+(?:ser[íi]a|es|sale|da|queda|vale|equivale)|"
    r"\b(?:a|en)\s+(?:pesos|d[óo]lares|ars|usd)\b",
    re.IGNORECASE,
)
# Monto + unidad (la unidad pegada al número define la moneda de origen).
_RE_CONVERTIR_MONTO = re.compile(
    r"(\d[\d.,]*)\s*(mil(?:lones?|[oó]n)?|palos?)?\s*"
    r"(d[óo]lar(?:es)?|usd|u\$s|pesos?|ars|\$)",
    re.IGNORECASE,
)

# Plazo fijo.
_RE_PLAZO_FIJO = re.compile(r"plazo\s*fijo", re.IGNORECASE)
_RE_PF_DIAS = re.compile(r"(\d[\d.,]*)\s*d[íi]as?", re.IGNORECASE)
_RE_PF_NUM = re.compile(r"\d[\d.,]*")
_RE_PF_TASA = re.compile(
    r"(?:tna|tasa|al?)\s*(?:del?\s*)?(\d+(?:[.,]\d+)?)\s*%|(\d+(?:[.,]\d+)?)\s*%",
    re.IGNORECASE,
)


# ── Detectores con parámetros ──────────────────────────────────────────────────

def _detectar_sentimiento(texto: str) -> str | None:
    """Detecta "analizá el sentimiento de: <frase>" y extrae la frase."""
    m = _RE_SENTIMIENTO.search(texto)
    if not m:
        return None
    frase = m.group(1).strip().strip('"').strip()
    if not frase:
        return None
    return f"sentimiento:{frase}"


def _detectar_convertir(texto: str) -> str | None:
    """Detecta una conversión de moneda y extrae monto + moneda de origen.

    La moneda devuelta ("usd" o "ars") es la del monto de origen (la unidad que
    aparece pegada al número), sin importar el orden de la frase.
    """
    m = _RE_CONVERTIR_MONTO.search(texto)
    if not m:
        return None
    if not _RE_CONVERTIR_TRIGGER.search(texto):
        return None

    monto = _norm_monto(m.group(1), m.group(2))
    unidad = _quitar_tildes(m.group(3).lower())
    if unidad.startswith("dolar") or unidad in ("usd", "u$s"):
        moneda = "usd"
    else:  # pesos, peso, ars, $
        moneda = "ars"
    return f"convertir:{monto}:{moneda}"


def _detectar_plazo_fijo(texto: str) -> str | None:
    """Detecta un simulador de plazo fijo y extrae monto, días y TNA opcional."""
    if not _RE_PLAZO_FIJO.search(texto):
        return None

    dias_m = _RE_PF_DIAS.search(texto)
    if not dias_m:
        return None
    dias = _norm_monto(dias_m.group(1))

    # Tasa explícita (ej. "97.5%" o "tna 97.5"), si la hay.
    tasa = None
    tasa_m = _RE_PF_TASA.search(texto)
    if tasa_m:
        tasa = (tasa_m.group(1) or tasa_m.group(2)).replace(",", ".")

    # El monto es el primer número que no sea el de los días ni el de la tasa.
    spans_excluidos = [dias_m.span(1)]
    if tasa_m:
        spans_excluidos.append(tasa_m.span())

    monto = None
    for num_m in _RE_PF_NUM.finditer(texto):
        if any(num_m.start() >= s and num_m.end() <= e for s, e in spans_excluidos):
            continue
        if num_m.start() == dias_m.start(1):
            continue
        monto = _norm_monto(num_m.group(0))
        break

    if monto is None:
        return None

    if tasa is not None:
        return f"plazo_fijo:{monto}:{dias}:{tasa}"
    return f"plazo_fijo:{monto}:{dias}"


def _detectar_cripto(texto: str) -> str | None:
    """Bloque cripto: resuelve coin puntual vs genérica, con o sin gráfico.

    Prioridad (regla 1 y 3): coin puntual con parámetro > cripto genérica, y
    gráfico > consulta de precio simple.
    """
    es_grafico = bool(_RE_GRAFICO.search(texto))
    ticker = _detectar_ticker(texto)

    if ticker and _RE_CONTEXTO_CRIPTO.search(texto):
        if es_grafico:
            return f"grafico_cripto_especifica:{ticker}"
        return f"cripto_especifica:{ticker}"

    if _RE_CRIPTO_GENERICA.search(texto):
        if es_grafico:
            return "grafico_cripto"
        return "cripto"

    return None


# ── Función principal ──────────────────────────────────────────────────────────

def detectar_intencion(texto: str) -> str | None:
    """Devuelve el comando a ejecutar (sin "/") para ``texto``, o ``None``.

    El orden de evaluación implementa las reglas de prioridad:
        1. Intenciones con parámetros (sentimiento, convertir, plazo_fijo,
           cripto puntual) antes que las genéricas.
        2. ``grafico_dolar`` antes que ``dolar``.
        3. ``grafico_cripto`` antes que ``cripto``.
        4. Si nada matchea, ``None``.
    """
    if not texto or not texto.strip():
        return None

    t = texto.strip()

    # 1) Intenciones con parámetros de mayor especificidad.
    for detector in (_detectar_sentimiento, _detectar_convertir, _detectar_plazo_fijo):
        resultado = detector(t)
        if resultado:
            return resultado

    # 2) Dólar: gráfico tiene prioridad sobre la cotización simple.
    hay_dolar = bool(_RE_DOLAR.search(t))
    if hay_dolar and _RE_GRAFICO.search(t):
        _avisar_ambiguedad(t, "grafico_dolar")
        return "grafico_dolar"
    if hay_dolar:
        _avisar_ambiguedad(t, "dolar")
        return "dolar"

    # 3) Cripto (puntual o genérica, con o sin gráfico).
    cripto = _detectar_cripto(t)
    if cripto:
        return cripto

    # 4) Resto de intenciones genéricas (gráfico de gastos antes que resumen).
    if _RE_BCRA.search(t):
        return "bcra"
    if _RE_GRAFICO_GASTOS.search(t):
        return "grafico_gastos"
    if _RE_RESUMEN.search(t):
        return "resumen"
    if _RE_COMPARAR.search(t):
        return "comparar"
    if _RE_MIS_CENTINELAS.search(t):
        return "mis_centinelas"
    if _RE_MIS_ALERTAS.search(t):
        return "mis_alertas"
    if _RE_MI_PERFIL.search(t):
        return "mi_perfil"

    return None


def _avisar_ambiguedad(texto: str, elegido: str) -> None:
    """Loguea un warning si el texto matchea dominios mutuamente excluyentes.

    No cambia el resultado (la prioridad ya lo resolvió), solo deja traza para
    poder afinar los patrones más adelante.
    """
    dominios = []
    if _RE_DOLAR.search(texto):
        dominios.append("dolar")
    if _RE_CRIPTO_GENERICA.search(texto) or _detectar_ticker(texto):
        dominios.append("cripto")
    if _RE_BCRA.search(texto):
        dominios.append("bcra")
    if len(dominios) > 1:
        logger.warning(
            "Intención ambigua (%s) en %r; se resolvió como %r",
            ", ".join(dominios), texto, elegido,
        )
