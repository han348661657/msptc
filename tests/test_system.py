import pytest
from pathlib import Path
from msptc.io import load_config
from msptc.htf import make_htf
from msptc.optics.analytical import AnalyticalOptics
from msptc.collector import Collector
from msptc.system import required_mdot, design_point

CFG = load_config(str(Path(__file__).parent.parent / "config" / "default.json"))


def _collector(htf_type):
    htf = make_htf(htf_type)
    return Collector(CFG, AnalyticalOptics(CFG["optics"], CFG["collector"]), htf)


def test_required_mdot_hits_target_outlet():
    coll = _collector("solar_salt")
    mdot = required_mdot(coll, T_in_C=290.0, T_target_C=500.0,
                         dni=900.0, theta_deg=0.0, T_amb_C=25.0, wind=3.0)
    out = coll.simulate_steady(290.0, mdot, 900.0, 0.0, 25.0, 3.0).T_out_C
    assert out == pytest.approx(500.0, abs=1.0)


def test_design_point_salt_more_electric_efficient_than_oil():
    salt = design_point(CFG, "solar_salt", T_hot_C=540.0)
    oil = design_point(CFG, "therminol_vp1", T_hot_C=390.0)
    # 熔盐发电环节效率更高
    assert salt["eta_pb_gross"] > oil["eta_pb_gross"]
    # 两者太阳能-电效率均为合理正值
    for d in (salt, oil):
        assert 0.0 < d["eta_solar_to_elec"] < 0.45


def test_design_point_returns_expected_keys():
    d = design_point(CFG, "solar_salt", T_hot_C=540.0)
    for key in ("htf_type", "mdot_kg_s", "T_to_PB_C", "Q_useful_W",
                "eta_field", "eta_pb_gross", "eta_pb_net",
                "P_elec_W", "eta_solar_to_elec"):
        assert key in d
