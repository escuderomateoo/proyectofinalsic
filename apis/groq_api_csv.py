import pandas as pd
import os


CSV_FILE = 'comprobantes.csv'

def guardar_comprobante_csv(comprobante_data: dict): 
    """
    Guarda los datos del comprobante en un archivo CSV usando Pandas.
    Si el archivo ya existe, agrega la fila sin borrar los anteriores
    """
    #convertir los datos del comprobante a dataframe
    df_nuevo = pd.DataFrame([comprobante_data])

    #si el archivo existe, se agregan los nuevo datos

    if os.path.isfile(CSV_FILE):
        df_existente = pd.read_csv(CSV_FILE)
        df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
    else:
        df_final = df_nuevo

    #guardar el CSV actualizado
    df_final.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')

    



