# tests/test_wind_deflection.py
import pytest
from msptc.optics.wind_deflection import sigma_slope_wind, dynamic_pressure


def test_dynamic_pressure():
    # q = ½·ρ·v² ; ρ=1.177, v=10 → 58.85 Pa
    assert dynamic_pressure(1.177, 10.0) == pytest.approx(58.85, abs=0.1)


def test_wind_slope_reference_calibration():
    # 参考开口、海平面、设计风速：σ_wind = c_w·q·1 = 1.7e-5·58.85 ≈ 1.0 mrad
    s = sigma_slope_wind(1.177, 10.0, 5.77, c_w=1.7e-5, aperture_exp=1.5, w_ref_m=5.77)
    assert s == pytest.approx(1.0e-3, abs=5e-5)


def test_wind_slope_increases_with_aperture():
    small = sigma_slope_wind(1.177, 10.0, 5.77, c_w=1.7e-5, aperture_exp=1.5, w_ref_m=5.77)
    large = sigma_slope_wind(1.177, 10.0, 8.6, c_w=1.7e-5, aperture_exp=1.5, w_ref_m=5.77)
    assert large > small


def test_wind_slope_lower_at_altitude():
    # 高原空气密度低 → 动压低 → 风致斜率误差低（协同入口）
    sea = sigma_slope_wind(1.177, 10.0, 8.6, c_w=1.7e-5, aperture_exp=1.5, w_ref_m=5.77)
    alt = sigma_slope_wind(0.835, 10.0, 8.6, c_w=1.7e-5, aperture_exp=1.5, w_ref_m=5.77)
    assert alt < sea
    assert alt / sea == pytest.approx(0.835 / 1.177, abs=1e-6)   # ∝ ρ


def test_wind_slope_zero_when_disabled():
    # c_w=None → 风载项关闭（回退纯重力）
    assert sigma_slope_wind(1.177, 10.0, 8.6, c_w=None, aperture_exp=1.5, w_ref_m=5.77) == 0.0
