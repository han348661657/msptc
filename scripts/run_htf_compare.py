"""设计点对比: 导热油 vs 熔盐 系统效率表。"""
import argparse
from pathlib import Path
import pandas as pd
from msptc.io import load_config, export_csv
from msptc.system import design_point

# 每介质设计点热端温度(受介质上限约束): 熔盐 540°C, 导热油 390°C
HTF_DESIGN = [("solar_salt", 540.0), ("therminol_vp1", 390.0)]


def run_compare(config_path="config/default.json", outdir="results", dni=900.0):
    cfg = load_config(config_path)
    rows = [design_point(cfg, htf, T_hot_C=T_hot, dni=dni) for htf, T_hot in HTF_DESIGN]
    df = pd.DataFrame(rows)
    path = export_csv(df, "htf_compare.csv", outdir)
    print("\n── 设计点对比 (DNI=%.0f W/m²) ──" % dni)
    print(df.to_string(index=False, float_format=lambda x: f"{x:.4g}"))
    print("\n输出:", path)
    return path, df


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="导热油 vs 熔盐 设计点对比")
    ap.add_argument("--config", default="config/default.json")
    ap.add_argument("--dni", type=float, default=900.0)
    ap.add_argument("--outdir", default="results")
    a = ap.parse_args()
    run_compare(a.config, outdir=a.outdir, dni=a.dni)
