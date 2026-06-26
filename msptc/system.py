"""系统集成：求流量、设计点链路。

设计点(on-sun): 集热场直供发电(T_to_PB = T_field_hot)，体现介质最高温差异。
"""
from scipy.optimize import brentq
from msptc.htf import make_htf
from msptc.optics.analytical import AnalyticalOptics
from msptc.collector import Collector
from msptc.powerblock import PowerBlock


def build_collector(cfg, htf_type, air=None, sky_model=None, v_wind=None):
    """从配置和HTF类型构建Collector；可注入海拔空气物性、天空温度模型、风载耦合。"""
    htf = make_htf(htf_type)
    wind_cfg = cfg.get("wind")
    rho_air = None
    if air is not None and wind_cfg is not None:
        rho_air = air.rho(wind_cfg.get("t_amb_design_C", 20.0))
    vw = v_wind if v_wind is not None else (wind_cfg.get("v_design_ms") if wind_cfg else None)
    optics = AnalyticalOptics(cfg["optics"], cfg["collector"], cfg.get("receiver"),
                              rho_air=rho_air, v_wind=vw, wind_cfg=wind_cfg)
    return Collector(cfg, optics, htf, air=air, sky_model=sky_model)


def required_mdot(coll, T_in_C, T_target_C, dni, theta_deg, T_amb_C, wind,
                  mdot_lo=1.0, mdot_hi=60.0, n_scan=40):
    """求使出口温度达到 T_target_C 的质量流量(kg/s)。

    在物理有效范围内扫描(T_out > T_in)，找到 T_out 单调下降区的过零点，
    用 brentq 精化。非单调的极低流量区因HTF超出定义域被自动排除。
    """
    import numpy as np

    def t_out(mdot):
        return coll.simulate_steady(T_in_C, mdot, dni, theta_deg, T_amb_C, wind).T_out_C

    # 在 [mdot_lo, mdot_hi] 的对数均匀网格上扫描，找第一个有效括号
    mdots = np.geomspace(mdot_lo, mdot_hi, n_scan)
    vals = [t_out(m) for m in mdots]

    # 寻找 T_out 单调递减段中 T_out 从 > T_target 变为 <= T_target 的第一个位置
    # (物理上：mdot 增大 → T_out 下降)
    best_lo, best_hi = None, None
    prev_v = None
    for i, (m, v) in enumerate(zip(mdots, vals)):
        if v <= T_in_C:          # 无效计算点（超出HTF定义域）
            prev_v = None
            continue
        if prev_v is not None and prev_v > T_target_C >= v:
            best_lo = mdots[i - 1]
            best_hi = m
            break
        prev_v = v

    if best_lo is None:
        # 目标不可达：返回最接近目标的有效流量
        valid = [(abs(v - T_target_C), m) for m, v in zip(mdots, vals) if v > T_in_C]
        return min(valid)[1] if valid else mdot_hi

    def g(mdot):
        return t_out(mdot) - T_target_C

    return brentq(g, best_lo, best_hi, xtol=1e-4, rtol=1e-6)


def design_point(cfg, htf_type, T_hot_C, dni=900.0, T_amb_C=25.0, wind=3.0):
    """设计点链路: 控流量使场出口达 T_hot_C，再算发电与总效率。

    Parameters
    ----------
    cfg : dict
        主配置字典（含 htf.T_cold_C 等）。
    htf_type : str
        HTF类型，如 "solar_salt" 或 "therminol_vp1"。
    T_hot_C : float
        目标场出口(热侧)温度，℃。
    dni : float
        法向直接辐射，W/m²，默认 900。
    T_amb_C : float
        环境温度，℃，默认 25。
    wind : float
        风速，m/s，默认 3。

    Returns
    -------
    dict
        包含效率、温度、电功率等关键设计点指标。
    """
    coll = build_collector(cfg, htf_type)
    T_cold = cfg["htf"]["T_cold_C"]
    mdot = required_mdot(coll, T_cold, T_hot_C, dni, 0.0, T_amb_C, wind)
    res = coll.simulate_steady(T_cold, mdot, dni, 0.0, T_amb_C, wind)

    pb = PowerBlock(cfg)
    pr = pb.electric_power(res.T_out_C, res.Q_useful_W)

    # 入射太阳能功率 = DNI × 采光口宽 × 总长
    Q_solar = dni * coll.aperture_m * coll.L_total

    return {
        "htf_type": htf_type,
        "mdot_kg_s": mdot,
        "T_to_PB_C": res.T_out_C,
        "Q_useful_W": res.Q_useful_W,
        "eta_field": res.eta_th,
        "eta_pb_gross": pr.eta_gross,
        "eta_pb_net": pr.eta_net,
        "P_elec_W": pr.P_elec_W,
        "eta_solar_to_elec": pr.P_elec_W / Q_solar if Q_solar > 0 else 0.0,
    }


def rated_thermal_power(cfg, htf_type, T_hot_C, dni=900.0, T_amb_C=25.0, wind=3.0):
    """额定热功率 = 回路设计点热出力 × solar_multiple。"""
    d = design_point(cfg, htf_type, T_hot_C, dni=dni, T_amb_C=T_amb_C, wind=wind)
    return d["Q_useful_W"] * cfg["storage"]["solar_multiple"]


def annual_step(coll, pb, storage, P_rated_W, T_field_hot_C, Q_field_W,
                T_amb_C, dt_s):
    """单时步贪婪调度。返回 (P_elec_W, Q_to_PB_W, dumped_W)。"""
    dumped = 0.0
    if Q_field_W >= P_rated_W:                         # 余量充储
        _, dumped = storage.charge(T_field_hot_C, Q_field_W - P_rated_W, dt_s)
        Q_to_PB, T_to_PB = P_rated_W, T_field_hot_C
    elif Q_field_W > 0:                                # 不足，放储补足
        deficit = P_rated_W - Q_field_W
        q_dis = storage.discharge(deficit, dt_s)
        Q_to_PB, T_to_PB = Q_field_W + q_dis, T_field_hot_C
    else:                                              # 夜间纯放储
        q_dis = storage.discharge(P_rated_W, dt_s)
        Q_to_PB = q_dis
        T_to_PB = storage.outlet_temp_C() or coll.htf.T_min_C
    storage.apply_losses(T_amb_C, dt_s)
    P_elec = pb.electric_power(T_to_PB, Q_to_PB).P_elec_W if Q_to_PB > 0 else 0.0
    return P_elec, Q_to_PB, dumped
