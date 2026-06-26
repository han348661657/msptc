"""年度全链路对比: 导热油 vs 熔盐 年净发电与年效率。"""
import argparse
from datetime import datetime, timezone, timedelta
import pandas as pd
from msptc.io import load_config, export_csv
from msptc.solar import solar_position, incidence_angle, dni_clear_sky
from msptc.system import build_collector, rated_thermal_power, annual_step
from msptc.powerblock import PowerBlock
from msptc.storage import TwoTankStorage
from msptc.weather import load_tmy3
from msptc.atmosphere import AirProperties
from msptc.freeze import freeze_parasitic_W
from msptc.exergy import solar_exergy_W

HTF_DESIGN = [("solar_salt", 540.0, False), ("therminol_vp1", 390.0, True)]
DNI_MIN = 50.0
DT_S = 3600.0


def _hours_of_year(year=2023):
    start = datetime(year, 1, 1, 0, 30, tzinfo=timezone.utc)
    for h in range(8760):
        yield start + timedelta(hours=h)


def _clearsky_records(year, T_amb_C, wind):
    """晴空记录序列: dni=None 表示由 dni_clear_sky 现算。"""
    for dt in _hours_of_year(year):
        yield (dt, None, T_amb_C, wind)


def _run_one(cfg, htf_type, T_hot_C, indirect, site, records,
             air=None, sky_model=None, account_freeze=False, guard_margin_C=12.0):
    """对单一 HTF 跑全年。records 为 (dt_utc, dni_meas, t_amb, wind) 序列。

    air/sky_model: 海拔空气物性与天空温度模型(None=海平面定值, 向后兼容)。
    account_freeze: True 时计入熔盐防冻寄生电耗(年度层面从毛发电中扣除)。
    㶲累计始终进行(纯后处理, 不改电量)。
    """
    coll = build_collector(cfg, htf_type, air=air, sky_model=sky_model)
    pb = PowerBlock(cfg)
    P_rated = rated_thermal_power(cfg, htf_type, T_hot_C)
    storage = TwoTankStorage(cfg, coll.htf, P_rated, indirect=indirect)
    T_cold = cfg["htf"]["T_cold_C"]
    mdot = cfg["htf"]["mdot_kg_s"]
    E_elec_gross_J = E_solar_J = E_freeze_J = Ex_solar_J = 0.0
    for dt, dni_meas, t_amb, wind in records:
        sun = solar_position(dt, site)
        Q_field, T_field_hot = 0.0, T_hot_C
        dni = 0.0
        if sun.zenith_deg < 88.0:
            theta = incidence_angle(sun, site.get("axis", "NS"))
            if theta < 75.0:
                dni = dni_clear_sky(sun.zenith_deg, site) if dni_meas is None else dni_meas
                if dni >= DNI_MIN:
                    res = coll.simulate_steady(T_cold, mdot, dni, theta, t_amb, wind)
                    Q_field = max(res.Q_useful_W, 0.0)
                    T_field_hot = res.T_out_C
        P_elec, _, _ = annual_step(coll, pb, storage, P_rated, T_field_hot,
                                   Q_field, t_amb, DT_S)
        P_freeze = 0.0
        if account_freeze:
            idle = dni < DNI_MIN
            P_freeze = freeze_parasitic_W(coll.htf, coll.geom, t_amb, wind, coll.L_total,
                                          idle, air=air, sky_model=sky_model or "swinbank",
                                          guard_margin_C=guard_margin_C)
        Q_solar_W = dni * coll.aperture_m * coll.L_total
        Ex_solar_J += solar_exergy_W(Q_solar_W, t_amb) * DT_S
        E_elec_gross_J += P_elec * DT_S
        E_freeze_J += P_freeze * DT_S
        E_solar_J += Q_solar_W * DT_S
    # 防冻为站用电寄生，在年度层面从毛发电中扣除(避免逐时与即时发电抵消被吞没)
    E_elec_net_J = E_elec_gross_J - E_freeze_J
    eta = E_elec_net_J / E_solar_J if E_solar_J > 0 else 0.0
    eta_ex = E_elec_net_J / Ex_solar_J if Ex_solar_J > 0 else 0.0
    return {"P_elec_MWh": E_elec_net_J / 3.6e9, "solar_MWh": E_solar_J / 3.6e9,
            "eta_solar_to_elec": eta, "P_rated_thermal_MW": P_rated / 1e6,
            "freeze_MWh": E_freeze_J / 3.6e9, "eta_exergy": eta_ex}


def run_system_annual(config_path="config/default.json", year=2023,
                      T_amb_C=25.0, wind=3.0, outdir="results",
                      weather="clearsky", tmy_file="data/CHN_QH_GEERMU_TMY3.csv",
                      use_altitude=False, elev_override=None):
    cfg = load_config(config_path)
    if weather == "tmy":
        tmy = load_tmy3(tmy_file)
        # 用文件元数据覆盖站点坐标，保证太阳几何与实测 DNI 同源
        site = {**cfg["site"], "lat_deg": tmy.site["lat_deg"],
                "lon_deg": tmy.site["lon_deg"], "elev_m": tmy.site["elev_m"]}
        records_master = [(r.dt_utc, r.dni, r.t_amb_C, r.wind) for r in tmy.records]
    elif weather == "clearsky":
        site = cfg["site"]
        records_master = None
    else:
        raise ValueError(f"未知 weather 模式: {weather}（可选 clearsky|tmy）")

    atm = cfg.get("atmosphere", {})
    if use_altitude:
        elev = elev_override if elev_override is not None else site["elev_m"]
        air = AirProperties(elev)
        sky_model = atm.get("sky_model", "swinbank")
    else:
        air, sky_model = None, None
    guard = cfg.get("freeze", {}).get("guard_margin_C", 12.0)

    summary = {}
    for htf_type, T_hot, indirect in HTF_DESIGN:
        # records 是生成器，会被 _run_one 完全消费一次，故每次循环须重新创建，不可在循环外复用
        records = records_master if weather == "tmy" else _clearsky_records(year, T_amb_C, wind)
        summary[htf_type] = _run_one(cfg, htf_type, T_hot, indirect, site, records,
                                     air=air, sky_model=sky_model,
                                     account_freeze=use_altitude, guard_margin_C=guard)
    df = pd.DataFrame(summary).T.reset_index().rename(columns={"index": "htf_type"})
    tag = f"{weather}_{'alt' if use_altitude else 'sea'}_{year}"
    path = export_csv(df, f"system_annual_{tag}.csv", outdir)
    print(f"\n── 年度全链路对比 [{weather}|{'alt' if use_altitude else 'sea'}] {year} ──")
    print(df.to_string(index=False, float_format=lambda x: f"{x:.4g}"))
    print("\n输出:", path)
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="导热油 vs 熔盐 年度全链路对比")
    ap.add_argument("--config", default="config/default.json")
    ap.add_argument("--year", type=int, default=2023)
    ap.add_argument("--T-amb", type=float, default=25.0, dest="T_amb")
    ap.add_argument("--wind", type=float, default=3.0)
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--weather", choices=["clearsky", "tmy"], default="clearsky")
    ap.add_argument("--tmy-file", default="data/CHN_QH_GEERMU_TMY3.csv", dest="tmy_file")
    ap.add_argument("--altitude", action="store_true", dest="use_altitude")
    ap.add_argument("--elev", type=float, default=None, dest="elev_override")
    a = ap.parse_args()
    run_system_annual(a.config, year=a.year, T_amb_C=a.T_amb, wind=a.wind,
                      outdir=a.outdir, weather=a.weather, tmy_file=a.tmy_file,
                      use_altitude=a.use_altitude, elev_override=a.elev_override)
