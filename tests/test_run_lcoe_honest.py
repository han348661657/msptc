from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import matplotlib.pyplot as plt

from scripts import run_lcoe_honest


def test_honest_lcoe_figure_highlights_six_hour_reversal():
    hours = [0, 3, 6, 9]
    cs = {
        "solar_salt": [570, 491, 480, 504],
        "therminol_vp1": [569, 523, 539, 590],
    }
    tm = {
        "solar_salt": [1396, 1100, 1040, 1065],
        "therminol_vp1": [945, 868, 891, 958],
    }
    dec = {
        "solar_salt": [480, 796, 1040],
        "therminol_vp1": [539, 883, 891],
    }

    fig = run_lcoe_honest._build_honest_lcoe_figure(hours, cs, tm, dec)
    try:
        axa, axb = fig.axes
        assert any(line.get_linestyle() == ":" for line in axa.lines)
        assert any("6 h reversal" in text.get_text() for text in axa.texts)
        assert any("oil lower" in text.get_text() for text in axb.texts)
    finally:
        plt.close(fig)


def test_run_lcoe_honest_exports_decomposition_and_guard_sensitivity(tmp_path, monkeypatch):
    fake_tmy = SimpleNamespace(
        site={"lat_deg": 36.42, "lon_deg": 94.90, "elev_m": 2801},
        records=[
            SimpleNamespace(
                dt_utc=datetime(2023, 1, 1, 0, 30, tzinfo=timezone.utc),
                dni=0.0,
                t_amb_C=-10.0,
                wind=3.0,
            )
        ],
    )
    monkeypatch.setattr(run_lcoe_honest, "load_tmy3", lambda _: fake_tmy)

    def fake_lcoe_one(cfg, htf, T_hot, indirect, hours, site, records, air, sky,
                      account_freeze, guard):
        is_tmy = isinstance(records, list)
        base = 400.0 + hours * 10.0 + (40.0 if htf == "therminol_vp1" else 0.0)
        weather_penalty = 100.0 if is_tmy else 0.0
        freeze_penalty = guard * (8.0 if htf == "solar_salt" else 1.0) if account_freeze else 0.0
        return base + weather_penalty + freeze_penalty

    monkeypatch.setattr(run_lcoe_honest, "_lcoe_one", fake_lcoe_one)

    run_lcoe_honest.run(outdir=str(tmp_path), pdf=False, sensitivity_guards=[0.0, 12.0])

    decomposition = pd.read_csv(tmp_path / "Table_09_lcoe_decomposition.csv")
    assert set(decomposition["basis"]) == {
        "clear_sky_freeze_excluded",
        "tmy_freeze_excluded",
        "tmy_freeze_included",
    }
    assert set(decomposition["htf_type"]) == {"solar_salt", "therminol_vp1"}
    assert set(decomposition["storage_hours"]) == {6}
    assert "LCOE_CNY_MWh" in decomposition.columns

    sensitivity = pd.read_csv(tmp_path / "Table_10_freeze_guard_sensitivity.csv")
    assert set(sensitivity["guard_margin_C"]) == {0.0, 12.0}
    assert set(sensitivity["htf_type"]) == {"solar_salt", "therminol_vp1"}
    assert set(sensitivity["storage_hours"]) == {3, 6}
    assert "winner" in sensitivity.columns
