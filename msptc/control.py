"""控制/优化接口：防凝保护、CollectorEnv（MPC/RL接口）。"""
from msptc.dynamic import Forcing, simulate

MIN_FLOW_KG_S = 0.5


def freeze_protection(T_C, mdot_request, cfg):
    """低于防凝阈值时切到最小流量(再循环), 否则放行请求流量。"""
    if T_C < cfg["htf"]["T_freeze_guard_C"]:
        return MIN_FLOW_KG_S
    return mdot_request


class CollectorEnv:
    """环境式接口(供 MPC/RL)。action: {mdot, defocus∈[0,1]}。"""

    def __init__(self, cfg, coll, dni_profile, T_amb_C=25.0, wind=3.0, theta_deg=10.0, dt=60.0):
        self.cfg = cfg
        self.coll = coll
        self.dni_profile = dni_profile
        self.T_amb_C = T_amb_C
        self.wind = wind
        self.theta_deg = theta_deg
        self.dt = dt
        self.T_target_C = cfg["htf"]["T_hot_C"]
        self.reset()

    def reset(self):
        self.t = 0.0
        self.T_out_C = self.cfg["htf"]["T_cold_C"]
        return self._state()

    def _state(self):
        return {"t": self.t, "T_out_C": self.T_out_C,
                "dni": self.dni_profile(self.t), "T_target_C": self.T_target_C}

    def step(self, action):
        mdot = freeze_protection(self.T_out_C,
                                 action.get("mdot", self.cfg["htf"]["mdot_kg_s"]), self.cfg)
        defocus = action.get("defocus", 0.0)
        dni_eff = self.dni_profile(self.t) * (1.0 - defocus)
        f = Forcing(dni=lambda t: dni_eff, T_amb_C=lambda t: self.T_amb_C,
                    wind=lambda t: self.wind, mdot=lambda t: mdot,
                    theta_deg=lambda t: self.theta_deg,
                    T_in_C=lambda t: self.cfg["htf"]["T_cold_C"])
        res = simulate(f, self.cfg, self.coll, t_span=(self.t, self.t + self.dt),
                       dt_out=self.dt, T0_C=self.T_out_C)
        self.T_out_C = float(res.T_out_C[-1])
        self.t += self.dt
        state = self._state()
        reward = -self.cost(state, action)
        return state, reward, {"Q_useful_W": float(res.Q_useful_W[-1])}

    def cost(self, state, action):
        T = state["T_out_C"]
        c = (T - self.T_target_C) ** 2
        guard = self.cfg["htf"]["T_freeze_guard_C"]
        if T < guard:
            c += 1e5 * (guard - T)
        return float(c)
