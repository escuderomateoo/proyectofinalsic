import logging
import numpy as np
from transformers import pipeline
import db

logger = logging.getLogger(__name__)

analizador_de_sentimiento = pipeline(
    "sentiment-analysis",
    model="nlptown/bert-base-multilingual-uncased-sentiment",
)
logger.info("Modelo de análisis de sentimiento cargado.")


def analizador_sentimiento(frase: str) -> tuple[int, float]:
    resultados = analizador_de_sentimiento(frase)[0]
    nota = int(resultados["label"].split()[0])
    confianza = resultados["score"]
    return nota, confianza


class EstadoDelChat:
    def __init__(self, codigo: int):
        self.__codigo = codigo
        self.__mensajes: list[str] = []
        self.__saved_count = 0
        self.__suma_notas = 0.0
        self.__suma_confianzas = 0.0

    def agregar_mensaje(self, mensaje: str) -> None:
        assert isinstance(mensaje, str), "El argumento tiene que ser un str"
        self.__mensajes.append(mensaje)

    def devolucion(self) -> None:
        total = len(self.__mensajes)
        if total < 5:
            return

        new_msgs = self.__mensajes[self.__saved_count:]
        if not new_msgs:
            return

        for msg in new_msgs:
            nota, confianza = analizador_sentimiento(msg)
            self.__suma_notas += nota
            self.__suma_confianzas += confianza
            try:
                db.guardar_mensaje(self.__codigo, msg, nota, confianza)
            except Exception as e:
                logger.error("Error guardando mensaje en DB: %s", e)

        self.__saved_count = total
        nota_mean = self.__suma_notas / total
        confianza_mean = self.__suma_confianzas / total

        try:
            db.guardar_mensajes_mean(self.__codigo, nota_mean, confianza_mean)
        except Exception as e:
            logger.error("Error guardando mean en DB: %s", e)

        logger.info("Sentimiento chat %d → mean=%.2f (confianza=%.2f)", self.__codigo, nota_mean, confianza_mean)
