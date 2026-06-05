import logging
import requests
import urllib3
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TIMEOUT = 8

# ── Dólar ─────────────────────────────────────────────────────────────────────

_CASAS_CONFIG = {
    "oficial":         ("🏦", "Oficial"),
    "blue":            ("💵", "Blue"),
    "bolsa":           ("📈", "MEP / Bolsa"),
    "contadoconliqui": ("💹", "CCL"),
    "cripto":          ("🔒", "Cripto"),
    "tarjeta":         ("💳", "Tarjeta"),
    "mayorista":       ("🏗", "Mayorista"),
}
_ORDEN_CASAS = ["oficial", "blue", "bolsa", "contadoconliqui", "cripto", "tarjeta", "mayorista"]


def obtener_dolar() -> list[dict] | None:
    try:
        r = requests.get("https://dolarapi.com/v1/dolares", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error("Error dólar API: %s", e)
        return None


def formatear_dolar(datos: list[dict]) -> str:
    datos_dict = {d["casa"]: d for d in datos}
    lineas = ["💵 *Cotizaciones del Dólar*"]

    ts = None
    for casa in _ORDEN_CASAS:
        d = datos_dict.get(casa)
        if not d:
            continue
        emoji, nombre = _CASAS_CONFIG.get(casa, ("💱", casa.capitalize()))
        compra = d.get("compra") or 0
        venta = d.get("venta") or 0
        if compra and venta:
            lineas.append(f"{emoji} {nombre:<14} C: ${compra:>10,.2f}   V: ${venta:>10,.2f}")
        elif venta:
            lineas.append(f"{emoji} {nombre:<14} ${venta:,.2f}")
        if not ts and d.get("fechaActualizacion"):
            ts = d["fechaActualizacion"]

    oficial = datos_dict.get("oficial")
    blue = datos_dict.get("blue")
    if oficial and blue:
        v_o = oficial.get("venta") or 0
        v_b = blue.get("venta") or 0
        if v_o:
            brecha = ((v_b - v_o) / v_o) * 100
            lineas.append(f"\n📊 Brecha blue/oficial: {brecha:.1f}%")

    fecha_str = ""
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            fecha_str = dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            pass
    if not fecha_str:
        fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    lineas.insert(1, f"📅 Actualizado: {fecha_str} hs\n")

    return "\n".join(lineas)


# ── Cripto ────────────────────────────────────────────────────────────────────

CRIPTO_ALIAS: dict[str, str] = {
    "btc": "bitcoin",       "bitcoin": "bitcoin",
    "eth": "ethereum",      "ethereum": "ethereum",
    "sol": "solana",        "solana": "solana",
    "bnb": "binancecoin",   "binance": "binancecoin",
    "usdt": "tether",       "tether": "tether",
    "ada": "cardano",       "cardano": "cardano",
    "xrp": "ripple",        "ripple": "ripple",
    "doge": "dogecoin",     "dogecoin": "dogecoin",
}

_CRIPTO_INFO: dict[str, tuple[str, str, str]] = {
    "bitcoin":     ("₿",  "Bitcoin",  "BTC"),
    "ethereum":    ("Ξ",  "Ethereum", "ETH"),
    "solana":      ("◎",  "Solana",   "SOL"),
    "binancecoin": ("⬡",  "BNB",      "BNB"),
    "tether":      ("💲", "Tether",   "USDT"),
    "cardano":     ("♦",  "Cardano",  "ADA"),
    "ripple":      ("✕",  "XRP",      "XRP"),
    "dogecoin":    ("🐕", "Dogecoin", "DOGE"),
}

TOP_5 = ["bitcoin", "ethereum", "solana", "binancecoin", "tether"]


def obtener_cripto(coins: list[str]) -> dict | None:
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": ",".join(coins),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error("Error cripto API: %s", e)
        return None


def formatear_cripto(datos: dict, coins: list[str]) -> str:
    lineas = ["🪙 *Precios Cripto (USD)*\n"]
    for coin in coins:
        info = datos.get(coin)
        if not info:
            continue
        emoji, nombre, ticker = _CRIPTO_INFO.get(coin, ("●", coin.capitalize(), coin.upper()))
        precio = info.get("usd", 0)
        cambio = info.get("usd_24h_change") or 0
        flecha = "↑" if cambio >= 0 else "↓"
        signo = "+" if cambio >= 0 else ""
        precio_str = f"${precio:>12,.2f}" if precio >= 1 else f"${precio:.6f}"
        lineas.append(f"{emoji} {nombre} ({ticker})\n   {precio_str}   {flecha} {signo}{cambio:.2f}%")

    lineas.append(f"\n📅 {datetime.now().strftime('%d/%m/%Y %H:%M')} hs")
    return "\n".join(lineas)


# ── BCRA ──────────────────────────────────────────────────────────────────────

_BCRA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BotFinanciero/1.0)",
    "Accept": "application/json",
}


def _fetch_bcra_var(var_id: int) -> tuple[float | None, str | None]:
    hasta = datetime.now().strftime("%Y-%m-%d")
    desde = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    url = f"https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/{var_id}"
    try:
        r = requests.get(
            url,
            params={"desde": desde, "hasta": hasta},
            timeout=TIMEOUT,
            verify=False,
            headers=_BCRA_HEADERS,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        if results:
            detalle = results[0].get("detalle", [])
            if detalle:
                # v4.0 entrega el detalle ordenado de más reciente a más antiguo;
                # tomamos el de fecha máxima para no depender del orden.
                ultimo = max(detalle, key=lambda d: d.get("fecha", ""))
                return ultimo.get("valor"), ultimo.get("fecha")
    except Exception as e:
        logger.warning("Error BCRA var %d: %s", var_id, e)
    return None, None


def _fetch_argentinadatos(endpoint: str) -> tuple[float | None, str | None]:
    """Fetch último valor de api.argentinadatos.com."""
    try:
        r = requests.get(
            f"https://api.argentinadatos.com/v1/finanzas/indices/{endpoint}",
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        if data:
            last = data[-1]
            return last.get("valor"), last.get("fecha", "")[:7]
    except Exception as e:
        logger.warning("Error argentinadatos %s: %s", endpoint, e)
    return None, None


def obtener_bcra() -> str:
    lineas = ["🏛 *Datos Macroeconómicos Argentina*\n"]

    # Inflación mensual — argentinadatos.com (más confiable que BCRA directo)
    valor, fecha = _fetch_argentinadatos("inflacion/")
    if valor is not None:
        lineas.append(f"📊 Inflación mensual (IPC): {valor:.1f}%  ({fecha})")
    else:
        lineas.append("📊 Inflación mensual: No disponible")

    # Inflación interanual
    valor, fecha = _fetch_argentinadatos("inflacionInteranual/")
    if valor is not None:
        lineas.append(f"📈 Inflación interanual: {valor:.1f}%  ({fecha})")

    # Reservas y tasa — intento a BCRA
    valor, fecha = _fetch_bcra_var(1)
    fecha_str = f"  ({fecha})" if fecha else ""
    lineas.append(
        f"💰 Reservas BCRA: USD {valor:,.0f} M{fecha_str}" if valor is not None
        else "💰 Reservas BCRA: No disponible"
    )

    valor, fecha = _fetch_bcra_var(7)
    fecha_str = f"  ({fecha})" if fecha else ""
    lineas.append(
        f"🏦 Tasa BADLAR (bancos privados): {valor:.2f}% anual{fecha_str}" if valor is not None
        else "🏦 Tasa BADLAR (bancos privados): No disponible"
    )

    lineas.append(f"\n📅 Fuentes: ArgentinaDatos + BCRA | {datetime.now().strftime('%d/%m/%Y')}")
    return "\n".join(lineas)


# ── Histórico cripto ──────────────────────────────────────────────────────────

def obtener_tasa_plazo_fijo() -> float:
    """TNA promedio de mercado desde argentinadatos.com. Fallback: 37%."""
    try:
        r = requests.get(
            "https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo/",
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        tasas = []
        for d in data:
            t = d.get("tnaClientes") or d.get("tna") or d.get("TNA") or 0
            if t > 0:
                tasas.append(float(t))
        if tasas:
            return sum(tasas) / len(tasas)
    except Exception as e:
        logger.warning("Error tasas plazo fijo: %s", e)
    return 37.0


# ── Contexto dinámico en tiempo real ─────────────────────────────────────────

from time import monotonic as _monotonic

_ctx_cache: dict[str, tuple[float, str]] = {}
_CTX_TTL = 120  # segundos


def _contexto_dolar_texto() -> str | None:
    if "dolar" in _ctx_cache and _monotonic() - _ctx_cache["dolar"][0] < _CTX_TTL:
        return _ctx_cache["dolar"][1]
    datos = obtener_dolar()
    if not datos:
        return None
    _NOMBRES = {"oficial": "Oficial", "blue": "Blue", "bolsa": "MEP",
                "contadoconliqui": "CCL", "cripto": "Cripto", "tarjeta": "Tarjeta"}
    dd = {d["casa"]: d for d in datos}
    lineas = ["Cotizaciones actuales del dólar (en pesos argentinos):"]
    for casa, nombre in _NOMBRES.items():
        d = dd.get(casa)
        if not d:
            continue
        c, v = d.get("compra") or 0, d.get("venta") or 0
        if v:
            lineas.append(f"- {nombre}: compra ${c:,.2f} / venta ${v:,.2f}")
    texto = "\n".join(lineas)
    _ctx_cache["dolar"] = (_monotonic(), texto)
    return texto


def _contexto_cripto_texto() -> str | None:
    if "cripto" in _ctx_cache and _monotonic() - _ctx_cache["cripto"][0] < _CTX_TTL:
        return _ctx_cache["cripto"][1]
    datos = obtener_cripto(TOP_5)
    if not datos:
        return None
    lineas = ["Precios actuales de criptomonedas (en USD):"]
    for coin_id in TOP_5:
        info = datos.get(coin_id)
        if not info:
            continue
        _, nombre, ticker = _CRIPTO_INFO.get(coin_id, ("", coin_id, coin_id.upper()))
        precio = info.get("usd", 0)
        cambio = info.get("usd_24h_change") or 0
        lineas.append(f"- {nombre} ({ticker}): ${precio:,.2f}  ({cambio:+.2f}% en 24h)")
    texto = "\n".join(lineas)
    _ctx_cache["cripto"] = (_monotonic(), texto)
    return texto


def _contexto_inflacion_texto() -> str | None:
    if "inflacion" in _ctx_cache and _monotonic() - _ctx_cache["inflacion"][0] < _CTX_TTL:
        return _ctx_cache["inflacion"][1]
    valor, fecha = _fetch_argentinadatos("inflacion/")
    if valor is None:
        return None
    texto = f"Inflación mensual Argentina (IPC): {valor:.1f}% — período {fecha}"
    _ctx_cache["inflacion"] = (_monotonic(), texto)
    return texto


def obtener_cripto_historico(coin_id: str, days: int = 7) -> list[tuple[datetime, float]] | None:
    """Retorna lista de (fecha, precio_usd) para los últimos N días."""
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": days, "interval": "daily"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        prices = r.json().get("prices", [])
        return [
            (datetime.fromtimestamp(ts / 1000), precio)
            for ts, precio in prices
        ]
    except Exception as e:
        logger.error("Error histórico cripto %s: %s", coin_id, e)
        return None
