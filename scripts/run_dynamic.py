"""变 DNI 动态工况：模拟云遮过境(DNI 在 1800-3600s 下降)。"""
import argparse
import numpy as np
import pandas as pd
from msptc.io import load_config, export_csv
from msptc.htf import SolarSalt
from msptc.optics.analytical import AnalyticalOptics
from msptc.collector import Collector
from msptc.dynamic import simulate, Forcing


def cloud_dni(t):
    return 300.0 if 1800.0 <= t <= 3600.0 else 900.0


def main(config_path="config/default.json", outdir="output"):
    cfg = load_config(config_path)
    coll = Collector(cfg, AnalyticalOptics(cfg["optics"], cfg["collector"]), SolarSalt())
    f = Forcing(dni=cloud_dni, T_amb_C=lambda t: 25.0, wind=lambda t: 3.0,
                mdot=lambda t: cfg["htf"]["mdot_kg_s"], theta_deg=lambda t: 10.0,
                T_in_C=lambda t: cfg["htf"]["T_cold_C"])
    res = simulate(f, cfg, coll, t_span=(0, 7200), dt_out=60)
    df = pd.DataFrame({
        "t_s": res.t,
        "T_out_C": res.T_out_C,
        "dni": [cloud_dni(t) for t in res.t],
        "Q_useful_W": res.Q_useful_W,
        "Q_loss_W": res.Q_loss_W,
        "eta": res.eta,
    })
    return export_csv(df, "dynamic_cloud.csv", outdir)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/default.json")
    args = ap.parse_args()
    print("写入:", main(args.config))
