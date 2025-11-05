from transformers import pipeline
from apis.filtrado_de_texto import filtrar_texto
import pandas as pd
import numpy as np

analizador_de_sentimiento = pipeline(
    "sentiment-analysis", 
    model="nlptown/bert-base-multilingual-uncased-sentiment"
)
print("Modelo de Analisis de Sentimiento cargado con éxito.")


def analizador_sentimiento(frase):
    resultados = analizador_de_sentimiento(frase)[0]
    sentimiento = int(resultados["label"].split()[0])
    confianza = resultados["score"]
    return sentimiento, confianza

class EstadoDelChat:
    def __init__(self,codigo):
        self.__codigo= codigo
        self.__mensajes=[]
    
    def agregar_mensaje(self,mensaje):
        assert type(mensaje)==str ,'El argumento tiene que ser un str'
        self.__mensajes.append(filtrar_texto(mensaje))
    
    def analizar_mensajes(self):
        notas = []
        confianzas = []
        for mensaje in self.__mensajes:
            resultados = analizador_sentimiento(mensaje)
            notas.append(resultados[0])
            confianzas.append(resultados[1])
        promedio_notas = np.mean(np.array(notas))
        promedio_confianzas = np.mean(np.array(confianzas))
        return  notas, confianzas, promedio_notas,promedio_confianzas

    def devolucion(self):
        #Frame 1 de notas y la confianzas respectivas, con el codigo del chat
        datos_1 = self.analizar_mensajes()
        frame_1 = pd.DataFrame({
                                "Codigo_Chat" : [self.__codigo]*len(datos_1[0]),
                                "Nota": datos_1[0],
                                "Confianza": datos_1[1]
                            })
        #frame 2, codigo del chat, con promedio respectivo
        frame_2= pd.DataFrame({
                                "Codigo_Chat" : [self.__codigo],
                                "Nota_Mean" : [datos_1[2]],
                                "Confianza_Mean" : [datos_1[3]]
                            })
        try:
            #Almacenamiento en el archivo "mensajes_mean.csv"
            datos_entrada = pd.read_csv("mensajes_mean.csv")
            df_total = pd.concat([datos_entrada, frame_2], ignore_index=True)
            df_total.to_csv("mensajes_mean.csv",index=False)

            #Almacenamiento en el archvio "mensajes.csv"
            datos_entrada = pd.read_csv('mensajes.csv')
            df_total = pd.concat([datos_entrada,frame_1],ignore_index=True)
            df_total.to_csv('mensajes.csv',index=False)

        except Exception as e:
            return print(f'No se pudo almacenar los datos en el csv {e}')