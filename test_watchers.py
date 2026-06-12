"""Tests del centinela de precios (módulo ``watchers``).

Dos bloques:
    * Parseo de lenguaje natural -> dict de watcher.
    * Lógica de disparo (``cumple``), que es la que garantiza que el centinela
      se gatilla bien sin tener que esperar a que el mercado se mueva.

    pytest test_watchers.py -v
"""

import pytest

from watchers import parsear_watcher, cumple, describir_condicion, parsear_cancelacion


# ── Parseo: dólar ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("texto,esperado", [
    ("avisame cuando el blue supere los 1500",
     {"clase": "dolar", "activo": "blue", "op": ">=", "umbral": 1500.0}),
    ("avisame cuando el dólar blue supere 1500",
     {"clase": "dolar", "activo": "blue", "op": ">=", "umbral": 1500.0}),
    ("notificame si el oficial baja de 1000",
     {"clase": "dolar", "activo": "oficial", "op": "<=", "umbral": 1000.0}),
    ("alerta cuando el mep pase de 1.450",
     {"clase": "dolar", "activo": "bolsa", "op": ">=", "umbral": 1450.0}),
    ("avisame si el ccl baja a 1200",
     {"clase": "dolar", "activo": "contadoconliqui", "op": "<=", "umbral": 1200.0}),
    # "dólar" sin casa -> blue por defecto
    ("avisame cuando el dolar supere 2000",
     {"clase": "dolar", "activo": "blue", "op": ">=", "umbral": 2000.0}),
    # multiplicador en palabra
    ("avisame cuando el blue llegue a 2 mil",
     {"clase": "dolar", "activo": "blue", "op": ">=", "umbral": 2000.0}),
])
def test_parseo_dolar(texto, esperado):
    w = parsear_watcher(texto)
    assert w is not None
    for k, v in esperado.items():
        assert w[k] == v


# ── Parseo: cripto ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("texto,esperado", [
    ("avisame cuando bitcoin supere los 70000",
     {"clase": "cripto", "activo": "bitcoin", "op": ">=", "umbral": 70000.0}),
    ("notificame si el btc baja de 60000",
     {"clase": "cripto", "activo": "bitcoin", "op": "<=", "umbral": 60000.0}),
    ("avisame cuando ethereum pase de 4000",
     {"clase": "cripto", "activo": "ethereum", "op": ">=", "umbral": 4000.0}),
    # typo frecuente + abreviatura "k"
    ("alerta si etherium baja de 3k",
     {"clase": "cripto", "activo": "ethereum", "op": "<=", "umbral": 3000.0}),
    ("avisame cuando el doge supere 1",
     {"clase": "cripto", "activo": "dogecoin", "op": ">=", "umbral": 1.0}),
    # cripto puntual tiene prioridad sobre "dólar" si ambos aparecen
    ("avisame cuando bitcoin en dolares supere 100k",
     {"clase": "cripto", "activo": "bitcoin", "op": ">=", "umbral": 100000.0}),
])
def test_parseo_cripto(texto, esperado):
    w = parsear_watcher(texto)
    assert w is not None
    for k, v in esperado.items():
        assert w[k] == v


# ── Parseo: casos que NO son watchers ───────────────────────────────────────────

@pytest.mark.parametrize("texto", [
    # falta el disparador (avisar/notificar/alertar)
    "a cuánto está el dólar blue",
    "el bitcoin supera los 70000",
    # falta el operador de cruce
    "avisame el precio del dólar",
    # falta el número
    "avisame cuando el blue suba",
    # activo desconocido
    "avisame cuando las acciones de apple suban a 200",
    "",
    "   ",
])
def test_no_es_watcher(texto):
    assert parsear_watcher(texto) is None


# ── Lógica de disparo (sin red, sin esperas) ────────────────────────────────────

@pytest.mark.parametrize("op,precio,umbral,esperado", [
    (">=", 1500, 1000, True),    # ya cruzó hacia arriba
    (">=", 950, 1000, False),    # todavía no llegó
    (">=", 1000, 1000, True),    # igualdad dispara
    ("<=", 950, 1000, True),     # ya cruzó hacia abajo
    ("<=", 1500, 1000, False),   # todavía está por encima
    ("<=", 1000, 1000, True),    # igualdad dispara
])
def test_cumple(op, precio, umbral, esperado):
    assert cumple(op, precio, umbral) is esperado


def test_op_invalido_no_dispara():
    assert cumple("==", 100, 100) is False


# ── Descripción legible ─────────────────────────────────────────────────────────

def test_describir_condicion():
    assert describir_condicion(">=", 1500, "dolar") == "supere los $1,500.00"
    assert describir_condicion("<=", 60000, "cripto") == "baje a USD 60,000.00"


# ── Cancelación en lenguaje natural ─────────────────────────────────────────────

def test_cancelar_todos():
    assert parsear_cancelacion("cancelá todos los centinelas") == {"tipo": "todos"}
    assert parsear_cancelacion("borrá todas las alertas de precio") == {"tipo": "todos"}


def test_cancelar_por_id():
    assert parsear_cancelacion("cancelá el centinela 2") == {"tipo": "id", "id": 2}
    assert parsear_cancelacion("borrá el centinela #3") == {"tipo": "id", "id": 3}
    assert parsear_cancelacion("sacá el centinela numero 4") == {"tipo": "id", "id": 4}
    # Regresión: Whisper transcribe "sentinela" (con S) por el seseo rioplatense.
    assert parsear_cancelacion("¿Me cancelas la sentinela 8?") == {"tipo": "id", "id": 8}


def test_cancelar_por_activo():
    c = parsear_cancelacion("cancelá el centinela del blue")
    assert c["tipo"] == "activo" and c["clase"] == "dolar" and c["activo"] == "blue"
    c = parsear_cancelacion("borrá la alerta de bitcoin")
    assert c["tipo"] == "activo" and c["clase"] == "cripto" and c["activo"] == "bitcoin"


def test_cancelar_generico():
    assert parsear_cancelacion("cancelá mi centinela") == {"tipo": "generico"}


@pytest.mark.parametrize("texto", [
    # falta el verbo de cancelar
    "mis centinelas",
    # no menciona centinela ni activo (no pisar cancelación de recordatorios)
    "cancelá la alerta 2",
    "cancelar recordatorio",
    "",
])
def test_no_es_cancelacion(texto):
    assert parsear_cancelacion(texto) is None
