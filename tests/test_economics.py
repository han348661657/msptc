import pytest
from msptc.economics import crf, storage_unit_cost, capex_total, lcoe

ECON = {"field_cost_per_m2": 170.0, "storage_cost_per_kWhth": 22.0,
        "oil_salt_hx_cost_per_kWhth": 10.0, "powerblock_cost_per_MW": 1.1e6}


def test_crf_known_values():
    assert crf(0.08, 25) == pytest.approx(0.09368, rel=1e-3)
    assert crf(0.0, 25) == pytest.approx(0.04)


def test_indirect_storage_costs_more():
    assert storage_unit_cost(ECON, indirect=True) > storage_unit_cost(ECON, indirect=False)
    assert storage_unit_cost(ECON, indirect=False) == 22.0


def test_capex_positive():
    cx = capex_total(ECON, aperture_area_m2=5000.0, storage_kWhth=1.0e4,
                     P_elec_rated_MW=2.0, indirect=False)
    assert cx > 0


def test_lcoe_value_and_zero_guard():
    assert lcoe(1.0e8, 2.0e6, 3000.0, 0.08, 25) == pytest.approx(3789.0, rel=0.01)
    assert lcoe(1.0e8, 2.0e6, 0.0, 0.08, 25) == float("inf")
