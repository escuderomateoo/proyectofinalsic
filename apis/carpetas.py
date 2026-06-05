import logging
from typing import Optional
import db

logger = logging.getLogger(__name__)


class CarpetasManager:
    def crear(self, nombre: str, dinero_inicial: float = 0.0) -> str:
        if db.carpeta_existe(nombre):
            return f"La carpeta '{nombre}' ya existe."
        db.crear_carpeta(nombre, dinero_inicial)
        return f"✅ Carpeta '{nombre}' creada con ${dinero_inicial:.2f}."

    def ver(self, nombre: str) -> str:
        dinero = db.obtener_dinero_carpeta(nombre)
        if dinero is None:
            return f"La carpeta '{nombre}' no existe."
        return f"El dinero en '{nombre}' es ${dinero:.2f}."

    def depositar(self, destino: str, monto: float) -> str:
        dinero_actual = db.obtener_dinero_carpeta(destino)
        if dinero_actual is None:
            return f"❌ La carpeta '{destino}' no existe."
        db.actualizar_dinero_carpeta(destino, dinero_actual + monto)
        return f"✅ Suma realizada: ${monto:.2f} → '{destino}'"

    def quitar(self, destino: str, monto: float) -> str:
        dinero_actual = db.obtener_dinero_carpeta(destino)
        if dinero_actual is None:
            return f"❌ La carpeta '{destino}' no existe."
        if dinero_actual < monto:
            return f"❌ Fondos insuficientes en '{destino}' (disponible: ${dinero_actual:.2f})."
        db.actualizar_dinero_carpeta(destino, dinero_actual - monto)
        return f"✅ Resta realizada: ${monto:.2f} ← '{destino}'"

    def resumen(self) -> str:
        carpetas = db.listar_carpetas()
        if not carpetas:
            return "No hay carpetas registradas."
        total = sum(c["dinero"] for c in carpetas)
        lineas = [f"- {c['nombre']}: ${c['dinero']:.2f}" for c in carpetas]
        lineas.append(f"\nTotal: ${total:.2f}")
        return "Resumen de carpetas:\n" + "\n".join(lineas)

    def handle_crear(self, texto: str) -> str:
        partes = texto.split()
        if len(partes) < 3:
            return "Uso: /crear nombre dinero_inicial"
        try:
            dinero = float(partes[2])
        except ValueError:
            return "⚠️ El dinero inicial debe ser un número."
        return self.crear(partes[1], dinero)

    def handle_gasto(self, texto: str) -> str:
        partes = texto.split()
        if len(partes) < 2:
            return "Uso: /gasto nombre"
        return self.ver(partes[1])

    def handle_depositar(self, texto: str) -> str:
        partes = texto.split()
        if len(partes) < 3:
            return "Uso: /depositar destino monto"
        try:
            monto = float(partes[2])
        except ValueError:
            return "⚠️ El monto debe ser un número."
        return self.depositar(partes[1], monto)

    def handle_quitar(self, texto: str) -> str:
        partes = texto.split()
        if len(partes) < 3:
            return "Uso: /quitar destino monto"
        try:
            monto = float(partes[2])
        except ValueError:
            return "⚠️ El monto debe ser un número."
        return self.quitar(partes[1], monto)

    def eliminar(self, nombre: str) -> str:
        if db.eliminar_carpeta(nombre):
            return f"🗑️ Carpeta '{nombre}' eliminada."
        return f"❌ La carpeta '{nombre}' no existe."

    def handle_eliminar(self, texto: str) -> str:
        partes = texto.split()
        if len(partes) < 2:
            return "Uso: /eliminar nombre"
        return self.eliminar(partes[1])

    def handle_resumen(self, texto: Optional[str] = None) -> str:
        return self.resumen()


_manager = CarpetasManager()


def handle_crear(texto: str) -> str:
    return _manager.handle_crear(texto)

def handle_gasto(texto: str) -> str:
    return _manager.handle_gasto(texto)

def handle_depositar(texto: str) -> str:
    return _manager.handle_depositar(texto)

def handle_quitar(texto: str) -> str:
    return _manager.handle_quitar(texto)

def handle_eliminar(texto: str) -> str:
    return _manager.handle_eliminar(texto)

def handle_resumen(texto: Optional[str] = None) -> str:
    return _manager.handle_resumen(texto)

def handle_transferir(*args, **kwargs) -> str:
    return "❌ La operación /transferir ya no está disponible. Usá /depositar y /quitar en su lugar."
