"""温度相关朗肯发电模型（单常数卡诺分数）。

η_gross = f_2nd · (1 − T_cond_K / T_turbine_in_K)，T_turbine_in = T_to_PB − ΔT_pinch。
f_2nd≈0.74 同时复现导热油(~0.375 @371°C汽机入口)与熔盐(~0.44 @512°C)两个文献点。
"""
from dataclasses import dataclass


@dataclass
class PowerResult:
    P_elec_W: float
    eta_gross: float
    eta_net: float


class PowerBlock:
    def __init__(self, cfg: dict):
        pb = cfg["powerblock"]
        self.T_cond_C = pb["T_cond_C"]
        self.dT_pinch_C = pb["dT_pinch_C"]
        self.f_2nd = pb["f_2nd"]
        self.parasitic = pb["parasitic_frac"]

    def cycle_efficiency(self, T_to_PB_C: float):
        """返回 (η_gross, η_net)。送入温度过低时返回 (0, 0)。"""
        T_turb_in_K = (T_to_PB_C - self.dT_pinch_C) + 273.15
        T_cond_K = self.T_cond_C + 273.15
        if T_turb_in_K <= T_cond_K:
            return 0.0, 0.0
        eta_carnot = 1.0 - T_cond_K / T_turb_in_K
        eta_gross = self.f_2nd * eta_carnot
        eta_net = eta_gross * (1.0 - self.parasitic)
        return eta_gross, eta_net

    def electric_power(self, T_to_PB_C: float, Q_thermal_W: float) -> PowerResult:
        eg, en = self.cycle_efficiency(T_to_PB_C)
        return PowerResult(P_elec_W=en * max(Q_thermal_W, 0.0), eta_gross=eg, eta_net=en)
