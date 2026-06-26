import pytest
from msptc.optics.analytical import AnalyticalOptics

def make(cfg_optics=None, collector=None):
    optics = cfg_optics or {"reflectance": 0.935, "intercept": 0.92, "transmittance": 0.96,
                            "absorptance": 0.955, "cleanliness": 0.95, "iam_model": "eurotrough"}
    coll = collector or {"aperture_m": 5.77, "focal_m": 1.71, "sca_length_m": 150.0}
    return AnalyticalOptics(optics, coll)

def test_peak_efficiency_at_normal_incidence():
    m = make()
    peak = 0.935 * 0.92 * 0.96 * 0.955 * 0.95   # ρ·γ·τ·α·cleanliness
    assert m.efficiency(0.0) == pytest.approx(peak, rel=1e-6)

def test_iam_unity_at_zero():
    assert make().iam(0.0) == pytest.approx(1.0, rel=1e-9)

def test_efficiency_decreases_with_angle():
    m = make()
    assert m.efficiency(40.0) < m.efficiency(10.0) < m.efficiency(0.0)

def test_end_loss_below_one_at_angle():
    m = make()
    assert 0.9 < m.end_loss(20.0) < 1.0
    assert m.end_loss(0.0) == pytest.approx(1.0)

def test_absorbed_power_normal():
    m = make()
    expected = 900.0 * 1.0 * 5.77 * m.efficiency(0.0)
    assert m.absorbed_power_per_length(0.0, 900.0) == pytest.approx(expected, rel=1e-6)
