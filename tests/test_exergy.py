import pytest
from msptc.exergy import (solar_exergy_W, thermal_exergy_W,
                          exergy_breakdown, exergy_balance_closes)


def test_petela_factor_about_093():
    assert solar_exergy_W(1.0e6, 25.0) == pytest.approx(0.933e6, rel=0.01)


def test_thermal_exergy_zero_below_ambient():
    assert thermal_exergy_W(1.0e6, 20.0, 25.0) == 0.0


def test_higher_source_temp_more_exergy():
    assert thermal_exergy_W(1.0e6, 540.0, 25.0) > thermal_exergy_W(1.0e6, 390.0, 25.0)


def test_breakdown_balance_closes():
    bd = exergy_breakdown(Q_solar_W=2.0e6, Q_useful_W=1.2e6, T_field_m_C=415.0,
                          T_to_PB_C=400.0, W_elec_W=0.42e6, T_0_C=25.0)
    assert exergy_balance_closes(bd, 0.42e6)
    assert 0.0 < bd["eta_exergy"] < 0.5


def test_indirect_storage_destroys_exergy():
    # T_to_PB < T_field_m(间接储热双重 approach) → 储热㶲损 > 0
    bd = exergy_breakdown(2.0e6, 1.2e6, 415.0, 360.0, 0.40e6, 25.0)
    assert bd["dest_storage_W"] > 0
