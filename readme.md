## 🤖 Asistente de Bancos en Telegram

    * Asistente conversacional para Telegram, impulsado por Groq.
      Este bot está diseñado para responder consultas bancarias en español mediante una base de datos local y realizar análisis de sentimiento, entre otras funcionalidades detalladas a continuación.

## 🧩 Requisitos del Sistema

    * Python 3.10 o superior
    * Telegram Bot Token (obtenido desde BotFather)
    * Clave API de Groq
    * Archivo dataset.json con la información estructurada

## ⚙️ Instalación y Configuración

  **1-Cloná este repositorio o descargá los archivos.**
  **2-Creá y activá un entorno virtual (recomendado):**
   
    python -m venv entorno_bot
    entorno_bot\Scripts\activate   # En Windows

  **3-Instalá las dependencias:**
    
    pip install -r requirements.txt

  **4-Creá un archivo .env en la raíz del proyecto con las siguientes variables:**

    TELEGRAM_TOKEN=tu_token_de_telegram_aquí
    GROQ_API_KEY=tu_clave_api_de_groq_aquí


  **5-Asegurate de tener el archivo dataset.json con preguntas y respuestas en la raíz.**


## 🚀 Uso del Bot

**Ejecutá el bot con:**

    python main.py

Luego, en Telegram, buscá tu bot y enviá:
/start o /help para iniciar la conversación.

## ✨ Funcionalidades Destacadas

    -Respuesta Asistida por IA: Cualquier consulta es procesada por el modelo de Groq, que utiliza el contenido de dataset.json como contexto para dar respuestas precisas y conversacionales.

    -Análisis de Sentimiento: 
    * Usá el comando 
    /sentimiento "frase" 
    para obtener una clasificación del tono emocional del texto.

    -Descripción de imagenes: 
    * Envía una imagen, y el bot la analizará para generar una descripción detallada de su contenido.

    -Comprobantes: 
    Enviá un comprobante de transferencia y el bot:
    * Enviará un resumen de la operación.
    * Guardará los datos en un archivo .CSV.  

    -Filtro de Texto Inteligente:
    * El bot realiza una limpieza avanzada del texto (elimina acentos, puntuación y stopwords) para:
    * Optimizar la búsqueda de datos.
    * Aumentar la velocidad de respuesta.
    * Disminuir errores.

    -Gestión de Usuarios y Saldos (Sistema Simulado)
    * El bot incluye una simulación bancaria para probar operaciones entre usuarios:
    * Comandos disponibles:

    * /crear nombre saldo_inicial → Crea un nuevo usuario con el saldo indicado.
    * /saldo nombre → Muestra el saldo actual del usuario.
    * /transferir origen destino monto → Transfiere dinero entre usuarios (actualizando automáticamente los saldos).

    - El archivo usuarios.json:

    * Se genera automáticamente si no existe.
    * Guarda los datos de todos los usuarios y sus saldos.
    * Se actualiza en tiempo real cada vez que se realiza una transferencia.

## ⚠️ IMPORTANTE

    * Una vez activado el bot, los comandos de la terminal dejan de funcionar.

## 👨‍💻 Desarrolladores y Agradecimientos

    * Proyecto desarrollado gracias a los conocimientos adquiridos en Samsung Innovation Campus.

    * Integrantes del grupo:

      - Escudero Mateo
      - Damián Melgarejo
      - Agustín Stella

**Agradecimiento especial:**

    Al profesor Ale Sosa por su guía y apoyo, y a los responsables del Programa Samsung Innovation por brindarnos esta oportunidad.


# Prueba desde servidor
