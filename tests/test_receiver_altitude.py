import pytest
from msptc.receiver import hce_steady, make_ptr70_geom
from msptc.atmosphere import AirProperties
from msptc.htf import SolarSalt


def _loss(air, sky_model):
    geom, salt = make_ptr70_geom(), SolarSalt()
    return hce_steady(400.0, 8.0, 12000.0, 10.0, 3.0, geom, salt,
                      air=air, sky_model=sky_model).q_loss_per_m


def test_sea_level_air_reproduces_legacy_within_tolerance():
    geom, salt = make_ptr70_geom(), SolarSalt()
    legacy = hce_steady(400.0, 8.0, 12000.0, 10.0, 3.0, geom, salt).q_loss_per_m
    sea = hce_steady(400.0, 8.0, 12000.0, 10.0, 3.0, geom, salt,
                     air=AirProperties(0.0)).q_loss_per_m
    assert sea == pytest.approx(legacy, rel=0.05)


def test_altitude_reduces_glass_convective_loss():
    assert _loss(AirProperties(2801.0), None) < _loss(AirProperties(0.0), None)


def test_swinbank_sky_increases_radiative_loss_vs_offset():
    geom, salt = make_ptr70_geom(), SolarSalt()
    off = hce_steady(400.0, 8.0, 12000.0, 0.0, 3.0, geom, salt, sky_model="offset8").q_loss_per_m
    swin = hce_steady(400.0, 8.0, 12000.0, 0.0, 3.0, geom, salt, sky_model="swinbank").q_loss_per_m
    assert swin > off
