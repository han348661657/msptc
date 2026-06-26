"""逐组件㶲分析(第二定律)。

参考态 T_0 = 当地环境温度。太阳㶲用 Petela；逐组件㶲损 = 入㶲 − 出㶲。
组件链: 太阳 →[光学+集热场]→ 交付㶲 →[储热]→ 入PB㶲 →[发电]→ 电功(纯㶲)。
"""
T_SUN_K = 5777.0


def solar_exergy_W(Q_solar_W: float, T_0_C: float) -> float:
    """Petela 太阳辐射㶲 (W)。"""
    T0 = T_0_C + 273.15
    psi = 1.0 - (4.0 / 3.0) * (T0 / T_SUN_K) + (1.0 / 3.0) * (T0 / T_SUN_K) ** 4
    return Q_solar_W * psi


def thermal_exergy_W(Q_W: float, T_source_C: float, T_0_C: float) -> float:
    """热流㶲 = Q·(1 − T_0/T_source) (W)；源温≤参考温时为 0。"""
    T0, Ts = T_0_C + 273.15, T_source_C + 273.15
    if Ts <= T0:
        return 0.0
    return Q_W * (1.0 - T0 / Ts)


def exergy_breakdown(Q_solar_W, Q_useful_W, T_field_m_C, T_to_PB_C, W_elec_W, T_0_C):
    """逐组件㶲损与㶲效率 (dict)。

    dest_optical_field = Ex_solar − Ex_delivered(以场平均温交付)
    dest_storage       = Ex_delivered − Ex_to_PB(approach 温降, 间接储热显著)
    dest_powerblock    = Ex_to_PB − W_elec
    """
    ex_solar = solar_exergy_W(Q_solar_W, T_0_C)
    ex_delivered = thermal_exergy_W(Q_useful_W, T_field_m_C, T_0_C)
    ex_to_pb = thermal_exergy_W(Q_useful_W, T_to_PB_C, T_0_C)
    return {
        "Ex_solar_W": ex_solar,
        "Ex_delivered_W": ex_delivered,
        "Ex_to_PB_W": ex_to_pb,
        "dest_optical_field_W": max(ex_solar - ex_delivered, 0.0),
        "dest_storage_W": max(ex_delivered - ex_to_pb, 0.0),
        "dest_powerblock_W": max(ex_to_pb - W_elec_W, 0.0),
        "eta_exergy": W_elec_W / ex_solar if ex_solar > 0 else 0.0,
    }


def exergy_balance_closes(bd: dict, W_elec_W: float, tol: float = 1e-6) -> bool:
    """校验 Σ㶲损 + W_elec = Ex_solar。"""
    total = (bd["dest_optical_field_W"] + bd["dest_storage_W"]
             + bd["dest_powerblock_W"] + W_elec_W)
    return abs(total - bd["Ex_solar_W"]) <= tol * max(bd["Ex_solar_W"], 1.0)
