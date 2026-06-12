"""Resumen financiero diario (briefing) para BankRanks Argentina.

Parser PURO del pedido en lenguaje natural: traduce frases como *"mandame el
resumen diario a las 9"* a una acción concreta. La composición del resumen y su
envío viven en ``main.py`` porque dependen de la red y la base.

Acciones que devuelve :func:`parsear_briefing`:
    * ``{"accion": "activar", "hora": "HH:MM"}`` — programar el envío diario.
    * ``{"accion": "ahora"}``                    — mostrarlo una vez, ya.
    * ``{"accion": "desactivar"}``               — dar de baja el envío diario.
    * ``None``                                   — no es un pedido de briefing.

El disparador está anclado a frases explícitas ("briefing", "resumen diario",
"resumen del día", "resumen de mercado"...) para NO pisar el "resumen de gastos"
de las carpetas, que es otra cosa.
"""

from __future__ import annotations

import re

_RE_BRIEF = re.compile(
    r"briefing|"
    r"resumen\s+(?:financiero|diario|del?\s+d[íi]a|matutino|"
    r"de\s+la\s+ma[ñn]ana|del?\s+mercado|de\s+mercado|econ[óo]mico)",
    re.IGNORECASE,
)

_RE_DESACTIVAR = re.compile(
    r"desactiv\w*|cancel\w*|borr\w*|elimin\w*|dej[áa]\s+de|"
    r"no\s+me\s+(?:mandes|env[ií]es|lo\s+mandes)",
    re.IGNORECASE,
)

_RE_AHORA = re.compile(r"\bahora\b|\bya\b|al\s+toque|reci[ée]n", re.IGNORECASE)

# Hora del día en varios formatos: "a las 9", "a las 9:30", "21:00", "9hs".
_RE_HORA = re.compile(
    r"a\s+las\s+(\d{1,2})(?::(\d{2}))?|"
    r"\b(\d{1,2}):(\d{2})\b|"
    r"\b(\d{1,2})\s*(?:hs|h|horas)\b",
    re.IGNORECASE,
)


def _extraer_hora(texto: str) -> str | None:
    """Devuelve la hora como "HH:MM" (cero-rellenada) o ``None``."""
    m = _RE_HORA.search(texto)
    if not m:
        return None
    if m.group(1) is not None:        # "a las H[:MM]"
        h, mi = int(m.group(1)), int(m.group(2) or 0)
    elif m.group(3) is not None:      # "HH:MM"
        h, mi = int(m.group(3)), int(m.group(4))
    else:                             # "HHhs"
        h, mi = int(m.group(5)), 0
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        return None
    return f"{h:02d}:{mi:02d}"


def parsear_briefing(texto: str) -> dict | None:
    if not texto or not _RE_BRIEF.search(texto):
        return None

    if _RE_DESACTIVAR.search(texto):
        return {"accion": "desactivar"}

    hora = _extraer_hora(texto)
    if hora:
        return {"accion": "activar", "hora": hora}

    # "mandame el briefing" / "...ahora": preview inmediato.
    return {"accion": "ahora"}
