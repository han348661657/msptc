from scripts.run_altitude_sweep import run_altitude_sweep, design_point_at_elev
from msptc.io import load_config

CFG = load_config("config/default.json")


def test_sweep_produces_rows_for_each_elevation(tmp_path):
    df = run_altitude_sweep(outdir=str(tmp_path), elevations=[0, 2801])
    assert set(df["elev_m"]) == {0, 2801}
    assert set(df["htf_type"]) == {"solar_salt", "therminol_vp1"}


def test_altitude_reduces_field_heat_loss():
    sea = design_point_at_elev(CFG, "solar_salt", 540.0, 0)
    alt = design_point_at_elev(CFG, "solar_salt", 540.0, 2801)
    assert alt["Q_loss_W"] < sea["Q_loss_W"]


def test_salt_more_efficient_than_oil_at_all_altitudes():
    for e in (0, 2801, 4000):
        salt = design_point_at_elev(CFG, "solar_salt", 540.0, e)
        oil = design_point_at_elev(CFG, "therminol_vp1", 390.0, e)
        assert salt["eta_solar_to_elec"] > oil["eta_solar_to_elec"]
