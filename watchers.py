"""Centinela de precios para BankRanks Argentina.

Parsea pedidos en lenguaje natural del tipo *"avisame cuando el blue supere
los 1500"* o *"notificame si bitcoin baja de 60000"* y los traduce a una
estructura que el scheduler puede chequear contra los precios en vivo.

Diseño (igual que ``intent_detector``):
    * Módulo PURO en su parte de parseo y decisión: ``parsear_watcher`` y
      ``cumple`` no tocan la red ni la base de datos, así que se testean de
      forma aislada con pytest y sin esperar a que el mercado se mueva.
    * El único import externo es el catálogo de criptos de ``apis.cotizaciones``
      (tablas de datos, no llamadas de red) para no duplicar la lista de coins.

Funciones públicas:
    * :func:`parsear_watcher` — texto natural -> dict de watcher (o ``None``).
    * :func:`cumple` — decide si un precio dispara el watcher (lógica pura).
    * :func:`describir_condicion` — texto legible de la condición.
"""

from __future__ import annotations

import logging
import re
import unicodedata

from apis.cotizaciones import _CRIPTO_INFO

logger = logging.getLogger(__name__)


# ── Helpers de normalización ──────────────────────────────────────────────────

def _quitar_tildes(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _norm_umbral(crudo: str, multiplicador: str | None = None) -> float:
    """Normaliza un número a float siguiendo la convención argentina.

    El punto se usa como separador de miles ("1.500" -> 1500) y la coma como
    decimal ("0,5" -> 0.5). Soporta multiplicadores en palabra ("70 mil",
    "1 palo") y la abreviatura "k".
    """
    valor = float(crudo.replace(".", "").replace(",", "."))
    if multiplicador:
        m = _quitar_tildes(multiplicador.lower())
        if m == "k" or m.startswith("mil"):
            valor *= 1_000
        elif m.startswith("millon") or m.startswith("palo"):
            valor *= 1_000_000
    return valor


# ── Disparadores y operadores ──────────────────────────────────────────────────

# El pedido tiene que ser explícito (avisar / notificar / alertar / centinela)
# para no confundir un watcher con una consulta de precio normal.
_RE_TRIGGER = re.compile(
    r"avis\w*|notific\w*|alert\w*|centinela|av[ií]same|avert[ií]\w*",
    re.IGNORECASE,
)

# Cruce hacia arriba: superar, pasar, subir, llegar, tocar, alcanzar, etc.
_RE_OP_UP = re.compile(
    r"super\w*|pas[ae]\w*|sub[ae]\w*|lleg\w*|toq\w*|toc[ae]\w*|alcanc\w*|"
    r"arriba|encima|m[áa]s\s+de|mayor",
    re.IGNORECASE,
)
# Cruce hacia abajo: bajar, caer, menos de, debajo, menor, etc.
_RE_OP_DOWN = re.compile(
    r"baj[ae]\w*|caig\w*|\bcae\b|menos\s+de|debajo|por\s+debajo|menor|m[íi]nimo",
    re.IGNORECASE,
)

# Umbral numérico, con separador de miles opcional y multiplicador en palabra.
_RE_UMBRAL = re.compile(
    r"(\d[\d.,]*)\s*(mil(?:lones?|[oó]n)?|palos?|k)?",
    re.IGNORECASE,
)


# ── Catálogo de activos ─────────────────────────────────────────────────────────

# Casas del dólar: (casa_api, patrón, nombre_display, emoji).
_CASAS_DOLAR: list[tuple[str, str, str, str]] = [
    ("blue",            r"\bblue\b",                                      "Dólar Blue",      "💵"),
    ("oficial",         r"\boficial\b",                                   "Dólar Oficial",   "🏦"),
    ("bolsa",           r"\b(?:mep|bolsa)\b",                             "Dólar MEP",       "📈"),
    ("contadoconliqui", r"\bccl\b|contado\s+con\s+l[ií]qui\w*",          "Dólar CCL",       "💹"),
    ("tarjeta",         r"\b(?:tarjeta|turista|ahorro)\b",                "Dólar Tarjeta",   "💳"),
    ("mayorista",       r"\bmayorista\b",                                 "Dólar Mayorista", "🏗"),
    ("cripto",          r"cripto\s*d[óo]lar|d[óo]lar\s*cripto",          "Dólar Cripto",    "🔒"),
]

# Criptos: (coin_id, patrón). El display sale de _CRIPTO_INFO (fuente única).
# Cubre los mismos typos frecuentes que intent_detector (bircoin, etherium...).
_CRIPTOS: list[tuple[str, str]] = [
    ("bitcoin",     r"\b(?:bitcoin|bitcoint|bitcoing|bircoin|bitcon|btc)\b"),
    ("ethereum",    r"\b(?:ethereum|etherium|etereum|ether|eth)\b"),
    ("solana",      r"\b(?:solana|sol)\b"),
    ("binancecoin", r"\b(?:binance|bnb)\b"),
    ("cardano",     r"\b(?:cardano|ada)\b"),
    ("ripple",      r"\b(?:ripple|xrp)\b"),
    ("dogecoin",    r"\b(?:dogecoin|doge)\b"),
    ("tether",      r"\b(?:tether|usdt)\b"),
]

# Mención genérica del dólar (sin casa puntual) -> default blue.
_RE_DOLAR_GENERICO = re.compile(r"d[óo]lar|d[oó]lares", re.IGNORECASE)


def _detectar_activo(texto: str) -> tuple[str, str, str, str] | None:
    """Devuelve (clase, activo, nombre, emoji) del primer activo mencionado.

    Las criptos puntuales tienen prioridad sobre el dólar genérico. Si solo se
    menciona "dólar" sin casa, se asume el blue (la referencia más usada).
    """
    for coin_id, patron in _CRIPTOS:
        if re.search(patron, texto, re.IGNORECASE):
            _, nombre, ticker = _CRIPTO_INFO.get(coin_id, ("●", coin_id.capitalize(), coin_id.upper()))
            return "cripto", coin_id, f"{nombre} ({ticker})", "🪙"

    for casa, patron, nombre, emoji in _CASAS_DOLAR:
        if re.search(patron, texto, re.IGNORECASE):
            return "dolar", casa, nombre, emoji

    if _RE_DOLAR_GENERICO.search(texto):
        return "dolar", "blue", "Dólar Blue", "💵"

    return None


# ── Función principal de parseo ─────────────────────────────────────────────────

def parsear_watcher(texto: str) -> dict | None:
    """Traduce un pedido natural a un dict de watcher, o ``None``.

    El dict tiene la forma::

        {
            "clase":  "dolar" | "cripto",
            "activo": "blue"  | "bitcoin",   # casa del dólar o coin_id
            "nombre": "Dólar Blue",          # display legible
            "emoji":  "💵",
            "op":     ">=" | "<=",
            "umbral": 1500.0,
        }

    Devuelve ``None`` si falta cualquiera de las tres piezas obligatorias
    (disparador, operador de cruce, número) o si no se reconoce el activo.
    """
    if not texto or not texto.strip():
        return None
    t = texto.strip()

    if not _RE_TRIGGER.search(t):
        return None

    # El operador define el sentido del cruce. "baje/menos de" gana sobre
    # "suba/supere" si ambos aparecieran (caso raro como "baje hasta").
    if _RE_OP_DOWN.search(t):
        op = "<="
    elif _RE_OP_UP.search(t):
        op = ">="
    else:
        return None

    activo = _detectar_activo(t)
    if not activo:
        return None
    clase, codigo, nombre, emoji = activo

    m = _RE_UMBRAL.search(t)
    if not m:
        return None
    umbral = _norm_umbral(m.group(1), m.group(2))
    if umbral <= 0:
        return None

    return {
        "clase": clase,
        "activo": codigo,
        "nombre": nombre,
        "emoji": emoji,
        "op": op,
        "umbral": umbral,
    }


# ── Lógica de disparo (pura) ────────────────────────────────────────────────────

def cumple(op: str, precio: float, umbral: float) -> bool:
    """Decide si ``precio`` dispara la condición. Sin red, sin estado.

    Es el corazón testeable del centinela: ``">="`` dispara cuando el precio
    alcanza o supera el umbral; ``"<="`` cuando lo alcanza o cae por debajo.
    """
    if op == ">=":
        return precio >= umbral
    if op == "<=":
        return precio <= umbral
    return False


def describir_condicion(op: str, umbral: float, clase: str) -> str:
    """Texto legible de la condición, ej. 'supere los $1.500,00'."""
    simbolo = "USD " if clase == "cripto" else "$"
    monto = f"{simbolo}{umbral:,.2f}"
    verbo = "supere los" if op == ">=" else "baje a"
    return f"{verbo} {monto}"


# ── Cancelación en lenguaje natural ─────────────────────────────────────────────

# Verbos de cancelar/quitar.
_RE_CANCEL_TRIGGER = re.compile(
    r"cancel\w*|borr\w*|elimin\w*|sac[aá]\w*|quit\w*|desactiv\w*|fren\w*|\bpar[aá]\b",
    re.IGNORECASE,
)
# Referencia explícita a un centinela (lo distingue de cancelar un recordatorio).
# Nota: "alerta" a secas NO alcanza (la usan los recordatorios); pedimos
# "alerta de precio" o la palabra "centinela", o que se nombre un activo.
# "[cs]entinela" cubre la transcripción de Whisper en español rioplatense, que
# por el seseo escribe "sentinela" (con S) en vez de "centinela".
_RE_CENTINELA_REF = re.compile(
    r"[cs]entinelas?|watchers?|alertas?\s+de\s+precio|avisos?\s+de\s+precio",
    re.IGNORECASE,
)
_RE_TODOS = re.compile(r"\btodos?\b|\btodas?\b", re.IGNORECASE)
# Id de un centinela puntual: "centinela 2", "#3", "numero 4".
_RE_CANCEL_ID = re.compile(
    r"(?:[cs]entinela|alerta|aviso|n[uú]mero|nro|id|#)\s*#?\s*(\d+)",
    re.IGNORECASE,
)


def parsear_cancelacion(texto: str) -> dict | None:
    """Detecta el pedido de cancelar un centinela y a cuál se refiere.

    Devuelve uno de::

        {"tipo": "todos"}
        {"tipo": "id", "id": 2}
        {"tipo": "activo", "clase": ..., "activo": ..., "nombre": ..., "emoji": ...}
        {"tipo": "generico"}            # quiere cancelar pero no aclaró cuál

    o ``None`` si no es un pedido de cancelación de centinela. Requiere un verbo
    de cancelar y, o bien la palabra "centinela"/"alerta de precio", o bien que
    se nombre un activo (para no pisar la cancelación de recordatorios).
    """
    if not texto or not _RE_CANCEL_TRIGGER.search(texto):
        return None

    activo = _detectar_activo(texto)
    if not (_RE_CENTINELA_REF.search(texto) or activo):
        return None

    if _RE_TODOS.search(texto):
        return {"tipo": "todos"}

    m = _RE_CANCEL_ID.search(texto)
    if m:
        return {"tipo": "id", "id": int(m.group(1))}

    if activo:
        clase, codigo, nombre, emoji = activo
        return {"tipo": "activo", "clase": clase, "activo": codigo,
                "nombre": nombre, "emoji": emoji}

    return {"tipo": "generico"}
