## 🤖 BankRanks Argentina — Asistente Financiero en Telegram

Asistente conversacional para Telegram, impulsado por Groq e inteligencia artificial.
Diseñado para responder consultas bancarias y financieras en español, con cotizaciones en tiempo real, análisis de gastos, recordatorios y mucho más.

---

## 🧩 Requisitos del Sistema

* Python 3.10 o superior
* Telegram Bot Token (obtenido desde BotFather)
* Clave API de Groq
* Archivo `dataset.json` con la información estructurada de bancos

---

## ⚙️ Instalación y Configuración

**1. Cloná este repositorio o descargá los archivos.**

**2. Creá y activá un entorno virtual (recomendado):**

```bash
python -m venv entorno_bot
source entorno_bot/bin/activate        # Linux / Mac
source entorno_bot/Scripts/activate    # Windows
```

**3. Instalá las dependencias:**

```bash
pip install -r requirements.txt
```

**4. Creá un archivo `.env` en la raíz del proyecto:**

```
TELEGRAM_TOKEN=tu_token_de_telegram_aquí
GROQ_API_KEY=tu_clave_api_de_groq_aquí
```

**5. Ejecutá el bot:**

```bash
python main.py
```

Luego buscá tu bot en Telegram y enviá `/start` para comenzar.

---

## 🚀 Comandos disponibles

### 💬 Generales

| Comando | Qué resuelve |
|---|---|
| `/start` | Inicia o reinicia la sesión. Muestra un menú de acceso rápido con botones para las funciones principales. |
| `/ayuda` | Muestra la lista completa de comandos disponibles con su descripción. |

---

### 🏦 Consultas bancarias

| Comando | Qué resuelve |
|---|---|
| Texto libre | Respondé cualquier pregunta sobre bancos, tarifas, costos de mantenimiento o comparativas en Argentina. La IA usa la base de datos actualizada de bancos para responder con precisión. |
| `/comparar` | Abre un wizard interactivo para comparar bancos. Podés filtrar por provincia, ver los más baratos, los gratuitos, o comparar dos bancos específicos cara a cara. |

---

### 💱 Mercados en tiempo real

| Comando | Qué resuelve |
|---|---|
| `/dolar` | Muestra todas las cotizaciones del dólar en tiempo real: oficial, blue, MEP, CCL, cripto y tarjeta. Incluye la brecha entre el blue y el oficial. Fuente: dolarapi.com |
| `/grafico_dolar` | Genera un gráfico de barras comparando el precio de compra y venta de cada tipo de dólar. |
| `/cripto` | Muestra los precios actuales del top 5 de criptomonedas (BTC, ETH, SOL, BNB, USDT) con la variación de las últimas 24 horas. Fuente: CoinGecko. |
| `/cripto btc` | Muestra el precio y variación de una criptomoneda específica. Monedas disponibles: BTC, ETH, SOL, BNB, USDT, ADA, XRP, DOGE. |
| `/grafico_cripto` | Genera un gráfico de línea con el historial de precio de Bitcoin en los últimos 7 días. |
| `/grafico_cripto eth` | Historial de precio de una cripto específica en los últimos 7 días. |
| `/bcra` | Muestra datos macroeconómicos de Argentina: inflación mensual e interanual (IPC), reservas internacionales del BCRA y tasa de política monetaria. Fuente: ArgentinaDatos + BCRA. |
| `/convertir 500 usd` | Convierte 500 USD a pesos argentinos mostrando el resultado para cada tipo de cambio (blue, MEP, CCL, etc.) usando cotizaciones en tiempo real. |
| `/convertir 100000 ars` | Convierte 100.000 pesos a dólares mostrando cuánto USD podés comprar con cada tipo de cambio. |
| `/plazo_fijo 100000 30` | Simula el rendimiento de un plazo fijo. Calcula la ganancia, el total a cobrar, la TNA y la TEA equivalente. Si no especificás la tasa, usa el promedio real del mercado. |
| `/plazo_fijo 100000 30 97.5` | Misma simulación pero con la TNA que vos elegís (en este caso 97.5%). Útil para comparar ofertas de distintos bancos. |

> **Enriquecimiento dinámico de contexto:** cuando le hacés una pregunta sobre dólares, criptomonedas o inflación al chat libre, el bot detecta el tema, consulta las APIs en tiempo real e inyecta las cotizaciones actuales en el prompt antes de enviárselo a la IA. Así responde siempre con datos del momento, no con los datos de entrenamiento del modelo.

---

### 💼 Gestión de gastos

| Comando | Qué resuelve |
|---|---|
| `/crear nombre monto` | Crea una carpeta de gastos con un nombre y un monto inicial. Sirve para organizar el dinero por categorías (ej: alquiler, comida, celular). |
| `/depositar nombre monto` | Suma dinero a una carpeta existente. |
| `/quitar nombre monto` | Resta dinero de una carpeta existente. |
| `/eliminar nombre` | Elimina una carpeta de gastos permanentemente. |
| `/gasto nombre` | Muestra el saldo actual de una carpeta específica. |
| `/resumen` | Muestra todas las carpetas con su saldo y el total acumulado. |
| `/grafico_gastos` | Genera un gráfico de torta con la distribución de todos los gastos, incluyendo el monto total. |
| `/analizar_gastos` | Envía el resumen de tus carpetas a la IA, que analiza tu distribución de gastos y te da recomendaciones personalizadas sobre cómo mejorar tus finanzas. |

---

### 🔬 Análisis de sentimiento

| Comando | Qué resuelve |
|---|---|
| `/sentimiento "tu frase"` | Analiza el tono emocional de cualquier texto usando un modelo BERT multilingüe. Devuelve una puntuación de 1 a 5 estrellas con nivel de confianza. |
| `/mi_perfil` | Muestra tu perfil de sentimiento histórico: puntuación promedio, nivel de confianza y un gráfico de línea con la evolución de tu estado emocional a lo largo de las conversaciones. |

---

### ⏰ Recordatorios

| Comando | Qué resuelve |
|---|---|
| `/recordar pagar alquiler en 30 minutos` | Programa un recordatorio que te llega en X minutos. |
| `/recordar reunión en 2 horas` | Programa un recordatorio que te llega en X horas. |
| `/recordar pagar tarjeta a las 15:30` | Programa un recordatorio para una hora exacta del día. Si ya pasó esa hora hoy, lo programa para mañana. |
| `/recordar pagar servicio el dia 10` | Programa un recordatorio mensual que se repite automáticamente el día indicado de cada mes. |
| `/mis_alertas` | Lista todos tus recordatorios activos con ID, fecha y mensaje. |
| `/cancelar_alerta [id]` | Cancela un recordatorio usando el ID que muestra `/mis_alertas`. |

---

### 📎 Contenido multimedia

| Tipo de envío | Qué hace el bot |
|---|---|
| **Imagen de comprobante** | Extrae automáticamente los datos de la transferencia (monto, fecha, número de operación, remitente y destinatario) y los guarda en la base de datos. |
| **Imagen general** | Describe el contenido de la imagen. Si no es bancaria, lo informa amablemente. |
| **Mensaje de voz** | Transcribe el audio usando Whisper y responde como si fuera un mensaje de texto. |
| **Número de tarjeta** | Detecta automáticamente si el texto contiene un número de tarjeta y valida si es válido usando el algoritmo de Luhn. |

---

## ✨ Novedades implementadas

Estas funcionalidades fueron desarrolladas durante el proyecto para llevar el bot de una versión básica a una plataforma financiera completa:

- **Base de datos SQLite** — reemplaza los archivos JSON y CSV. Datos persistentes, seguros y eficientes.
- **Historial de conversación** — el bot recuerda los últimos 10 mensajes de cada usuario para dar respuestas con contexto.
- **Rate limiting** — máximo 10 mensajes por minuto por usuario para evitar spam y proteger las APIs.
- **Logging con rotación** — registra todos los eventos en `bot.log` con archivos de hasta 5 MB y 3 backups.
- **Enriquecimiento dinámico de contexto** — detecta si la pregunta es sobre dólar, cripto o inflación, consulta las APIs en tiempo real e inyecta los datos actuales en el prompt antes de enviárselo a la IA.
- **Comparador de bancos** — wizard paso a paso con filtros por provincia, precio y comparación directa entre dos bancos.
- **Alertas y recordatorios** — scheduler corriendo en hilo separado que revisa y envía alertas cada 30 segundos.
- **Cotizaciones en tiempo real** — dólar (dolarapi.com), criptos (CoinGecko) y datos del BCRA (ArgentinaDatos).
- **Gráficos con matplotlib** — gráficos de torta, barras y líneas generados en memoria sin guardar archivos.
- **Simulador de plazo fijo** — calcula ganancia, TNA y TEA con tasa real del mercado o la que el usuario indique.
- **Convertidor de monedas** — convierte entre ARS y USD usando cotizaciones en tiempo real por tipo de cambio.
- **Menú de inicio con botones** — `/start` muestra accesos rápidos a las funciones principales como botones interactivos.

---

## 🖥️ Configuración del VPS y entorno

Se alquiló un VPS económico en DonWeb, donde se instaló Ubuntu como sistema operativo base y Python 3.11 como entorno de ejecución.

**Ejecución continua**

Para asegurar un funcionamiento 24/7, se configuró PM2 como gestor de procesos. PM2 mantiene los bots activos de forma permanente, los reinicia si ocurre algún fallo y los lanza automáticamente al reiniciar el VPS.

**Estructura del sistema**

El sistema está compuesto por dos bots:

- **BanksRate** → Bot principal con todas las funcionalidades del proyecto.
- **BotAdmin** → Bot de administración que controla a BanksRate remotamente: encenderlo, apagarlo, actualizarlo desde GitHub y ver logs en tiempo real.

---

## 👨‍💻 Desarrolladores y Agradecimientos

Proyecto desarrollado gracias a los conocimientos adquiridos en **Samsung Innovation Campus**.

**Integrantes del grupo:**
- Escudero Mateo
- Damián Melgarejo
- Agustín Stella

**Agradecimiento especial:**
Al profesor Ale Sosa por su guía y apoyo, y a los responsables del Programa Samsung Innovation por brindarnos esta oportunidad.
