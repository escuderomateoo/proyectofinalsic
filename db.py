import json
import os
import logging
from contextlib import contextmanager
import sqlite3

logger = logging.getLogger(__name__)

DB_PATH = "bot_data.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS carpetas (
                nombre TEXT PRIMARY KEY,
                dinero REAL NOT NULL DEFAULT 0.0
            );
            CREATE TABLE IF NOT EXISTS mensajes (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_chat INTEGER NOT NULL,
                nota      INTEGER NOT NULL,
                confianza REAL NOT NULL,
                mensaje   TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS mensajes_mean (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_chat   INTEGER NOT NULL,
                nota_mean     REAL NOT NULL,
                confianza_mean REAL NOT NULL,
                timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS alertas (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_chat INTEGER NOT NULL,
                mensaje     TEXT NOT NULL,
                fecha_hora  DATETIME NOT NULL,
                recurrente  INTEGER DEFAULT 0,
                dia_mes     INTEGER,
                timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS comprobantes (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                monto             TEXT,
                fecha_hora        TEXT,
                numero_operacion  TEXT,
                remitente         TEXT,
                destinatario      TEXT,
                timestamp         DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
    logger.info("Base de datos inicializada.")
    _migrate_existing_data()


def _migrate_existing_data() -> None:
    _migrate_carpetas()
    _migrate_comprobantes()


def _migrate_carpetas() -> None:
    if not os.path.exists("carpetas.json"):
        return
    try:
        with open("carpetas.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        with get_connection() as conn:
            for nombre, info in data.items():
                dinero = float(info.get("dinero", 0)) if isinstance(info, dict) else 0.0
                conn.execute(
                    "INSERT OR IGNORE INTO carpetas (nombre, dinero) VALUES (?, ?)",
                    (nombre, dinero),
                )
        logger.info("Migración de carpetas.json completada (%d carpetas).", len(data))
    except Exception as e:
        logger.warning("No se pudo migrar carpetas.json: %s", e)


def _migrate_comprobantes() -> None:
    if not os.path.exists("comprobantes.csv"):
        return
    try:
        import pandas as pd
        with get_connection() as conn:
            ya_hay = conn.execute("SELECT 1 FROM comprobantes LIMIT 1").fetchone()
        if ya_hay:
            logger.info("Migración de comprobantes omitida: la tabla ya tiene datos.")
            return
        df = pd.read_csv("comprobantes.csv")
        with get_connection() as conn:
            for _, row in df.iterrows():
                conn.execute(
                    "INSERT INTO comprobantes (monto, fecha_hora, numero_operacion, remitente, destinatario) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        str(row.get("Monto", "")),
                        str(row.get("Fecha y hora", "")),
                        str(row.get("Número de operación", "")),
                        str(row.get("Nombre, CUIT/CUIL y CVU del remitente", "")),
                        str(row.get("Nombre, CUIT/CUIL y CVU del destinatario", "")),
                    ),
                )
        logger.info("Migración de comprobantes.csv completada.")
    except Exception as e:
        logger.warning("No se pudo migrar comprobantes.csv: %s", e)


# ── Carpetas ──────────────────────────────────────────────────────────────────

def carpeta_existe(nombre: str) -> bool:
    with get_connection() as conn:
        return conn.execute("SELECT 1 FROM carpetas WHERE nombre = ?", (nombre,)).fetchone() is not None


def crear_carpeta(nombre: str, dinero: float) -> None:
    with get_connection() as conn:
        conn.execute("INSERT INTO carpetas (nombre, dinero) VALUES (?, ?)", (nombre, dinero))


def obtener_dinero_carpeta(nombre: str) -> float | None:
    with get_connection() as conn:
        row = conn.execute("SELECT dinero FROM carpetas WHERE nombre = ?", (nombre,)).fetchone()
        return float(row["dinero"]) if row else None


def actualizar_dinero_carpeta(nombre: str, dinero: float) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE carpetas SET dinero = ? WHERE nombre = ?", (dinero, nombre))


def listar_carpetas() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT nombre, dinero FROM carpetas ORDER BY dinero DESC").fetchall()
        return [{"nombre": r["nombre"], "dinero": float(r["dinero"])} for r in rows]


def eliminar_carpeta(nombre: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM carpetas WHERE nombre = ?", (nombre,))
        return cursor.rowcount > 0


# ── Sentimiento ───────────────────────────────────────────────────────────────

def guardar_mensaje(codigo_chat: int, mensaje: str, nota: int, confianza: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO mensajes (codigo_chat, nota, confianza, mensaje) VALUES (?, ?, ?, ?)",
            (codigo_chat, nota, confianza, mensaje),
        )


def obtener_notas_usuario(codigo_chat: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT nota, confianza, timestamp FROM mensajes WHERE codigo_chat = ? ORDER BY timestamp",
            (codigo_chat,),
        ).fetchall()
        return [{"nota": r["nota"], "confianza": r["confianza"], "timestamp": r["timestamp"]} for r in rows]


def guardar_mensajes_mean(codigo_chat: int, nota_mean: float, confianza_mean: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO mensajes_mean (codigo_chat, nota_mean, confianza_mean) VALUES (?, ?, ?)",
            (codigo_chat, nota_mean, confianza_mean),
        )


# ── Comprobantes ──────────────────────────────────────────────────────────────

def crear_alerta(codigo_chat: int, mensaje: str, fecha_hora, recurrente: bool = False, dia_mes: int | None = None) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO alertas (codigo_chat, mensaje, fecha_hora, recurrente, dia_mes) VALUES (?, ?, ?, ?, ?)",
            (codigo_chat, mensaje, fecha_hora, int(recurrente), dia_mes),
        )
        return cursor.lastrowid


def obtener_alertas_pendientes() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM alertas WHERE fecha_hora <= datetime('now', 'localtime')",
        ).fetchall()
        return [dict(r) for r in rows]


def reprogramar_alerta(id: int, nueva_fecha_hora) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE alertas SET fecha_hora = ? WHERE id = ?",
            (nueva_fecha_hora, id),
        )


def eliminar_alerta(id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM alertas WHERE id = ?", (id,))


def listar_alertas_usuario(codigo_chat: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM alertas WHERE codigo_chat = ? ORDER BY fecha_hora",
            (codigo_chat,),
        ).fetchall()
        return [dict(r) for r in rows]


def cancelar_alerta_usuario(id: int, codigo_chat: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM alertas WHERE id = ? AND codigo_chat = ?",
            (id, codigo_chat),
        )
        return cursor.rowcount > 0


def guardar_comprobante(
    monto: str, fecha_hora: str, numero_operacion: str, remitente: str, destinatario: str
) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO comprobantes (monto, fecha_hora, numero_operacion, remitente, destinatario) "
            "VALUES (?, ?, ?, ?, ?)",
            (monto, fecha_hora, numero_operacion, remitente, destinatario),
        )
