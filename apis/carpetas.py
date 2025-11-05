import json
import os

RUTA_CARPETAS = "carpetas.json"

if not os.path.exists(RUTA_CARPETAS):
    with open(RUTA_CARPETAS, "w", encoding="utf-8") as f:
        # Inicializamos el archivo como un objeto vacío para que las carpetas
        # se puedan crear como claves en el objeto raíz con la propiedad "dinero".
        json.dump({}, f, indent=4, ensure_ascii=False)

def cargar_carpetas():
    if not os.path.exists(RUTA_CARPETAS):
        with open(RUTA_CARPETAS, "w") as f:
            json.dump({}, f)
    with open(RUTA_CARPETAS, "r") as f:
        return json.load(f)
    
def guardar_carpetas(carpetas):
    with open(RUTA_CARPETAS, "w") as f:
        json.dump(carpetas, f, indent=4)

def crear_carpeta(nombre, dinero_inicial=0):
    carpetas = cargar_carpetas()
    if nombre in carpetas:
        return f'La carpeta {nombre} ya existe.'
    carpetas[nombre] = {"dinero": dinero_inicial}
    guardar_carpetas(carpetas)
    return f'Carpeta {nombre} creada con dinero inicial de {dinero_inicial}.'

def ver_gasto(nombre):
    carpetas = cargar_carpetas()
    if nombre not in carpetas:
        return f'La carpeta {nombre} no existe.'
    dinero = carpetas[nombre].get("dinero", 0)
    return f'El dinero en {nombre} es {dinero}.'

def depositar(destino, monto):
    carpetas = cargar_carpetas()

    if destino not in carpetas:
        return f"❌ La carpeta destino '{destino}' no existe."
    
    carpetas[destino]["dinero"] += monto
    guardar_carpetas(carpetas)

    return f"✅ Suma realizada: ${monto} → {destino}"

def quitar(destino, monto):
    carpetas = cargar_carpetas()

    if destino not in carpetas:
        return f"❌ La carpeta destino '{destino}' no existe."
    
    if carpetas[destino]["dinero"] < monto:
        return f"❌ Fondos insuficientes en '{destino}'."
    
    carpetas[destino]["dinero"] -= monto
    guardar_carpetas(carpetas)

    return f"✅ Resta realizada: ${monto} ← {destino}"
