import re
from datetime import datetime, timedelta


def parsear_alerta(texto: str) -> tuple[str, datetime, bool, int | None]:
    """
    Parsea el texto del comando /recordar y devuelve
    (mensaje, fecha_hora, recurrente, dia_mes).
    Lanza ValueError si no puede interpretar el tiempo.
    """
    texto = texto.strip()

    # "en X minutos"
    m = re.search(r'\ben (\d+) minutos?\b', texto, re.IGNORECASE)
    if m:
        mins = int(m.group(1))
        mensaje = re.sub(r'\s*\ben \d+ minutos?\b\s*', ' ', texto, flags=re.IGNORECASE).strip()
        return mensaje, datetime.now() + timedelta(minutes=mins), False, None

    # "en X horas"
    m = re.search(r'\ben (\d+) horas?\b', texto, re.IGNORECASE)
    if m:
        hrs = int(m.group(1))
        mensaje = re.sub(r'\s*\ben \d+ horas?\b\s*', ' ', texto, flags=re.IGNORECASE).strip()
        return mensaje, datetime.now() + timedelta(hours=hrs), False, None

    # "a las HH:MM"
    m = re.search(r'\ba las (\d{1,2}):(\d{2})\b', texto, re.IGNORECASE)
    if m:
        hora, minuto = int(m.group(1)), int(m.group(2))
        mensaje = re.sub(r'\s*\ba las \d{1,2}:\d{2}\b\s*', ' ', texto, flags=re.IGNORECASE).strip()
        fecha = datetime.now().replace(hour=hora, minute=minuto, second=0, microsecond=0)
        if fecha <= datetime.now():
            fecha += timedelta(days=1)
        return mensaje, fecha, False, None

    # "el dia X" o "el X de cada mes" → mensual
    m = re.search(r'\bel\s+(?:dia\s+)?(\d{1,2})(?:\s+de\s+cada\s+mes)?\b', texto, re.IGNORECASE)
    if m:
        dia = int(m.group(1))
        if not 1 <= dia <= 31:
            raise ValueError(f"El día {dia} no es válido. Tiene que estar entre 1 y 31.")
        mensaje = re.sub(r'\s*\bel\s+(?:dia\s+)?\d{1,2}(?:\s+de\s+cada\s+mes)?\b\s*', ' ', texto, flags=re.IGNORECASE).strip()
        now = datetime.now()
        try:
            fecha = now.replace(day=dia, hour=9, minute=0, second=0, microsecond=0)
        except ValueError:
            # día inválido para este mes (ej: 31 en febrero)
            fecha = now.replace(day=28, hour=9, minute=0, second=0, microsecond=0)
        if fecha <= now:
            # próximo mes
            if now.month == 12:
                fecha = fecha.replace(year=now.year + 1, month=1)
            else:
                fecha = fecha.replace(month=now.month + 1)
        return mensaje, fecha, True, dia

    raise ValueError(
        "No entendí cuándo querés el recordatorio.\n\n"
        "Formatos válidos:\n"
        "• en X minutos\n"
        "• en X horas\n"
        "• a las HH:MM\n"
        "• el dia X (se repite mensual)"
    )


def proxima_fecha_mensual(dia_mes: int) -> datetime:
    """Calcula la próxima fecha para un recordatorio mensual."""
    now = datetime.now()
    if now.month == 12:
        return now.replace(year=now.year + 1, month=1, day=dia_mes, hour=9, minute=0, second=0, microsecond=0)
    return now.replace(month=now.month + 1, day=dia_mes, hour=9, minute=0, second=0, microsecond=0)
