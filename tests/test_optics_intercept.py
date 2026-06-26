# tests/test_optics_intercept.py
import math
import pytest
from msptc.optics.intercept import rim_angle, concentration


def test_rim_angle_eurotrough():
    # W=5.77, f=1.71 → φ_r ≈ 80.3°（EuroTrough 实际 ~80°）
    assert math.degrees(rim_angle(5.77, 1.71)) == pytest.approx(80.30, abs=0.1)


def test_concentration_values():
    assert concentration(5.77, 0.070) == pytest.approx(26.24, abs=0.05)
    assert concentration(8.6, 0.070) == pytest.approx(39.11, abs=0.05)
    assert concentration(8.6, 0.090) == pytest.approx(30.42, abs=0.05)


from msptc.optics.intercept import intercept_factor, sigma_total

# 误差预算 mrad: sun=2.8, slope=2.5(×2), spec=1.0, track=1.0 → σ_tot≈5.903 mrad
SIGMA = sigma_total(2.8e-3, 2.5e-3, 1.0e-3, 1.0e-3)   # 返回 rad


def test_sigma_total_quadrature():
    # √(2.8² + (2·2.5)² + 1² + 1²) = 5.903 mrad
    assert SIGMA == pytest.approx(5.903e-3, abs=1e-5)


def test_intercept_eurotrough_baseline():
    g = intercept_factor(5.77, 1.71, 0.070, SIGMA)
    assert g == pytest.approx(0.991, abs=3e-3)


def test_intercept_drops_with_aperture():
    # 同误差、同吸热管，开口加大 → γ 下降（光学惩罚）
    g_small = intercept_factor(5.77, 1.71, 0.070, SIGMA)
    g_large = intercept_factor(8.6, 2.56, 0.070, SIGMA)
    assert g_large < g_small
    assert g_large == pytest.approx(0.934, abs=4e-3)


def test_intercept_recovers_with_larger_receiver():
    # 8.6 m 配 PTR90(90mm) 比 PTR70(70mm) 截距回升
    g70 = intercept_factor(8.6, 2.56, 0.070, SIGMA)
    g90 = intercept_factor(8.6, 2.56, 0.090, SIGMA)
    assert g90 > g70
    assert g90 == pytest.approx(0.979, abs=4e-3)


def test_intercept_drops_with_error():
    assert intercept_factor(5.77, 1.71, 0.070, 9e-3) < \
           intercept_factor(5.77, 1.71, 0.070, 4e-3)


def test_intercept_bias_reduces_gamma():
    # 非随机指向偏置降低 γ
    base = intercept_factor(5.77, 1.71, 0.070, SIGMA)
    biased = intercept_factor(5.77, 1.71, 0.070, SIGMA, track_bias_rad=3e-3)
    assert biased < base
    assert 0.0 < biased <= 1.0


def test_intercept_in_unit_interval():
    assert 0.0 < intercept_factor(8.6, 2.56, 0.070, SIGMA) <= 1.0


from msptc.optics.intercept import effective_intercept

OPTICS = {"intercept_model": "error_cone",
          "error_budget": {"sigma_sun_mrad": 2.8, "sigma_slope_grav_mrad": 2.5,
                           "sigma_spec_mrad": 1.0, "sigma_track_mrad": 1.0}}
COLL_577 = {"aperture_m": 5.77, "focal_m": 1.71}
COLL_86 = {"aperture_m": 8.6, "focal_m": 2.56}
RECV_70 = {"d_abs_out_m": 0.070}
WIND = {"couple_altitude": True, "c_w": 1.7e-5, "aperture_exp": 1.5, "w_ref_m": 5.77}


def test_effective_intercept_no_wind_matches_baseline():
    g = effective_intercept(OPTICS, COLL_577, RECV_70)
    assert g == pytest.approx(0.991, abs=3e-3)


def test_effective_intercept_altitude_synergy():
    # 8.6m 大开口：高原(ρ低→风载低) γ 高于海平面 —— 论文协同主结论方向
    g_sea = effective_intercept(OPTICS, COLL_86, RECV_70, rho_air=1.177, v_wind=10.0, wind_cfg=WIND)
    g_alt = effective_intercept(OPTICS, COLL_86, RECV_70, rho_air=0.835, v_wind=10.0, wind_cfg=WIND)
    assert g_alt > g_sea


def test_effective_intercept_wind_off_when_cw_none():
    wind_off = {**WIND, "c_w": None}
    g_sea = effective_intercept(OPTICS, COLL_86, RECV_70, rho_air=1.177, v_wind=10.0, wind_cfg=wind_off)
    g_alt = effective_intercept(OPTICS, COLL_86, RECV_70, rho_air=0.835, v_wind=10.0, wind_cfg=wind_off)
    assert g_sea == pytest.approx(g_alt, abs=1e-9)   # 无风载 → 海拔不影响 γ
