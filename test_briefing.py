"""Tests del parser de briefing (módulo ``briefing``).

    pytest test_briefing.py -v
"""

import pytest

from briefing import parsear_briefing


@pytest.mark.parametrize("texto,hora", [
    ("mandame el resumen diario a las 9", "09:00"),
    ("activá el resumen financiero a las 9:30", "09:30"),
    ("quiero el briefing todos los días a las 21", "21:00"),
    ("mandame el resumen del día a las 16:10", "16:10"),
    ("resumen de mercado a las 8hs", "08:00"),
])
def test_activar_con_hora(texto, hora):
    assert parsear_briefing(texto) == {"accion": "activar", "hora": hora}


@pytest.mark.parametrize("texto", [
    "mandame el briefing",
    "mandame el resumen financiero ahora",
    "quiero ver el resumen del día ya",
])
def test_ahora(texto):
    assert parsear_briefing(texto) == {"accion": "ahora"}


@pytest.mark.parametrize("texto", [
    "desactivá el resumen diario",
    "cancelá el briefing",
    "no me mandes más el resumen diario",
])
def test_desactivar(texto):
    assert parsear_briefing(texto) == {"accion": "desactivar"}


@pytest.mark.parametrize("texto", [
    # "resumen de gastos" es otra feature, no el briefing
    "resumen de mis gastos",
    "mostrame mis gastos",
    "a cuánto está el dólar",
    "",
])
def test_no_es_briefing(texto):
    assert parsear_briefing(texto) is None


def test_hora_invalida_no_activa():
    # 25:00 no es hora válida -> no se interpreta como activación
    assert parsear_briefing("mandame el resumen diario a las 25") == {"accion": "ahora"}
