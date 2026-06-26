import warnings
import pytest
from pathlib import Path
from msptc.io import load_config
from msptc.htf import SolarSalt
from msptc.optics.analytical import AnalyticalOptics
from msptc.collector import Collector, CollectorResult

def build():
    cfg = load_config(str(Path(__file__).parent.parent / "config" / "default.json"))
    optics = AnalyticalOptics(cfg["optics"], cfg["collector"])
    return Collector(cfg, optics, SolarSalt())

def test_outlet_warmer_than_inlet_with_sun():
    c = build()
    r = c.simulate_steady(T_in_C=290.0, mdot=8.0, dni=900.0, theta_deg=10.0, T_amb_C=25.0, wind=3.0)
    assert isinstance(r, CollectorResult)
    assert r.T_out_C > 290.0
    assert 0.0 < r.eta_th < 1.0

def test_higher_dni_higher_outlet():
    c = build()
    lo = c.simulate_steady(290.0, 8.0, 500.0, 10.0, 25.0, 3.0)
    hi = c.simulate_steady(290.0, 8.0, 950.0, 10.0, 25.0, 3.0)
    assert hi.T_out_C > lo.T_out_C

def test_n_segments_refines_consistently():
    # 多段与单段结果接近(差<5K)
    c = build()
    r1 = c.simulate_steady(290.0, 8.0, 900.0, 10.0, 25.0, 3.0, n_segments=1)
    r10 = c.simulate_steady(290.0, 8.0, 900.0, 10.0, 25.0, 3.0, n_segments=10)
    assert abs(r1.T_out_C - r10.T_out_C) < 5.0


def test_outlet_clamped_at_htf_t_max():
    """极低流量下出口温度被裁剪至 HTF.T_max_C，无超温 warning，能量守恒。"""
    c = build()
    with warnings.catch_warnings():
        warnings.simplefilter("error")   # 任何 UserWarning 均变为错误
        r = c.simulate_steady(T_in_C=290.0, mdot=0.1, dni=900.0,
                              theta_deg=10.0, T_amb_C=25.0, wind=3.0,
                              n_segments=1)
    assert r.T_out_C <= SolarSalt.T_max_C
    assert r.T_out_C > 290.0
    # 能量守恒：Q_useful ≈ mdot × cp(T_mid) × ΔT
    htf = SolarSalt()
    cp_mid = htf.cp(0.5 * (290.0 + r.T_out_C))
    assert r.Q_useful_W == pytest.approx(0.1 * cp_mid * (r.T_out_C - 290.0), rel=0.02)
