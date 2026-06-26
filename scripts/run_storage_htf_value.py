"""储热×介质 市场价值扫描: 储热小时数 × 介质 → LCOE/收入/价值因子/CO₂。

价格感知贪婪调度(高价放储)下量化"储热×介质"的市场价值。
熔盐直接储热更便宜+温度更高 → 同等储热投资捕获更多峰价电量。

两个关键建模约定(否则储热价值无法显现, 均已实测验证):
1. 太阳倍数 SM>1: 发电块热需求 = 场设计热出力 / SM(场过设计), 正午余量充储;
2. 罐体散热按容量比例(~1.5%/天)缩放, 而非 config 固定 5000 W/K
   (对本~2MW单回路过大, 会在~4h 内把储热漏空, 储热价值无法显现)。
注: 自带价格感知年度循环(复用积木), 与 run_system_annual 物理循环刻意分离以降耦合。
"""
import argparse
import copy
from datetime import timedelta
import pandas as pd
from msptc.io import load_config, export_csv
from msptc.solar import solar_position, incidence_angle, dni_clear_sky
from msptc.system import build_collector, design_point
from msptc.powerblock import PowerBlock
from msptc.storage import TwoTankStorage
from msptc.atmosphere import AirProperties
from msptc.market import tou_price, mean_price, value_factor, annual_step_priced
from msptc.economics import capex_total, lcoe
from msptc.environment import co2_avoided_tonnes
from scripts.run_system_annual import _clearsky_records

HTF_DESIGN = [("solar_salt", 540.0, False), ("therminol_vp1", 390.0, True)]
STORAGE_HOURS = [0, 3, 6, 9, 12, 15]
DNI_MIN = 50.0
DT_S = 3600.0


def _priced_annual(cfg, htf_type, T_hot_C, indirect, hours_storage, site, records,
                   tz_hours, air, sky_model, solar_multiple=2.5,
                   tank_loss_frac_per_day=0.015):
    c = copy.deepcopy(cfg)
    coll = build_collector(c, htf_type, air=air, sky_model=sky_model)
    pb = PowerBlock(c)
    # 太阳倍数: 发电块热需求 = 场设计热出力 / SM (SM>1 ⇒ 场过设计, 正午余量充储)
    Q_design = design_point(c, htf_type, T_hot_C=T_hot_C)["Q_useful_W"]
    P_rated = Q_design / solar_multiple
    c["storage"]["hours"] = hours_storage
    cap_J = hours_storage * 3600.0 * P_rated
    # 罐体散热按容量比例(~1.5%/天)缩放
    c["storage"]["tank_UA_W_K"] = (tank_loss_frac_per_day * cap_J / 86400.0
                                   / max(T_hot_C - 25.0, 1.0)) if cap_J > 0 else 0.0
    storage = TwoTankStorage(c, coll.htf, P_rated, indirect=indirect)
    T_cold, mdot = c["htf"]["T_cold_C"], c["htf"]["mdot_kg_s"]
    market, econ, env = c["market"], c["economics"], c["environment"]
    price_hi = market["price_flat"]
    E_elec_J = revenue = 0.0
    for dt, dni_meas, t_amb, wind in records:
        sun = solar_position(dt, site)
        Q_field, T_field_hot, dni = 0.0, T_hot_C, 0.0
        if sun.zenith_deg < 88.0:
            theta = incidence_angle(sun, site.get("axis", "NS"))
            if theta < 75.0:
                dni = dni_clear_sky(sun.zenith_deg, site) if dni_meas is None else dni_meas
                if dni >= DNI_MIN:
                    res = coll.simulate_steady(T_cold, mdot, dni, theta, t_amb, wind)
                    Q_field, T_field_hot = max(res.Q_useful_W, 0.0), res.T_out_C
        local_hour = (dt + timedelta(hours=tz_hours)).hour
        price = tou_price(local_hour, market)
        P_elec, _, _ = annual_step_priced(coll, pb, storage, P_rated, T_field_hot,
                                          Q_field, t_amb, DT_S, price, price_hi)
        E_elec_J += P_elec * DT_S
        revenue += P_elec * DT_S / 3.6e6 * price          # kWh × 价
    net_MWh = E_elec_J / 3.6e9
    storage_kWhth = cap_J / 3.6e6
    aperture_area = coll.aperture_m * coll.L_total
    eta_net = pb.cycle_efficiency(T_hot_C)[1]
    P_elec_rated_MW = P_rated * eta_net / 1e6
    capex = capex_total(econ, aperture_area, storage_kWhth, P_elec_rated_MW, indirect)
    opex = econ["opex_frac"] * capex
    return {
        "htf_type": htf_type, "storage_hours": hours_storage,
        "P_elec_MWh": net_MWh, "revenue_kCNY": revenue / 1e3,
        "value_factor": value_factor(revenue, net_MWh, mean_price(market)),
        "LCOE_CNY_MWh": lcoe(capex, opex, net_MWh, econ["discount_rate"], econ["lifetime_years"]),
        "CO2_avoided_t": co2_avoided_tonnes(net_MWh, env["grid_factor_kg_per_kWh"]),
        "capex_MCNY": capex / 1e6,
    }


def run_storage_htf_value(config_path="config/default.json", outdir="results",
                          T_amb_C=10.0, wind=3.0, year=2023, use_altitude=True,
                          solar_multiple=2.5, storage_hours=STORAGE_HOURS,
                          csv_name="storage_htf_value.csv"):
    cfg = load_config(config_path)
    site = cfg["site"]
    tz = site.get("tz_hours", 8)
    atm = cfg.get("atmosphere", {})
    air = AirProperties(site["elev_m"]) if use_altitude else None
    sky_model = atm.get("sky_model", "swinbank") if use_altitude else None
    rows = []
    for htf_type, T_hot, indirect in HTF_DESIGN:
        for h in storage_hours:
            records = _clearsky_records(year, T_amb_C, wind)
            rows.append(_priced_annual(cfg, htf_type, T_hot, indirect, h, site, records,
                                       tz, air, sky_model, solar_multiple=solar_multiple))
    df = pd.DataFrame(rows)
    path = export_csv(df, csv_name, outdir)
    print("\n── 储热×介质 市场价值扫描(价格感知调度, SM=%.1f) ──" % solar_multiple)
    print(df.to_string(index=False, float_format=lambda x: f"{x:.4g}"))
    print("\n输出:", path)
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="储热×介质 市场价值扫描")
    ap.add_argument("--config", default="config/default.json")
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--sm", type=float, default=2.5, dest="solar_multiple")
    ap.add_argument("--no-altitude", action="store_false", dest="use_altitude")
    a = ap.parse_args()
    run_storage_htf_value(a.config, outdir=a.outdir, solar_multiple=a.solar_multiple,
                          use_altitude=a.use_altitude)
