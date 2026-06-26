from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from scripts.run_storage_htf_value import run_storage_htf_value


def _two_days():
    start = datetime(2023, 6, 1, 0, 30, tzinfo=timezone.utc)
    for h in range(48):
        yield start + timedelta(hours=h)


def test_storage_htf_value_smoke(tmp_path):
    # _clearsky_records 定义在 run_system_annual 并调用其 _hours_of_year，故 patch 该处
    with patch("scripts.run_system_annual._hours_of_year",
               side_effect=lambda *a, **k: _two_days()):
        df = run_storage_htf_value(outdir=str(tmp_path), storage_hours=[0, 6])
    assert set(df["storage_hours"]) == {0, 6}
    assert set(df["htf_type"]) == {"solar_salt", "therminol_vp1"}
    assert (df["LCOE_CNY_MWh"] > 0).all()
    assert (df["CO2_avoided_t"] >= 0).all()
    assert "value_factor" in df.columns
