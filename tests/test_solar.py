import math
from datetime import datetime
import pytest
from msptc.solar import solar_position, incidence_angle, dni_clear_sky, SunState

SITE = {"lat_deg": 38.0, "lon_deg": 100.0, "elev_m": 3000,
        "pressure_hpa": 700, "water_vapour_cm": 0.5, "ozone_atmcm": 0.3,
        "no2_atmcm": 0.0002, "aod550": 0.05, "angstrom": 1.3, "albedo": 0.2}

def test_solar_position_summer_noon_low_zenith():
    # 2025-06-21 约当地正午(UTC≈04:20 @ lon100E)
    s = solar_position(datetime(2025, 6, 21, 4, 20), SITE)
    assert isinstance(s, SunState)
    assert 0 <= s.zenith_deg < 30     # 夏至高原正午太阳很高
    assert 20 < s.declination_deg < 24

def test_incidence_angle_in_unit_range():
    s = solar_position(datetime(2025, 6, 21, 4, 20), SITE)
    for axis in ("NS", "EW"):
        theta = incidence_angle(s, axis)
        assert 0.0 <= theta <= 90.0

def test_ns_axis_noon_equals_zenith():
    # 正午 ω≈0 时 NS 轴入射角 ≈ 天顶角
    # lon=100E 真太阳正午约 UTC 05:20（solar noon = 12:00 - 100/15h ≈ 05:20 UTC）
    s = solar_position(datetime(2025, 6, 21, 5, 20), SITE)
    theta_ns = incidence_angle(s, "NS")
    assert theta_ns == pytest.approx(s.zenith_deg, abs=3.0)

def test_dni_clear_sky_daytime_positive():
    s = solar_position(datetime(2025, 6, 21, 4, 20), SITE)
    dni = dni_clear_sky(s.zenith_deg, SITE)
    assert 300 < dni < 1100
