import pytest
from msptc.htf import SolarSalt, TherminolVP1, make_htf

salt = SolarSalt()

def test_density_at_300C():
    assert salt.rho(300.0) == pytest.approx(1899.2, rel=1e-3)   # 2090-0.636*300

def test_cp_at_300C():
    assert salt.cp(300.0) == pytest.approx(1494.6, rel=1e-3)    # 1443+0.172*300

def test_viscosity_at_500C_positive_and_small():
    mu = salt.mu(500.0)
    assert 0.5e-3 < mu < 5e-3        # ~1.3e-3 Pa·s

def test_conductivity_at_400C():
    assert salt.k(400.0) == pytest.approx(0.519, rel=1e-3)      # 0.443+1.9e-4*400

def test_prandtl_positive():
    assert salt.prandtl(400.0) > 0

def test_out_of_range_warns():
    with pytest.warns(UserWarning):
        salt.rho(700.0)

def test_freeze_point():
    assert salt.freeze_point_C == pytest.approx(238.0, abs=1.0)


def test_therminol_density_matches_datasheet():
    oil = TherminolVP1()
    # 数据表: 100°C ρ~999, 300°C ρ~817 kg/m³
    assert abs(oil.rho(100.0) - 999.0) < 5.0
    assert abs(oil.rho(300.0) - 817.0) < 5.0


def test_therminol_cp_increases_with_temperature():
    oil = TherminolVP1()
    assert oil.cp(300.0) > oil.cp(100.0)


def test_therminol_prandtl_positive():
    oil = TherminolVP1()
    assert oil.prandtl(200.0) > 0


def test_therminol_limits():
    oil = TherminolVP1()
    assert oil.freeze_point_C == 12.0
    assert oil.T_max_C == 400.0


def test_therminol_warns_above_max():
    oil = TherminolVP1()
    with pytest.warns(UserWarning):
        oil.rho(450.0)


def test_therminol_viscosity_order_of_magnitude():
    oil = TherminolVP1()
    mu = oil.mu(100.0)
    # Formula has known high-T limitations; check order-of-magnitude at 100°C
    assert 0.5e-3 < mu < 2.0e-3


def test_make_htf_factory():
    assert isinstance(make_htf("solar_salt"), SolarSalt)
    assert isinstance(make_htf("therminol_vp1"), TherminolVP1)
    with __import__("pytest").raises(ValueError):
        make_htf("unknown_fluid")


# --- P1: Therminol VP-1 物性精度（参考: Forristall 2003 Table 3.1 + 数据表锚点）---

_VP1_TABLE_31 = [  # (T°C, cp J/kgK, mu Pa·s, k W/mK) — Forristall Table 3.1
    (172, 1970, 4.86e-4, 0.1180),
    (182, 2000, 4.50e-4, 0.1165),
    (192, 2030, 4.18e-4, 0.1150),
    (202, 2050, 3.89e-4, 0.1135),
    (212, 2080, 3.64e-4, 0.1119),
    (222, 2110, 3.41e-4, 0.1103),
]


def test_therminol_cp_high_temp_corrected():
    # 旧 4 次式在 390°C 给出 ~2595 J/kgK(+7.8%)，新式应回到数据表 ~2410
    oil = TherminolVP1()
    assert oil.cp(390.0) == pytest.approx(2410.0, rel=0.03)


def test_therminol_cp_matches_table31():
    oil = TherminolVP1()
    for T, cp_ref, _mu, _k in _VP1_TABLE_31:
        assert oil.cp(T) == pytest.approx(cp_ref, rel=0.02)


def test_therminol_mu_high_temp_corrected():
    # 旧 VFT 在 390°C 给出 ~2.19e-4 Pa·s(+~90%)，新式应回到数据表 ~1.14e-4
    oil = TherminolVP1()
    assert oil.mu(390.0) == pytest.approx(1.14e-4, rel=0.10)


def test_therminol_mu_matches_table31():
    oil = TherminolVP1()
    for T, _cp, mu_ref, _k in _VP1_TABLE_31:
        assert oil.mu(T) == pytest.approx(mu_ref, rel=0.10)


def test_therminol_k_high_temp_corrected():
    # 旧 3 次式在 390°C 给出 ~0.0780 W/mK(-9%)，新式应回到数据表 ~0.0857
    oil = TherminolVP1()
    assert oil.k(390.0) == pytest.approx(0.0857, rel=0.03)


def test_therminol_k_matches_table31():
    oil = TherminolVP1()
    for T, _cp, _mu, k_ref in _VP1_TABLE_31:
        assert oil.k(T) == pytest.approx(k_ref, rel=0.02)
