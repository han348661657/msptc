"""热损扫描：q_loss vs 温度，可选出图。"""
import argparse
import numpy as np
import pandas as pd
from msptc.io import load_config, export_csv, setup_cn_font
from msptc.htf import SolarSalt
from msptc.receiver import ReceiverGeom
from msptc.heatloss import sweep_temperature


def main(config_path="config/default.json", outdir="output", plot=False):
    cfg = load_config(config_path)
    r = cfg["receiver"]
    geom = ReceiverGeom(d_abs_in_m=r["d_abs_in_m"], d_abs_out_m=r["d_abs_out_m"],
                        d_glass_in_m=r["d_glass_in_m"], d_glass_out_m=r["d_glass_out_m"],
                        eps_abs=r["eps_abs"], eps_glass=r["eps_glass"], vacuum=r["vacuum"])
    T_arr = np.arange(290.0, 565.0, 25.0)
    T, q = sweep_temperature(T_arr, geom, SolarSalt(), mdot=cfg["htf"]["mdot_kg_s"],
                             q_abs_per_m=3000.0, T_amb_C=25.0, wind=3.0)
    df = pd.DataFrame({"T_htf_C": T, "q_loss_W_m": q})
    path = export_csv(df, "heatloss_vs_T.csv", outdir)
    if plot:
        import matplotlib.pyplot as plt
        setup_cn_font()
        plt.figure(figsize=(7, 4.5))
        plt.plot(T, q, "o-")
        plt.xlabel("HTF 温度 (°C)")
        plt.ylabel("单位长度热损 (W/m)")
        plt.title("熔盐槽集热管热损 vs 温度")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(f"{outdir}/heatloss_vs_T.png", dpi=150)
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/default.json")
    ap.add_argument("--plot", action="store_true")
    args = ap.parse_args()
    print("写入:", main(args.config, plot=args.plot))
