from transformers import pipeline
from filtrado_de_texto import filtrar_texto
import pandas as pd

analizador_de_sentimiento = pipeline(
    "sentiment-analysis", 
    model="nlptown/bert-base-multilingual-uncased-sentiment"
)
print("Modelo de Analisis de Sentimiento cargado con éxito.")


def analizador_sentimiento(frase):
    resultados = analizador_de_sentimiento(frase)[0]
    sentimiento = resultados["label"]
    confianza = resultados["score"]
    return sentimiento, confianza

class EstadoDelChat:
    def __init__(self,codigo):
        self.__codigo=codigo
        self.__mensajes=[]
        self.__resultados = []
    
    def agregar_mensaje(self,mensaje):
        assert type(mensaje)==str ,'El argumento tiene que ser un str'
        self.__mensajes.append(filtrar_texto(mensaje))
    
    def analizar_mensajes(self):
        for mensaje in self.__mensajes:
            resultados = analizador_sentimiento(mensaje)
        promedio_nota = resultados(0).mean()
        promedio_confianza = resultados(1).mean()
        return promedio_nota, promedio_confianza,

    def devolucion(self)
            