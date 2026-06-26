import pytest
from msptc.htf import SolarSalt
from msptc.receiver import (
    hce_steady, HCEResult, ReceiverGeom,
    hce_loss_empirical, eps_abs_PTR70, make_ptr70_geom,
)

# PTR70 标准几何 (Burkholder 2009 p.12): d_abs 66/70mm, d_glass 114/120mm, eps_glass=0.89
GEOM = ReceiverGeom(d_abs_in_m=0.066, d_abs_out_m=0.070,
                    d_glass_in_m=0.114, d_glass_out_m=0.120,
                    eps_abs=0.10, eps_glass=0.89, vacuum=True)
SALT = SolarSalt()


# ── hce_steady 基本物理 ────────────────────────────────────────────────

def test_hce_energy_balance_closes():
    r = hce_steady(T_htf_C=400.0, mdot=8.0, q_abs_per_m=3000.0,
                   T_amb_C=25.0, wind=3.0, geom=GEOM, htf=SALT)
    assert isinstance(r, HCEResult)
    assert r.q_useful_per_m + r.q_loss_per_m == pytest.approx(3000.0, rel=1e-3)
    assert r.q_loss_per_m > 0
    assert r.T_abs_C > 400.0

def test_hce_loss_increases_with_temperature():
    lo = hce_steady(300.0, 8.0, 3000.0, 25.0, 3.0, GEOM, SALT)
    hi = hce_steady(500.0, 8.0, 3000.0, 25.0, 3.0, GEOM, SALT)
    assert hi.q_loss_per_m > lo.q_loss_per_m

def test_hce_zero_solar_gives_negative_useful():
    r = hce_steady(400.0, 8.0, 0.0, 25.0, 3.0, GEOM, SALT)
    assert r.q_useful_per_m < 0


# ── hce_loss_empirical：公式验证 (Burkholder 2009 Table 3, ±10 W/m 不确定度) ──

@pytest.mark.parametrize("T_abs_C, expected_Wm", [
    (100.0, 15.0),   # PTR70 #1 Test 1: 15 W/m
    (346.0, 141.0),  # PTR70 #1 Test 6: 141 W/m
    (506.0, 495.0),  # PTR70 #1 Test 11: 495 W/m
])
def test_ptr70_empirical_vs_burkholder_table3(T_abs_C, expected_Wm):
    """Burkholder (2009) Table 3 实测值，不确定度 ±10 W/m。"""
    hl = hce_loss_empirical(T_abs_C)
    assert abs(hl - expected_Wm) < 10.0, f"T={T_abs_C}°C: got {hl:.1f} W/m, expected {expected_Wm} ±10"

def test_ptr70_loss_monotonic():
    assert hce_loss_empirical(500.0) > hce_loss_empirical(300.0)


# ── 温度相关发射率 eps_abs_PTR70 ────────────────────────────────────────

def test_eps_abs_ptr70_at_100C():
    # ε = 0.062 + 2e-7 × 100² = 0.062 + 0.002 = 0.064
    assert eps_abs_PTR70(100.0) == pytest.approx(0.064, abs=1e-6)

def test_eps_abs_ptr70_increases_with_temperature():
    assert eps_abs_PTR70(400.0) > eps_abs_PTR70(200.0) > eps_abs_PTR70(100.0)


# ── make_ptr70_geom + callable eps_abs 集成 ─────────────────────────────

def test_make_ptr70_geom_callable_emittance():
    geom_td = make_ptr70_geom()
    assert callable(geom_td.eps_abs)
    r = hce_steady(400.0, 8.0, 3000.0, 25.0, 3.0, geom_td, SALT)
    assert r.q_useful_per_m + r.q_loss_per_m == pytest.approx(3000.0, rel=1e-3)

def test_make_ptr70_geom_fixed_emittance():
    geom_fixed = make_ptr70_geom(eps_abs=0.10)
    assert not callable(geom_fixed.eps_abs)
    r = hce_steady(400.0, 8.0, 3000.0, 25.0, 3.0, geom_fixed, SALT)
    assert r.q_useful_per_m + r.q_loss_per_m == pytest.approx(3000.0, rel=1e-3)
