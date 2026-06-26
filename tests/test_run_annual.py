"""冒烟测试：run_annual 在 2 天内能正常跑通并返回合理结果。"""
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pandas as pd
from scripts.run_annual import run_annual


def _two_days_of_hours():
    """替换 _hours_of_year：只返回前 48 h（1 月 1-2 日）。"""
    start = datetime(2023, 1, 1, 0, 30, tzinfo=timezone.utc)
    for h in range(48):
        yield start + timedelta(hours=h)


def test_run_annual_smoke(tmp_path):
    with patch("scripts.run_annual._hours_of_year", return_value=_two_days_of_hours()):
        path, df = run_annual(outdir=str(tmp_path))
    assert path.endswith(".csv")
    # 在纬度38°N的1月，白天约7-8小时，2天期望≥4个有效小时
    assert len(df) >= 4, f"有效小时数过少: {len(df)}"
    assert "Q_useful_W" in df.columns
    assert (df["Q_useful_W"] > 0).all()
    assert (df["eta_th"] > 0).all() and (df["eta_th"] < 1).all()
