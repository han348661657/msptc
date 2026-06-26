"""开口扫描: γ/聚光比/效率 vs 开口宽度 × 吸热管 × 海拔 × 介质（P4 论文图数据）。

聚光比 C、截距因子 γ 由误差锥光学算出；设计点效率经海拔空气物性 + 风载耦合贯通。
吸热管放大时按吸收管外径比例缩放整管几何（保持 PTR70→PTR90 近似一致性）。
"""
import argparse
import copy
import pandas as pd
from msptc.io import load_config, export_csv
from msptc.atmosphere import AirProperties
from msptc.optics.intercept import concentration
from msptc.system import build_collector, required_mdot
from msptc.powerblock import PowerBlock

# 配型组：名称, 开口(m), 焦距(m,保 φ_r≈80°), 吸热管外径(m)
APERTURE_CONFIGS = [
    {"name": "EuroTrough-5.77/70", "aperture_m": 5.77, "focal_m": 1.71, "d_abs_out_m": 0.070},
    {"name": "Mid-6.0/70",         "aperture_m": 6.0,  "focal_m": 1.78, "d_abs_out_m": 0.070},
    {"name": "UltimateTrough-7.5/70", "aperture_m": 7.5, "focal_m": 2.23, "d_abs_out_m": 0.070},
    {"name": "UltimateTrough-7.5/90", "aperture_m": 7.5, "focal_m": 2.23, "d_abs_out_m": 0.090},
    {"name": "LargeAperture-8.6/70", "aperture_m": 8.6, "focal_m": 2.56, "d_abs_out_m": 0.070},
    {"name": "CGN-8.6/80",           "aperture_m": 8.6, "focal_m": 2.56, "d_abs_out_m": 0.080},
    {"name": "LargeAperture-8.6/90", "aperture_m": 8.6, "focal_m": 2.56, "d_abs_out_m": 0.090},
]
ELEVATIONS_M = [0, 2801]
HTF_DESIGN = [("solar_salt", 540.0), ("therminol_vp1", 390.0)]
_RECV_BASE_D = 0.070   # 基准吸收管外径，用于按比例缩放整管几何


def _scaled_receiver(recv_base: dict, d_abs_out_m: float) -> dict:
    """按吸收管外径比例缩放整管几何（PTR70→PTR90 近似）。"""
    s = d_abs_out_m / _RECV_BASE_D
    r = dict(recv_base)
    for k in ("d_abs_in_m", "d_abs_out_m", "d_glass_in_m", "d_glass_out_m"):
        r[k] = recv_base[k] * s
    return r


def _case(cfg_base, ac, htf_type, T_hot_C, elev_m, c_w,
          dni=900.0, T_amb_C=10.0, wind=3.0):
    cfg = copy.deepcopy(cfg_base)
    cfg["optics"]["intercept_model"] = "error_cone"
    cfg["collector"]["aperture_m"] = ac["aperture_m"]
    cfg["collector"]["focal_m"] = ac["focal_m"]
    cfg["receiver"] = _scaled_receiver(cfg_base["receiver"], ac["d_abs_out_m"])
    cfg["wind"]["c_w"] = c_w
    air = AirProperties(elev_m)
    coll = build_collector(cfg, htf_type, air=air, sky_model="swinbank")
    T_cold = cfg["htf"]["T_cold_C"]
    mdot = required_mdot(coll, T_cold, T_hot_C, dni, 0.0, T_amb_C, wind)
    res = coll.simulate_steady(T_cold, mdot, dni, 0.0, T_amb_C, wind)
    pb = PowerBlock(cfg)
    pr = pb.electric_power(res.T_out_C, res.Q_useful_W)
    Q_solar = dni * coll.aperture_m * coll.L_total
    return {"config": ac["name"], "aperture_m": ac["aperture_m"],
            "d_abs_out_m": ac["d_abs_out_m"], "htf_type": htf_type, "elev_m": elev_m,
            "gamma": coll.optics.intercept,
            "concentration": concentration(ac["aperture_m"], ac["d_abs_out_m"]),
            "Q_loss_W": res.Q_loss_W, "eta_field": res.eta_th,
            "eta_solar_to_elec": pr.P_elec_W / Q_solar if Q_solar > 0 else 0.0}


def run_aperture_sweep(config_path="config/default.json", outdir="results",
                       elevations=ELEVATIONS_M, c_w=1.7e-5,
                       csv_name="aperture_sweep.csv"):
    cfg = load_config(config_path)
    rows = [_case(cfg, ac, htf, T, e, c_w)
            for ac in APERTURE_CONFIGS for e in elevations for htf, T in HTF_DESIGN]
    df = pd.DataFrame(rows)
    path = export_csv(df, csv_name, outdir)
    print("\n── 开口扫描: γ/聚光比/效率 vs 开口 × 吸热管 × 海拔 ──")
    print(df.to_string(index=False, float_format=lambda x: f"{x:.4g}"))
    print("\n输出:", path)
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="开口扫描: 大开口 × 海拔协同")
    ap.add_argument("--config", default="config/default.json")
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--c_w", type=float, default=1.7e-5,
                    help="风载斜率标定系数 (rad/Pa)；结构文献溯源，做敏感性")
    a = ap.parse_args()
    run_aperture_sweep(a.config, outdir=a.outdir, c_w=a.c_w)
