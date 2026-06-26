import pytest
from msptc.freeze import freeze_guard_temp_C, freeze_parasitic_W
from msptc.receiver import make_ptr70_geom
from msptc.htf import SolarSalt, TherminolVP1

GEOM = make_ptr70_geom()
L = 600.0


def test_guard_temp():
    assert freeze_guard_temp_C(SolarSalt()) == pytest.approx(250.0)
    assert freeze_guard_temp_C(TherminolVP1()) == pytest.approx(24.0)


def test_no_penalty_when_not_idle():
    assert freeze_parasitic_W(SolarSalt(), GEOM, -10.0, 3.0, L, idle=False) == 0.0


def test_no_penalty_when_warm():
    assert freeze_parasitic_W(SolarSalt(), GEOM, 300.0, 3.0, L, idle=True) == 0.0
    assert freeze_parasitic_W(TherminolVP1(), GEOM, 30.0, 3.0, L, idle=True) == 0.0


def test_salt_penalty_much_larger_than_oil():
    salt = freeze_parasitic_W(SolarSalt(), GEOM, -10.0, 3.0, L, idle=True)
    oil = freeze_parasitic_W(TherminolVP1(), GEOM, -10.0, 3.0, L, idle=True)
    assert salt > 0
    assert salt > oil


def test_colder_ambient_increases_penalty():
    warm = freeze_parasitic_W(SolarSalt(), GEOM, 20.0, 3.0, L, idle=True, sky_model="swinbank")
    cold = freeze_parasitic_W(SolarSalt(), GEOM, -20.0, 3.0, L, idle=True, sky_model="swinbank")
    assert cold > warm
