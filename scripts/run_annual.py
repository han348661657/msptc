"""年度晴天性能仿真：逐小时运行稳态集热回路模型。

基于 REST2 晴天模型计算逐小时 DNI；太阳几何由 SPA 给出入射角。
仅仿真晴天工况（无云、无遮挡），适合作为年度能量潜力基准。

用法:
    python scripts/run_annual.py [--config config/default.json] [--year 2023]
                                 [--T-amb 25] [--wind 3] [--outdir results]
"""
import argparse
import math
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd

from msptc.io import load_config, export_csv
from msptc.htf import SolarSalt
from msptc.optics.analytical import AnalyticalOptics
from msptc.collector import Collector
from msptc.solar import solar_position, incidence_angle, dni_clear_sky

DNI_MIN_W_M2 = 50.0    # 低于此值不启动集热


def _hours_of_year(year: int):
    """生成指定年份每小时的 UTC datetime（本地时近似等于 UTC）。"""
    start = datetime(year, 1, 1, 0, 30, tzinfo=timezone.utc)
    for h in range(8760):
        yield start + timedelta(hours=h)


def run_annual(cfg_path="config/default.json", year=2023,
               T_amb_C=25.0, wind_m_s=3.0, outdir="results"):
    cfg = load_config(cfg_path)
    site = cfg["site"]
    htf_cfg = cfg["htf"]
    coll = Collector(cfg, AnalyticalOptics(cfg["optics"], cfg["collector"]), SolarSalt())

    rows = []
    for dt in _hours_of_year(year):
        sun = solar_position(dt, site)
        if sun.zenith_deg >= 88.0:     # 夜间或极低太阳高度角，跳过
            continue
        theta = incidence_angle(sun, site.get("axis", "NS"))
        if theta >= 75.0:              # 入射角过大，光学效率接近零
            continue
        dni = dni_clear_sky(sun.zenith_deg, site)
        if dni < DNI_MIN_W_M2:
            continue
        r = coll.simulate_steady(
            T_in_C=htf_cfg["T_cold_C"],
            mdot=htf_cfg["mdot_kg_s"],
            dni=dni,
            theta_deg=theta,
            T_amb_C=T_amb_C,
            wind=wind_m_s,
        )
        rows.append({
            "datetime_utc": dt.strftime("%Y-%m-%dT%H:%M"),
            "doy": dt.timetuple().tm_yday,
            "hour": dt.hour,
            "zenith_deg": round(sun.zenith_deg, 2),
            "theta_deg": round(theta, 2),
            "DNI_W_m2": round(dni, 1),
            "T_out_C": round(r.T_out_C, 2),
            "Q_useful_W": round(r.Q_useful_W, 1),
            "Q_loss_W": round(r.Q_loss_W, 1),
            "eta_th": round(r.eta_th, 4),
        })

    df = pd.DataFrame(rows)
    path = export_csv(df, f"annual_{year}.csv", outdir)

    # 年度摘要
    n_op = len(df)
    total_Wh = df["Q_useful_W"].sum()          # 每小时值直接为 Wh（dt=1h）
    total_solar_Wh = (df["DNI_W_m2"] * coll.aperture_m * coll.L_total).sum()
    eta_ann = total_Wh / total_solar_Wh if total_solar_Wh > 0 else 0.0

    print(f"\n── 年度晴天仿真 {year} ──")
    print(f"  运行小时数  : {n_op} h")
    print(f"  集热量      : {total_Wh/1e6:.2f} MWh")
    print(f"  入射太阳能  : {total_solar_Wh/1e6:.2f} MWh")
    print(f"  年平均效率  : {eta_ann*100:.1f}%")
    print(f"  输出文件    : {path}")
    return path, df


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="年度晴天集热性能仿真")
    ap.add_argument("--config", default="config/default.json")
    ap.add_argument("--year", type=int, default=2023)
    ap.add_argument("--T-amb", type=float, default=25.0, dest="T_amb")
    ap.add_argument("--wind", type=float, default=3.0)
    ap.add_argument("--outdir", default="results")
    a = ap.parse_args()
    run_annual(a.config, year=a.year, T_amb_C=a.T_amb, wind_m_s=a.wind, outdir=a.outdir)
