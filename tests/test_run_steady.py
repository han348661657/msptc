# tests/test_run_steady.py
import os
from pathlib import Path
import pandas as pd
from scripts.run_steady import main

def test_run_steady_creates_csv(tmp_path):
    cfg_path = str(Path(__file__).parent.parent / "config" / "default.json")
    out = main(config_path=cfg_path, outdir=str(tmp_path))
    assert os.path.exists(out)
    df = pd.read_csv(out)
    assert {"theta_deg", "eta_th", "T_out_C", "Q_loss_W"}.issubset(df.columns)
    assert len(df) > 0
