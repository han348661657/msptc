"""双罐储热：直接(熔盐) / 间接(导热油经油-盐换热器)。

温度惩罚为纯函数，能量缓冲为有状态类。能量平衡跟踪热罐储能 E_hot_J。
"""


def storage_hot_temp(T_field_hot_C, indirect, dT_approach_C, T_max_C):
    """充热后热罐温度。间接架构受换热器 approach 温降 + 介质上限约束。"""
    if indirect:
        return min(T_field_hot_C, T_max_C) - dT_approach_C
    return T_field_hot_C


def storage_delivery_temp(T_hot_store_C, indirect, dT_approach_C):
    """放热送往发电的温度。间接架构再扣一次 approach。"""
    if indirect:
        return T_hot_store_C - dT_approach_C
    return T_hot_store_C


class TwoTankStorage:
    def __init__(self, cfg, htf, P_thermal_rated_W, indirect):
        st = cfg["storage"]
        self.capacity_J = st["hours"] * 3600.0 * P_thermal_rated_W
        self.dT_approach_C = st["dT_approach_C"]
        self.tank_UA_W_K = st["tank_UA_W_K"]
        self.tank_conv_frac = st.get("tank_conv_frac", 0.5)   # UA 中对流占比(余为辐射/导热)
        self.indirect = indirect
        self.htf = htf
        self.E_hot_J = 0.0
        self.T_hot_store_C = None    # 最近充热时的热罐温度

    def charge(self, T_field_hot_C, Q_avail_W, dt_s):
        """充热 Q_avail_W 持续 dt_s。返回 (实际充入功率, 弃热功率)。"""
        self.T_hot_store_C = storage_hot_temp(
            T_field_hot_C, self.indirect, self.dT_approach_C, self.htf.T_max_C)
        room = self.capacity_J - self.E_hot_J
        e_in = Q_avail_W * dt_s
        stored = min(e_in, room)
        self.E_hot_J += stored
        return stored / dt_s, (e_in - stored) / dt_s

    def discharge(self, Q_demand_W, dt_s):
        """放热，受存量限制。返回实际放出功率。"""
        e_out = min(Q_demand_W * dt_s, self.E_hot_J)
        self.E_hot_J -= e_out
        return e_out / dt_s

    def apply_losses(self, T_amb_C, dt_s, air=None, sky_model=None):
        """罐体散热 UA·(T_hot − T_amb)，对流部分随空气密度(海拔)修正。返回散热功率。

        自然对流 h ∝ ρ^0.5；air=None 时不修正(向后兼容)。
        """
        if self.T_hot_store_C is None:
            return 0.0
        conv_scale = 1.0
        if air is not None:
            from msptc.atmosphere import AirProperties
            a0 = AirProperties(0.0)
            conv_scale = (air.rho(T_amb_C) / a0.rho(T_amb_C)) ** 0.5
        ua_eff = self.tank_UA_W_K * (self.tank_conv_frac * conv_scale
                                     + (1.0 - self.tank_conv_frac))
        q_loss = max(ua_eff * (self.T_hot_store_C - T_amb_C), 0.0)
        e_loss = min(q_loss * dt_s, self.E_hot_J)
        self.E_hot_J -= e_loss
        return e_loss / dt_s

    def outlet_temp_C(self):
        """当前放热送往发电的温度。"""
        if self.T_hot_store_C is None:
            return None
        return storage_delivery_temp(self.T_hot_store_C, self.indirect, self.dT_approach_C)

    def soc(self):
        return self.E_hot_J / self.capacity_J if self.capacity_J > 0 else 0.0
