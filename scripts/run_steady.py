"""稳态扫描：固定 DNI，扫入射角 θ，输出集热效率/出口温/热损。"""
import argparse
import numpy as np
import pandas as pd
from msptc.io import load_config, export_csv
from msptc.htf import SolarSalt
from msptc.optics.analytical import AnalyticalOptics
from msptc.collector import Collector


def main(config_path="config/default.json", outdir="output", dni=900.0):
    cfg = load_config(config_path)
    coll = Collector(cfg, AnalyticalOptics(cfg["optics"], cfg["collector"]), SolarSalt())
    rows = []
    for theta in np.arange(0.0, 60.0, 5.0):
        r = coll.simulate_steady(T_in_C=cfg["htf"]["T_cold_C"], mdot=cfg["htf"]["mdot_kg_s"],
                                 dni=dni, theta_deg=float(theta), T_amb_C=25.0, wind=3.0)
        rows.append({"theta_deg": theta, "eta_th": r.eta_th, "T_out_C": r.T_out_C,
                     "Q_useful_W": r.Q_useful_W, "Q_loss_W": r.Q_loss_W})
    df = pd.DataFrame(rows)
    return export_csv(df, "steady_sweep.csv", outdir)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/default.json")
    ap.add_argument("--dni", type=float, default=900.0)
    args = ap.parse_args()
    print("写入:", main(args.config, dni=args.dni))
