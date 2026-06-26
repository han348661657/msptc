import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
import pytest
from scripts.run_system_annual import run_system_annual

_FIXTURE = str(Path(__file__).parent / "fixtures" / "tmy3_sample.csv")


def _two_days():
    start = datetime(2023, 6, 1, 0, 30, tzinfo=timezone.utc)
    for h in range(48):
        yield start + timedelta(hours=h)


def test_system_annual_smoke(tmp_path):
    # _run_one calls _hours_of_year once per HTF; side_effect returns fresh generator each time
    with patch("scripts.run_system_annual._hours_of_year",
               side_effect=lambda *a, **k: _two_days()):
        summary = run_system_annual(outdir=str(tmp_path))
    # 两介质都有结果
    assert set(summary) == {"solar_salt", "therminol_vp1"}
    for htf, s in summary.items():
        assert s["P_elec_MWh"] > 0
        assert 0.0 < s["eta_solar_to_elec"] < 0.45
    # 熔盐年太阳能-电效率高于导热油
    assert summary["solar_salt"]["eta_solar_to_elec"] > summary["therminol_vp1"]["eta_solar_to_elec"]


def test_tmy_mode_produces_positive_energy(tmp_path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")            # 24 行 fixture 触发 ≠8760 警告
        summary = run_system_annual(outdir=str(tmp_path), weather="tmy",
                                    tmy_file=_FIXTURE)
    assert set(summary) == {"solar_salt", "therminol_vp1"}
    for s in summary.values():
        assert s["solar_MWh"] > 0                  # 白天实测 DNI 被采集
        assert s["P_elec_MWh"] >= 0
        assert 0.0 <= s["eta_solar_to_elec"] < 0.45


def test_tmy_mode_uses_measured_dni_not_clearsky(tmp_path):
    # TMY 模式绝不应调用晴空模型；patch 成抛错以证明
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with patch("scripts.run_system_annual.dni_clear_sky",
                   side_effect=AssertionError("clearsky 不应在 TMY 模式被调用")):
            summary = run_system_annual(outdir=str(tmp_path), weather="tmy",
                                        tmy_file=_FIXTURE)
    assert summary["solar_salt"]["solar_MWh"] > 0


def test_unknown_weather_mode_raises(tmp_path):
    with pytest.raises(ValueError, match="weather"):
        run_system_annual(outdir=str(tmp_path), weather="bogus")


def test_altitude_run_adds_freeze_and_exergy(tmp_path):
    with patch("scripts.run_system_annual._hours_of_year",
               side_effect=lambda *a, **k: _two_days()):
        summary = run_system_annual(outdir=str(tmp_path), use_altitude=True, T_amb_C=-10.0)
    for htf, s in summary.items():
        assert "freeze_MWh" in s and "eta_exergy" in s
        assert 0.0 < s["eta_exergy"] < 0.45
    assert summary["solar_salt"]["freeze_MWh"] > summary["therminol_vp1"]["freeze_MWh"]
