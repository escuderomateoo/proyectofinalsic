import re
import unicodedata
import nltk
from nltk.corpus import stopwords


##Funciones Para Filtrar el texto ingresado, para así el bot "piense" menos
nltk.download("stopwords")


def limpiar_texto(texto: str) -> str:
    """
    Funcion que recibe una linea de texto, la cual es corregida, es decis,
    elimina espacios innecesarios, mayusculas y caracteres especiales.
    Argumento:
        texto(str): Linea de texto en formato str.

    Return:
        texto_corregido(str):   texto en formato str.
    """
    # Minsucula todo
    texto = texto.lower()

    # Elimino acentos
    texto = unicodedata.normalize(
        "NFD", texto
    )  # Separa las tildes de cada letra, por mas que
    # no se vea en el print, no tienen espacio nada mas.

    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    # Esta funcion une el strg eliminando los caracteres que pertenezcan a 'Mn', que son
    # acentos y demas tipos similares.

    # Ahora, eliminemos caracteres especiales y multiples espacios mal puestos.

    texto = re.sub(
        r"[^a-z0-9\s]", "", texto
    )  # Defino un cojunto de elementos a considerar, los cuales
    # son, de [a,z],[0,9] y [\s](espacios en blanco). Luego
    # aplico una negacion (^), i.e, si no es alguno de esos, lo
    # elimina.

    texto = re.sub(
        r"\s+", " ", texto
    ).strip()  # Elimina espacios iniciales y finales, y luego corrige
    # que no hayan espacios seguidos, es decir si se cumple:
    # \s+, ie, dos espacios seguidos, pone un solo espacio.
    # texto = re.sub(r'(.)\1+',r'\1',texto)   #Elimina letras repetidas
    texto_arreglado = texto

    return texto_arreglado


def eliminar_stopwords(texto: str) -> str:
    """
    Funcion que elimina stopwords usando la libreria nltk

    Args:
        texto(str): Linea de texto en formato str

    Returns:
        texto_arreglado(str):   linea de texto en formato str sin stopwords
    """
    stopwords_es = set(stopwords.words("spanish"))  # Set de stopwords en Español

    palabras = texto.split()
    filtrado = [
        pala for pala in palabras if pala not in stopwords_es
    ]  # lista de palabras sin
    # las stopwords
    texto_corregido = " ".join(filtrado)
    return texto_corregido


def filtrar_texto(texto: str) -> str:
    """
    Funcion que aplica las funciones de limpieza y eliminacion de stopwords
    a una linea de texto.

    Args:
        texto(str): Linea de texto en formato str

    Returns:
        texto_arreglado(str):   linea de texto en formato str limpia y sin stopwords
    """
    texto_limpio = limpiar_texto(texto)
    texto_filtrado = eliminar_stopwords(texto_limpio)
    return texto_filtrado
