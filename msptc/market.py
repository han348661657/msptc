"""电力市场: 分时电价(ToU) + 价值因子 + 价格感知贪婪调度。

分时电价按当地小时分峰/平/谷(config)。价值因子 VF = 售电收入 / (年电量×均价),
VF>1 表示发电更落在高价时段——量化储热把电量搬到峰价的市场价值。
价格感知调度: 高价时段优先放储发电, 低价时段尽量蓄能。
"""


def tou_price(local_hour: int, market: dict) -> float:
    """当地小时(0-23, 自动取模) → 电价(币/kWh)。"""
    h = int(local_hour) % 24
    if h in market["peak_hours"]:
        return market["price_peak"]
    if h in market["valley_hours"]:
        return market["price_valley"]
    return market["price_flat"]


def mean_price(market: dict) -> float:
    """24 小时算术平均电价。"""
    return sum(tou_price(h, market) for h in range(24)) / 24.0


def value_factor(revenue: float, energy_MWh: float, mean_price_val: float) -> float:
    """价值因子 = 收入 / (电量[kWh] × 均价)。"""
    if energy_MWh <= 0 or mean_price_val <= 0:
        return 0.0
    return revenue / (energy_MWh * 1000.0 * mean_price_val)


def annual_step_priced(coll, pb, storage, P_rated_W, T_field_hot_C, Q_field_W,
                       T_amb_C, dt_s, price, price_hi):
    """价格感知贪婪调度。price≥price_hi 视为高价时段。

    高价: 放储补足到额定; 低价: 不放储(蓄留高价), 仅直发场出力, 余量充储。
    返回 (P_elec_W, Q_to_PB_W, dumped_W)。
    """
    dumped = 0.0
    high = price >= price_hi
    if Q_field_W >= P_rated_W:                         # 余量充储(任何时段)
        _, dumped = storage.charge(T_field_hot_C, Q_field_W - P_rated_W, dt_s)
        Q_to_PB, T_to_PB = P_rated_W, T_field_hot_C
    elif Q_field_W > 0:
        if high:                                       # 高价: 放储补足额定
            q_dis = storage.discharge(P_rated_W - Q_field_W, dt_s)
            Q_to_PB, T_to_PB = Q_field_W + q_dis, T_field_hot_C
        else:                                          # 低价: 蓄留储热, 仅直发
            Q_to_PB, T_to_PB = Q_field_W, T_field_hot_C
    else:                                              # 夜间: 仅高价放储
        if high:
            q_dis = storage.discharge(P_rated_W, dt_s)
            Q_to_PB = q_dis
            T_to_PB = storage.outlet_temp_C() or coll.htf.T_min_C
        else:
            Q_to_PB, T_to_PB = 0.0, coll.htf.T_min_C
    storage.apply_losses(T_amb_C, dt_s)
    P_elec = pb.electric_power(T_to_PB, Q_to_PB).P_elec_W if Q_to_PB > 0 else 0.0
    return P_elec, Q_to_PB, dumped
