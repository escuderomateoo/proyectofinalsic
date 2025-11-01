import json
import os

RUTA_USUARIOS = "usuarios.json"

if not os.path.exists(RUTA_USUARIOS):
    with open(RUTA_USUARIOS, "w", encoding="utf-8") as f:
        json.dump({"usuarios": []}, f, indent=4, ensure_ascii=False)

def cargar_usuarios():
    if not os.path.exists(RUTA_USUARIOS):
        with open(RUTA_USUARIOS, "w") as f:
            json.dump({}, f)
    with open(RUTA_USUARIOS, "r") as f:
        return json.load(f)
    
def guardar_usuarios(usuarios):
    with open(RUTA_USUARIOS, "w") as f:
        json.dump(usuarios, f, indent=4)

def crear_usuario(nombre, saldo_inicial=0):
    usuarios = cargar_usuarios()
    if nombre in usuarios:
        return f'El usuario {nombre} ya existe.'
    usuarios[nombre] = {"saldo": saldo_inicial}
    guardar_usuarios(usuarios)
    return f'Usuario {nombre} creado con un saldo inicial de {saldo_inicial}.'

def ver_saldo(nombre):
    usuarios = cargar_usuarios()
    if nombre not in usuarios:
        return f'El usuario {nombre} no existe.'
    saldo = usuarios[nombre]["saldo"]
    return f'El saldo de {nombre} es {saldo}.'

def trasferir(origen, destino, monto):
    usuarios = cargar_usuarios()

    if origen not in usuarios:
        return f"❌ El usuario origen '{origen}' no existe."
    if destino not in usuarios:
        return f"❌ El usuario destino '{destino}' no existe."
    if usuarios[origen]["saldo"] < monto:
        return "⚠️ Saldo insuficiente."

    usuarios[origen]["saldo"] -= monto
    usuarios[destino]["saldo"] += monto
    guardar_usuarios(usuarios)

    return f"✅ Transferencia realizada: ${monto} de {origen} → {destino}"
