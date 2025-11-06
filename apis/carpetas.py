import json
import os
from typing import Dict, Any, Optional


class CarpetasManager:
    """Manager para operaciones sobre carpetas almacenadas en un JSON.

    Cada carpeta es una clave en el objeto raíz y contiene al menos la
    propiedad `dinero` con un valor numérico.
    """

    def __init__(self, path: str = "carpetas.json"):
        self.path = path
        # Asegurar que exista el archivo
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4, ensure_ascii=False)

    def _load(self) -> Dict[str, Any]:
        if not os.path.exists(self.path):
            return {}
        with open(self.path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}

    def _save(self, data: Dict[str, Any]) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    # Operaciones básicas
    def crear(self, nombre: str, dinero_inicial: float = 0.0) -> str:
        data = self._load()
        if nombre in data:
            return f"La carpeta {nombre} ya existe."
        data[nombre] = {"dinero": float(dinero_inicial)}
        self._save(data)
        return f"Carpeta {nombre} creada con dinero inicial de {dinero_inicial}."

    def ver(self, nombre: str) -> str:
        data = self._load()
        if nombre not in data:
            return f"La carpeta {nombre} no existe."
        dinero = float(data[nombre].get("dinero", 0))
        return f"El dinero en {nombre} es {dinero}."

    def depositar(self, destino: str, monto: float) -> str:
        data = self._load()
        if destino not in data:
            return f"❌ La carpeta destino '{destino}' no existe."
        data[destino]["dinero"] = float(data[destino].get("dinero", 0)) + float(monto)
        self._save(data)
        return f"✅ Suma realizada: ${monto} → {destino}"

    def quitar(self, destino: str, monto: float) -> str:
        data = self._load()
        if destino not in data:
            return f"❌ La carpeta destino '{destino}' no existe."
        if float(data[destino].get("dinero", 0)) < float(monto):
            return f"❌ Fondos insuficientes en '{destino}'."
        data[destino]["dinero"] = float(data[destino].get("dinero", 0)) - float(monto)
        self._save(data)
        return f"✅ Resta realizada: ${monto} ← {destino}"

    def transferir(self, origen: str, destino: str, monto: float) -> str:
        data = self._load()
        if origen not in data:
            return f"❌ La carpeta origen '{origen}' no existe."
        if destino not in data:
            return f"❌ La carpeta destino '{destino}' no existe."
        if float(data[origen].get("dinero", 0)) < float(monto):
            return "⚠️ Dinero insuficiente para transferir."
        data[origen]["dinero"] = float(data[origen].get("dinero", 0)) - float(monto)
        data[destino]["dinero"] = float(data[destino].get("dinero", 0)) + float(monto)
        self._save(data)
        return f"✅ Transferencia realizada: ${monto} de {origen} → {destino}"

    def resumen(self) -> str:
        data = self._load()
        if not data:
            return "No hay carpetas registradas."
        lineas = []
        total = 0.0
        try:
            items = sorted(data.items(), key=lambda x: float(x[1].get("dinero", 0)), reverse=True)
        except Exception:
            items = data.items()
        for nombre, datos in items:
            dinero = float(datos.get("dinero", 0)) if isinstance(datos, dict) else 0.0
            lineas.append(f"- {nombre}: ${dinero:.2f}")
            total += dinero
        lineas.append(f"\nTotal: ${total:.2f}")
        return "Resumen de carpetas:\n" + "\n".join(lineas)

    # Handlers que reciben el texto del comando y devuelven la respuesta lista para enviar
    def handle_crear(self, texto_comando: str) -> str:
        partes = texto_comando.split()
        if len(partes) < 3:
            return "Uso: /crear nombre dinero_inicial"
        nombre = partes[1]
        try:
            dinero = float(partes[2])
        except ValueError:
            return "⚠️ El dinero inicial debe ser un número."
        return self.crear(nombre, dinero)

    def handle_gasto(self, texto_comando: str) -> str:
        partes = texto_comando.split()
        if len(partes) < 2:
            return "Uso: /gasto nombre"
        nombre = partes[1]
        return self.ver(nombre)

    def handle_depositar(self, texto_comando: str) -> str:
        partes = texto_comando.split()
        if len(partes) < 3:
            return "Uso: /depositar destino monto"
        destino = partes[1]
        try:
            monto = float(partes[2])
        except ValueError:
            return "⚠️ El monto debe ser un número."
        return self.depositar(destino, monto)

    def handle_quitar(self, texto_comando: str) -> str:
        partes = texto_comando.split()
        if len(partes) < 3:
            return "Uso: /quitar destino monto"
        destino = partes[1]
        try:
            monto = float(partes[2])
        except ValueError:
            return "⚠️ El monto debe ser un número."
        return self.quitar(destino, monto)

    def handle_transferir(self, texto_comando: str) -> str:
        partes = texto_comando.split()
        if len(partes) < 4:
            return "Uso: /transferir origen destino monto"
        origen, destino = partes[1], partes[2]
        try:
            monto = float(partes[3])
        except ValueError:
            return "⚠️ El monto debe ser un número."
        return self.transferir(origen, destino, monto)

    def handle_resumen(self, texto_comando: Optional[str] = None) -> str:
        # texto_comando no es usado pero se mantiene para simetría con otros handlers
        return self.resumen()


# Instancia por defecto para uso sencillo desde main
default_manager = CarpetasManager()

# Exponer funciones de compatibilidad (opcional)
def cargar_carpetas() -> Dict[str, Any]:
    return default_manager._load()

def guardar_carpetas(carpetas: Dict[str, Any]) -> None:
    return default_manager._save(carpetas)

def crear_carpeta(nombre: str, dinero_inicial: float = 0.0) -> str:
    return default_manager.crear(nombre, dinero_inicial)

def ver_gasto(nombre: str) -> str:
    return default_manager.ver(nombre)

def depositar(destino: str, monto: float) -> str:
    return default_manager.depositar(destino, monto)

def quitar(destino: str, monto: float) -> str:
    return default_manager.quitar(destino, monto)

def transferir(origen: str, destino: str, monto: float) -> str:
    return default_manager.transferir(origen, destino, monto)

def handle_crear(texto_comando: str) -> str:
    return default_manager.handle_crear(texto_comando)

def handle_gasto(texto_comando: str) -> str:
    return default_manager.handle_gasto(texto_comando)

def handle_depositar(texto_comando: str) -> str:
    return default_manager.handle_depositar(texto_comando)

def handle_quitar(texto_comando: str) -> str:
    return default_manager.handle_quitar(texto_comando)

def handle_transferir(texto_comando: str) -> str:
    return default_manager.handle_transferir(texto_comando)

def handle_resumen(texto_comando: Optional[str] = None) -> str:
    return default_manager.handle_resumen(texto_comando)
