                                                                                                                                                        
                                                                                                                                                        
`7MM"""Mq.`7MM"""Mq.   .g8""8q.`YMM'   `MM'`7MM"""YMM    .g8"""bgd MMP""MM""YMM   .g8""8q.       `7MM"""YMM `7MMF'`7MN.   `7MF'     db      `7MMF'      
  MM   `MM. MM   `MM..dP'    `YM.VMA   ,V    MM    `7  .dP'     `M P'   MM   `7 .dP'    `YM.       MM    `7   MM    MMN.    M      ;MM:       MM        
  MM   ,M9  MM   ,M9 dM'      `MM VMA ,V     MM   d    dM'       `      MM      dM'      `MM       MM   d     MM    M YMb   M     ,V^MM.      MM        
  MMmmdM9   MMmmdM9  MM        MM  VMMP      MMmmMM    MM               MM      MM        MM       MM""MM     MM    M  `MN. M    ,M  `MM      MM        
  MM        MM  YM.  MM.      ,MP   MM       MM   Y  , MM.              MM      MM.      ,MP       MM   Y     MM    M   `MM.M    AbmmmqMA     MM      , 
  MM        MM   `Mb.`Mb.    ,dP'   MM       MM     ,M `Mb.     ,'      MM      `Mb.    ,dP'       MM         MM    M     YMM   A'     VML    MM     ,M 
.JMML.    .JMML. .JMM. `"bmmd"'   .JMML.   .JMMmmmmMMM   `"bmmmd'     .JMML.      `"bmmd"'       .JMML.     .JMML..JML.    YM .AMA.   .AMMA..JMMmmmmMMM 
                                                                                                                                                        
                                                                                                                                                        
                                                                                                                                                                        
#🤖 Asistente de Bancos en Telegram

Asistente conversacional para Telegram, impulsado por Groq, este bot esta diseñado para responder consultas bancarias en español mediante una base de datos local y realizar análisis de sentimiento, entre otras cosas que se detallan a continuación.

Requisitos del Sistema

-Python 3.10 o superior
-Telegram Bot Token (Obtenido de BotFather)
-Clave API de Groq
-Archivo dataset.json con la información estructurada.

🛠️ Instalación y Configuración

1. Cloná este repositorio o descargá los archivos.
2. Creá y activá un entorno virtual (recomendado):
   python -m venv entorno_bot
   entorno_bot\Scripts\activate # Windows

Instalá las dependencias:
pip install -r requirements.txt

Creá un archivo .env en la raíz con estas variables:
TELEGRAM_TOKEN=tu_token_de_telegram_aquí
GROQ_API_KEY=tu_clave_api_de_groq_aquí

Asegurate de tener el archivo dataset.json con preguntas y respuestas en la raíz.


🚀 Uso del Bot

Ejecutá el bot con:
python main.py
Luego, en Telegram, buscá tu bot y enviá:
/start o /help para iniciar la conversación.

#✨ Funcionalidades Destacadas

-Respuesta Asistida por IA: Cualquier consulta es procesada por el modelo de Groq, que utiliza el contenido de dataset.json como contexto para dar respuestas precisas y conversacionales.

-Análisis de Sentimiento: Usá el comando /sentimiento "frase" para obtener una clasificación del tono emocional del texto.

-Descripción de imagenes: Envía una imagen, y el bot la analizará para generar una descripción detallada de su contenido.

-Comprobantes: Envía un comprobante de transferencia, y el bot te enviará un resumen de la transferencia y guardará los datos en un archivo .CSV

-Filtro de Texto Inteligente: El bot aplica un proceso de limpieza (elimina acentos, puntuación y stopwords) a la consulta para optimizar la búsqueda de datos, la velocidad de respuesta de la IA y disminuir porcentaje de errores.


⚠️ IMPORTANTE

Una vez activado el bot, los comandos de la terminal dejan de funcionar.

👨‍💻 Desarrolladores y Agradecimientos
Este proyecto fue desarrollado gracias a los conocimientos adquiridos en Samsung Innovation Campus.

Integrantes del grupo:

-Escudero Mateo
-Damián Melgarejo
-Agustín Stella

Un agradecimiento especial al profesor Ale Sosa por su guía y apoyo durante el desarrollo y a los responsables del Programa Samusung Innovation por darnos esta oportunidad.


# Prueba desde servidor
