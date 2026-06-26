# tests/test_optics_intercept_model.py
import pytest
from msptc.optics.analytical import AnalyticalOptics

FIXED = {"reflectance": 0.935, "intercept": 0.92, "transmittance": 0.96,
         "absorptance": 0.955, "cleanliness": 0.95, "iam_model": "eurotrough"}
COLL = {"aperture_m": 5.77, "focal_m": 1.71, "sca_length_m": 150.0}
RECV = {"d_abs_out_m": 0.070}
EB = {"sigma_sun_mrad": 2.8, "sigma_slope_grav_mrad": 2.5,
      "sigma_spec_mrad": 1.0, "sigma_track_mrad": 1.0}
WIND = {"couple_altitude": True, "c_w": 1.7e-5, "aperture_exp": 1.5, "w_ref_m": 5.77}


def test_fixed_model_unchanged():
    # 缺省 fixed：γ = config 定值 0.92（向后兼容，旧 2 参调用仍可用）
    m = AnalyticalOptics(FIXED, COLL)
    assert m.intercept == pytest.approx(0.92)
    assert m.efficiency(0.0) == pytest.approx(0.935 * 0.92 * 0.96 * 0.955 * 0.95, rel=1e-6)


def test_error_cone_model_computes_gamma():
    optics = {**FIXED, "intercept_model": "error_cone", "error_budget": EB}
    m = AnalyticalOptics(optics, COLL, RECV)
    assert m.intercept == pytest.approx(0.991, abs=3e-3)   # 误差锥 γ 替换定值


def test_error_cone_altitude_raises_gamma():
    optics = {**FIXED, "intercept_model": "error_cone", "error_budget": EB}
    coll86 = {"aperture_m": 8.6, "focal_m": 2.56, "sca_length_m": 150.0}
    sea = AnalyticalOptics(optics, coll86, RECV, rho_air=1.177, v_wind=10.0, wind_cfg=WIND)
    alt = AnalyticalOptics(optics, coll86, RECV, rho_air=0.835, v_wind=10.0, wind_cfg=WIND)
    assert alt.intercept > sea.intercept


import copy
from msptc.io import load_config
from msptc.atmosphere import AirProperties
from msptc.system import build_collector


def test_build_collector_fixed_default_backward_compat():
    cfg = load_config("config/default.json")
    coll = build_collector(cfg, "solar_salt")           # 旧两参调用
    assert coll.optics.intercept == pytest.approx(0.92)


def test_build_collector_error_cone_with_altitude():
    cfg = copy.deepcopy(load_config("config/default.json"))
    cfg["optics"]["intercept_model"] = "error_cone"
    cfg["collector"].update({"aperture_m": 8.6, "focal_m": 2.56})
    cfg["receiver"]["d_abs_out_m"] = 0.090
    cfg["wind"]["c_w"] = 1.7e-5
    sea = build_collector(cfg, "solar_salt", air=AirProperties(0))
    alt = build_collector(cfg, "solar_salt", air=AirProperties(2801))
    assert alt.optics.intercept > sea.optics.intercept   # 海拔协同贯通到 Collector
