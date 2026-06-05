from typing import Optional
import telebot

PROVINCIAS_DISPLAY = {
    "CABA": "🏙️ CABA",
    "BA":   "🏘️ Buenos Aires",
    "CBA":  "🏔️ Córdoba",
    "SF":   "🌾 Santa Fe",
    "CHACO":"🌲 Chaco",
    "LPAM": "🌿 La Pampa",
    "LRJA": "⛰️ La Rioja",
    "CHUB": "🌊 Chubut",
}

PROVINCIAS_MATCH = {
    "CABA": "ciudad autónoma de buenos aires (sede)",
    "BA":   "buenos aires",
    "CBA":  "córdoba",
    "SF":   "santa fe",
    "CHACO":"chaco",
    "LPAM": "la pampa",
    "LRJA": "la rioja",
    "CHUB": "chubut",
}


def menu_principal() -> telebot.types.InlineKeyboardMarkup:
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("🏆 Los más baratos",    callback_data="cmp:baratos"),
        telebot.types.InlineKeyboardButton("🎁 Sin costo mensual",  callback_data="cmp:gratis"),
        telebot.types.InlineKeyboardButton("⚖️ Comparar dos bancos", callback_data="cmp:dos"),
        telebot.types.InlineKeyboardButton("📍 Por provincia",       callback_data="cmp:prov"),
    )
    return markup


def menu_provincias() -> telebot.types.InlineKeyboardMarkup:
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    botones = [
        telebot.types.InlineKeyboardButton(label, callback_data=f"cmp:p:{code}")
        for code, label in PROVINCIAS_DISPLAY.items()
    ]
    markup.add(*botones)
    markup.add(telebot.types.InlineKeyboardButton("« Volver", callback_data="cmp:menu"))
    return markup


def menu_bancos(bancos: list, excluir_idx: Optional[int] = None) -> telebot.types.InlineKeyboardMarkup:
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    botones = []
    for i, banco in enumerate(bancos):
        if i == excluir_idx:
            continue
        nombre = banco["bank"]
        etiqueta = nombre[:28] + "…" if len(nombre) > 28 else nombre
        botones.append(telebot.types.InlineKeyboardButton(etiqueta, callback_data=f"cmp:b:{i}"))
    markup.add(*botones)
    markup.add(telebot.types.InlineKeyboardButton("« Volver", callback_data="cmp:menu"))
    return markup


def resultado_baratos(bancos: list) -> str:
    digitales = [b for b in bancos if float(b["monthly_maintenance_ars"]) == 0]
    tradicionales = sorted(
        [b for b in bancos if float(b["monthly_maintenance_ars"]) > 0],
        key=lambda b: float(b["monthly_maintenance_ars"]),
    )[:5]

    lineas = ["🏆 *Bancos más convenientes:*\n"]

    if digitales:
        lineas.append("📱 *Digitales — Sin costo mensual:*")
        for b in digitales:
            lineas.append(f"✅ *{b['bank']}*  📍 {b['province']}")

    emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    lineas.append("\n🏦 *Bancos tradicionales más baratos:*")
    for i, b in enumerate(tradicionales):
        costo = float(b["monthly_maintenance_ars"])
        lineas.append(f"{emojis[i]} *{b['bank']}*\n   💰 ${costo:,.2f}/mes  📍 {b['province']}")

    return "\n\n".join(lineas)


def resultado_gratis(bancos: list) -> str:
    gratis = [b for b in bancos if float(b["monthly_maintenance_ars"]) == 0]
    if not gratis:
        return "No hay bancos sin costo en el dataset."
    lineas = ["🎁 *Bancos sin costo mensual:*\n"]
    for b in gratis:
        nota = b.get("note", "")
        lineas.append(f"✅ *{b['bank']}*\n   📍 {b['province']}\n   📝 _{nota}_")
    lineas.append("\n💡 Todos son bancos digitales. Cero mantenimiento, cero sorpresas.")
    return "\n\n".join(lineas)


def resultado_provincia(bancos: list, code: str) -> str:
    match = PROVINCIAS_MATCH.get(code, "").lower()
    label = PROVINCIAS_DISPLAY.get(code, code)

    provinciales = [b for b in bancos if b["province"].lower() == match]
    nacionales_top5 = sorted(
        [b for b in bancos if b["province"].lower() == "nacional"],
        key=lambda b: float(b["monthly_maintenance_ars"]),
    )[:5]

    lineas = [f"📍 *Bancos en {label}:*\n"]

    if provinciales:
        lineas.append("🏛️ *Banco provincial:*")
        for b in provinciales:
            costo = float(b["monthly_maintenance_ars"])
            costo_str = "Sin costo" if costo == 0 else f"${costo:,.2f}/mes"
            lineas.append(f"🏦 *{b['bank']}*  —  💰 {costo_str}")

    digitales = [b for b in nacionales_top5 if float(b["monthly_maintenance_ars"]) == 0]
    tradicionales = [b for b in nacionales_top5 if float(b["monthly_maintenance_ars"]) > 0]

    if digitales:
        lineas.append("📱 *Digitales nacionales — Sin costo:*")
        for b in digitales:
            lineas.append(f"✅ *{b['bank']}*")

    if tradicionales:
        lineas.append("🌍 *Bancos tradicionales nacionales:*")
        for b in tradicionales:
            costo = float(b["monthly_maintenance_ars"])
            lineas.append(f"🏦 *{b['bank']}*  —  💰 ${costo:,.2f}/mes")

    return "\n\n".join(lineas)


def resultado_comparacion(bancos: list, idx1: int, idx2: int) -> str:
    b1, b2 = bancos[idx1], bancos[idx2]
    c1, c2 = float(b1["monthly_maintenance_ars"]), float(b2["monthly_maintenance_ars"])

    def bloque(b, c):
        costo_str = "Sin costo ✨" if c == 0 else f"${c:,.2f}/mes"
        return (
            f"🏦 *{b['bank']}*\n"
            f"   💰 {costo_str}\n"
            f"   📍 {b['province']}\n"
            f"   📝 _{b.get('note', 'Sin información adicional.')}_"
        )

    texto = f"⚖️ *Comparación bancaria*\n\n{bloque(b1, c1)}\n\n— — — VS — — —\n\n{bloque(b2, c2)}\n\n"

    if c1 == 0 and c2 == 0:
        texto += "🤝 ¡Ambos son gratuitos! No hay diferencia de costo."
    elif c1 == c2:
        texto += "🤝 Tienen exactamente el mismo costo mensual."
    else:
        mas_barato = b1 if c1 < c2 else b2
        dif_mes = abs(c1 - c2)
        dif_anio = dif_mes * 12
        texto += (
            f"✅ *{mas_barato['bank']}* es el más conveniente\n"
            f"   Ahorrás *${dif_mes:,.2f}* por mes\n"
            f"   💡 Eso es *${dif_anio:,.2f} por año*"
        )
    return texto
