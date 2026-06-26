"""海拔扫描: 导热油 vs 熔盐 设计点效率/场热损随海拔演化(论文头图数据)。"""
import argparse
import pandas as pd
from msptc.io import load_config, export_csv
from msptc.atmosphere import AirProperties
from msptc.system import build_collector, required_mdot
from msptc.powerblock import PowerBlock

ELEVATIONS_M = [0, 1000, 2000, 2801, 4000]
HTF_DESIGN = [("solar_salt", 540.0), ("therminol_vp1", 390.0)]


def design_point_at_elev(cfg, htf_type, T_hot_C, elev_m, dni=900.0, T_amb_C=10.0,
                         wind=3.0, sky_model="swinbank"):
    """单一海拔的设计点链路(注入海拔空气物性)。"""
    air = AirProperties(elev_m)
    coll = build_collector(cfg, htf_type, air=air, sky_model=sky_model)
    T_cold = cfg["htf"]["T_cold_C"]
    mdot = required_mdot(coll, T_cold, T_hot_C, dni, 0.0, T_amb_C, wind)
    res = coll.simulate_steady(T_cold, mdot, dni, 0.0, T_amb_C, wind)
    pb = PowerBlock(cfg)
    pr = pb.electric_power(res.T_out_C, res.Q_useful_W)
    Q_solar = dni * coll.aperture_m * coll.L_total
    return {"htf_type": htf_type, "elev_m": elev_m, "T_to_PB_C": res.T_out_C,
            "Q_loss_W": res.Q_loss_W, "eta_field": res.eta_th,
            "eta_pb_gross": pr.eta_gross,
            "eta_solar_to_elec": pr.P_elec_W / Q_solar if Q_solar > 0 else 0.0}


def run_altitude_sweep(config_path="config/default.json", outdir="results",
                       elevations=ELEVATIONS_M,
                       csv_name="altitude_sweep.csv"):
    cfg = load_config(config_path)
    rows = [design_point_at_elev(cfg, htf, T, e)
            for e in elevations for htf, T in HTF_DESIGN]
    df = pd.DataFrame(rows)
    path = export_csv(df, csv_name, outdir)
    print("\n── 海拔扫描: 设计点效率/热损 vs 海拔 ──")
    print(df.to_string(index=False, float_format=lambda x: f"{x:.4g}"))
    print("\n输出:", path)
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="海拔扫描: 导热油 vs 熔盐")
    ap.add_argument("--config", default="config/default.json")
    ap.add_argument("--outdir", default="results")
    a = ap.parse_args()
    run_altitude_sweep(a.config, outdir=a.outdir)
