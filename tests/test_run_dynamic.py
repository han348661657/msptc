import os
import pandas as pd
from pathlib import Path
from scripts.run_dynamic import main


def test_run_dynamic_creates_csv_with_cloud_response(tmp_path):
    cfg_path = str(Path(__file__).parent.parent / "config" / "default.json")
    out = main(config_path=cfg_path, outdir=str(tmp_path))
    assert os.path.exists(out)
    df = pd.read_csv(out)
    assert {"t_s", "T_out_C", "dni", "Q_useful_W"}.issubset(df.columns)
    # 云遮期间 DNI 低 → 该段平均出口温低于晴空段
    cloud = df[(df.t_s >= 1800) & (df.t_s <= 3600)]
    clear = df[df.t_s < 1800]
    assert cloud["T_out_C"].mean() < clear["T_out_C"].mean()
