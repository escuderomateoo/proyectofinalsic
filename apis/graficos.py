import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def generar_grafico_sentimiento(notas: list[int]) -> io.BytesIO:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = list(range(1, len(notas) + 1))
    media = sum(notas) / len(notas)

    fig, ax = plt.subplots(figsize=(10, 5), facecolor="#FFFFFF")

    # Zonas de color de fondo
    ax.axhspan(0.5, 2.5, alpha=0.08, color="#F44336")   # rojo: negativo
    ax.axhspan(2.5, 3.5, alpha=0.08, color="#FFC107")   # amarillo: neutro
    ax.axhspan(3.5, 5.5, alpha=0.08, color="#4CAF50")   # verde: positivo

    # Línea del sentimiento
    ax.plot(x, notas, color="#2196F3", linewidth=2, marker="o", markersize=5, label="Sentimiento")

    # Línea del promedio
    ax.axhline(media, color="#FF5722", linestyle="--", linewidth=1.5, label=f"Promedio: {media:.1f}/5")

    ax.set_ylim(0.5, 5.5)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["1 ★", "2 ★★", "3 ★★★", "4 ★★★★", "5 ★★★★★"], fontsize=10)
    ax.set_xlabel("Mensaje N°", fontsize=11)
    ax.set_title("Evolución de tu sentimiento", fontsize=14, fontweight="bold", pad=15)
    ax.legend(loc="upper right", fontsize=10, framealpha=0.8)
    ax.grid(axis="y", alpha=0.3, linestyle="--")

    # Etiquetas de zona
    ax.text(len(x) + 0.3, 1.5, "Negativo", color="#F44336", fontsize=8, va="center")
    ax.text(len(x) + 0.3, 3.0, "Neutro",   color="#FF8F00", fontsize=8, va="center")
    ax.text(len(x) + 0.3, 4.5, "Positivo", color="#388E3C", fontsize=8, va="center")

    fig.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf


COLORES = [
    "#2196F3", "#4CAF50", "#FF9800", "#E91E63", "#9C27B0",
    "#00BCD4", "#FF5722", "#8BC34A", "#FFC107", "#3F51B5",
]


def generar_grafico_gastos(carpetas: list[dict]) -> io.BytesIO:
    import matplotlib
    matplotlib.use("Agg")  # backend sin pantalla, necesario en VPS
    import matplotlib.pyplot as plt

    nombres = [c["nombre"].capitalize() for c in carpetas]
    montos = [c["dinero"] for c in carpetas]
    total = sum(montos)
    colores = COLORES[: len(nombres)]

    fig, ax = plt.subplots(figsize=(9, 7), facecolor="#FFFFFF")

    wedges, _, autotexts = ax.pie(
        montos,
        colors=colores,
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.80,
        wedgeprops={"linewidth": 2, "edgecolor": "white", "antialiased": True},
    )

    for at in autotexts:
        at.set_fontsize(10)
        at.set_fontweight("bold")
        at.set_color("white")

    leyendas = [f"{nombres[i]}  —  ${montos[i]:,.2f}" for i in range(len(nombres))]
    ax.legend(
        wedges,
        leyendas,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.20),
        ncol=2,
        fontsize=10,
        frameon=False,
    )

    ax.set_title(
        f"Distribución de Gastos\nTotal: ${total:,.2f}",
        fontsize=14,
        fontweight="bold",
        pad=20,
        color="#212121",
    )

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf


def generar_grafico_cripto(
    precios: list[tuple[datetime, float]],
    nombre: str,
    ticker: str,
    dias: int = 7,
) -> io.BytesIO:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    fechas = [p[0] for p in precios]
    valores = [p[1] for p in precios]
    cambio_pct = ((valores[-1] - valores[0]) / valores[0] * 100) if valores[0] else 0
    color_linea = "#4CAF50" if cambio_pct >= 0 else "#F44336"
    flecha = "↑" if cambio_pct >= 0 else "↓"

    fig, ax = plt.subplots(figsize=(10, 5), facecolor="#FFFFFF")
    ax.plot(fechas, valores, color=color_linea, linewidth=2.5, marker="o", markersize=5)
    ax.fill_between(fechas, valores, min(valores) * 0.998, alpha=0.12, color=color_linea)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    fig.autofmt_xdate(rotation=30)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    ax.set_xlabel("Fecha", fontsize=11)
    ax.set_ylabel("Precio (USD)", fontsize=11)
    ax.set_title(
        f"{nombre} ({ticker}) — Últimos {dias} días\n"
        f"Actual: ${valores[-1]:,.2f}   {flecha} {cambio_pct:+.2f}%",
        fontsize=13, fontweight="bold", pad=12,
    )
    fig.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf


def generar_grafico_dolar(datos: list[dict]) -> io.BytesIO:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _ORDEN = ["oficial", "blue", "bolsa", "contadoconliqui", "cripto", "tarjeta"]
    _NOMBRES = {
        "oficial": "Oficial", "blue": "Blue", "bolsa": "MEP",
        "contadoconliqui": "CCL", "cripto": "Cripto", "tarjeta": "Tarjeta",
    }
    datos_dict = {d["casa"]: d for d in datos}

    nombres, compras, ventas = [], [], []
    for casa in _ORDEN:
        d = datos_dict.get(casa)
        if not d:
            continue
        c = d.get("compra") or 0
        v = d.get("venta") or 0
        if not v:
            continue
        nombres.append(_NOMBRES.get(casa, casa.capitalize()))
        compras.append(c)
        ventas.append(v)

    y = range(len(nombres))
    ancho = 0.38
    fig, ax = plt.subplots(figsize=(10, 6), facecolor="#FFFFFF")
    b1 = ax.barh([i + ancho / 2 for i in y], compras, height=ancho,
                 color="#2196F3", label="Compra", alpha=0.88)
    b2 = ax.barh([i - ancho / 2 for i in y], ventas, height=ancho,
                 color="#4CAF50", label="Venta", alpha=0.88)
    for bar in b1:
        w = bar.get_width()
        ax.text(w + 5, bar.get_y() + bar.get_height() / 2,
                f"${w:,.0f}", va="center", fontsize=9, color="#1565C0")
    for bar in b2:
        w = bar.get_width()
        ax.text(w + 5, bar.get_y() + bar.get_height() / 2,
                f"${w:,.0f}", va="center", fontsize=9, color="#2E7D32")
    ax.set_yticks(list(y))
    ax.set_yticklabels(nombres, fontsize=11)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.legend(fontsize=11, loc="lower right")
    ax.grid(axis="x", alpha=0.2, linestyle="--")
    ax.set_title(
        f"Cotizaciones del Dólar\n{datetime.now().strftime('%d/%m/%Y %H:%M')} hs",
        fontsize=13, fontweight="bold", pad=12,
    )
    fig.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf
