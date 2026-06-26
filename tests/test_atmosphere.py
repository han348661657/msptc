import pytest
from msptc.atmosphere import air_pressure, AirProperties, sky_temp_C


def test_air_pressure_sea_level_and_altitude():
    assert air_pressure(0.0) == pytest.approx(101325.0, rel=1e-6)
    assert air_pressure(2801.0) == pytest.approx(71900.0, rel=0.02)   # 格尔木


def test_air_density_decreases_with_altitude():
    a0, a3 = AirProperties(0.0), AirProperties(2801.0)
    assert a0.rho(27.0) > a3.rho(27.0)
    assert a0.rho(26.85) == pytest.approx(1.177, rel=0.02)            # 海平面 300K


def test_kinematic_viscosity_matches_legacy_constant_at_sea_level():
    a0 = AirProperties(0.0)
    assert a0.nu(26.85) == pytest.approx(1.6e-5, rel=0.05)            # 旧 NU_AIR


def test_kinematic_viscosity_higher_at_altitude():
    a0, a3 = AirProperties(0.0), AirProperties(2801.0)
    assert a3.nu(26.85) / a0.nu(26.85) == pytest.approx(1.41, rel=0.05)


def test_thermal_conductivity_matches_legacy_at_sea_level():
    assert AirProperties(0.0).k(26.85) == pytest.approx(0.026, rel=0.05)  # 旧 K_AIR


def test_prandtl_pressure_independent():
    a0, a3 = AirProperties(0.0), AirProperties(2801.0)
    assert a0.prandtl(26.85) == pytest.approx(a3.prandtl(26.85), rel=1e-9)
    assert a0.prandtl(26.85) == pytest.approx(0.7, rel=0.06)          # 旧 PR_AIR


def test_sky_temp_below_ambient_clear_sky():
    assert sky_temp_C(25.0) < 25.0
    assert 5.0 < (25.0 - sky_temp_C(25.0)) < 30.0
