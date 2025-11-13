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
    source entorno_bot/Scripts/activate   # En Windows

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

    -Procesamiento de Audio:
    * Envía un mensaje de voz y el bot responderá. 
    * El bot puede escuchar el audio del usuario, transcribirlo a texto y luego procesar esa consulta como lo haría con cualquier mensaje de texto para generar una respuesta relevante y conversacional.

    -Gestión de gastos (por categoría)
    * /crear nombre dinero_inicial → Crea una categoría con el nombre y monto inicial especificado.
    * /depositar destino monto → Suma `monto` a la categoría `destino`.
    * /gasto nombre → Muestra el dinero actual en la carpeta `nombre`.
    * /resumen (o /resumen_gastos) → Devuelve un resumen con cada carpeta y el total acumulado.

     - El archivo `carpetas.json`:

    * Se genera automáticamente si no existe.
    * Guarda las carpetas como claves y en cada una un objeto con la propiedad `dinero`.
    * Ejemplo de estructura:
    
    ```json
    {
    "escuela": {
        "dinero": 1100.0
    },
    "celular": {
        "dinero": 5.0
    }
    }
    ```

    * Se actualiza automáticamente cuando se usan los comandos mencionados.

    - Analisis del Chat por IA
    El proyecto incluye un módulo adicional que realiza análisis de sentimiento sobre los mensajes enviados por los usuarios en Telegram.
    Este análisis permite identificar la tendencia emocional general de cada usuario (por ejemplo, si suele ser positivo, neutro o negativo en sus reseñas o mensajes al bot).

    ⚙️ Funcionamiento

    Cada vez que un usuario envía un mensaje, este se almacena junto con su chat_id.

    El módulo envía el texto a una API de Groq, que devuelve una puntuación de sentimiento (expresada como número de “⭐ estrellas” o un valor numérico).

    El  resultado se guarda en:

    mensajes.csv → contiene cada mensaje con su puntuación individual.
    mensajes_mean.csv → resume el promedio de sentimiento por cada chat.

##
      🖥️ Configuración del VPS y entorno

      Se alquiló un VPS económico en DonWeb, donde se instaló Ubuntu como sistema operativo base y Python 3.11.10 como entorno principal de ejecución.
      El servidor funciona como entorno centralizado para correr y administrar los bots del proyecto.

      ⚙️ Ejecución continua

      Para asegurar un funcionamiento 24/7, se configuró PM2 como gestor de procesos.
      PM2 mantiene ambos bots activos de forma permanente, los reinicia automáticamente si ocurre algún fallo y los lanza nuevamente cada vez que se reinicia el VPS.

      🤖 Estructura del proyecto

      El sistema está compuesto por dos bots:

      BanksRate → Bot principal encargado de las tareas automatizadas del proyecto.

      BotAdmin → Bot de administración que controla a BanksRate y supervisa su estado.

      🧩 Funcionalidades del BotAdmin

      🔌 Encender o apagar el bot BanksRate remotamente.

      🔄 Actualizar el bot principal con las últimas versiones del repositorio (pull automático).

      📊 Ver el estado de BanksRate y del propio BotAdmin, mostrando información y logs en tiempo real.

      🤖 Creación del BotAdmin en Telegram

      Como BotAdmin es un bot independiente, debe tener su propio bot y API key de Telegram:

      Abre Telegram y busca el usuario @BotFather.

      Usa el comando /newbot para crear un nuevo bot.

      Asigna un nombre y un username único (por ejemplo, BanksRateAdminBot).

      BotFather te entregará un token de acceso (API Key), que deberás copiar y pegar en la configuración del BotAdmin (por ejemplo, en un archivo .env o variable de entorno).

      ⚠️ Es importante no reutilizar el mismo token que el bot BanksRate, ya que el BotAdmin funciona como un servicio separado que controla al otro bot.

      Con esta configuración, el VPS mantiene ambos bots activos permanentemente, gestionados y actualizados de forma remota mediante Telegram.
      ﻿


## 👨‍💻 Desarrolladores y Agradecimientos

    * Proyecto desarrollado gracias a los conocimientos adquiridos en Samsung Innovation Campus.

    * Integrantes del grupo:

      - Escudero Mateo
      - Damián Melgarejo
      - Agustín Stella

**Agradecimiento especial:**

    Al profesor Ale Sosa por su guía y apoyo, y a los responsables del Programa Samsung Innovation por brindarnos esta oportunidad.



