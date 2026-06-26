import pytest
from msptc.storage import TwoTankStorage
from msptc.htf import SolarSalt
from msptc.atmosphere import AirProperties

CFG = {"storage": {"hours": 6.0, "dT_approach_C": 15.0, "tank_UA_W_K": 5000.0,
                   "solar_multiple": 1.0, "tank_conv_frac": 0.5}}


def _charged():
    s = TwoTankStorage(CFG, SolarSalt(), P_thermal_rated_W=1.0e6, indirect=False)
    s.charge(T_field_hot_C=540.0, Q_avail_W=1.0e7, dt_s=3600.0)   # 充满
    return s


def test_tank_loss_sea_level_matches_legacy():
    legacy = _charged().apply_losses(10.0, 60.0)
    sea = _charged().apply_losses(10.0, 60.0, air=AirProperties(0.0))
    assert sea == pytest.approx(legacy, rel=1e-6)


def test_altitude_reduces_tank_loss():
    loss_sea = _charged().apply_losses(10.0, 60.0, air=AirProperties(0.0))
    loss_alt = _charged().apply_losses(10.0, 60.0, air=AirProperties(2801.0))
    assert loss_alt < loss_sea


def test_collector_accepts_air_and_reduces_loss():
    # 直接构造 Collector (build_collector 的 air 形参在后续 Task 才加)
    from pathlib import Path
    from msptc.io import load_config
    from msptc.collector import Collector
    from msptc.optics.analytical import AnalyticalOptics
    from msptc.htf import make_htf
    cfg = load_config(str(Path(__file__).parent.parent / "config" / "default.json"))

    def _coll(elev):
        return Collector(cfg, AnalyticalOptics(cfg["optics"], cfg["collector"]),
                         make_htf("solar_salt"), air=AirProperties(elev))

    r_sea = _coll(0.0).simulate_steady(290.0, 8.0, 900.0, 0.0, 10.0, 3.0)
    r_alt = _coll(2801.0).simulate_steady(290.0, 8.0, 900.0, 0.0, 10.0, 3.0)
    assert r_alt.Q_loss_W < r_sea.Q_loss_W
