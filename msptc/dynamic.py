"""动态瞬态仿真：单段集总热容 ODE（变 DNI）。

C_th·dT/dt = Q_abs(t) - HL_emp(T)·L - mdot·cp(T)·(T - T_in)
热损用 PTR70 经验式(快速光滑)；C_th = 金属热容 + 熔盐热容。
"""
import math
from dataclasses import dataclass
from typing import Callable
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from msptc.receiver import hce_loss_empirical


@dataclass
class Forcing:
    dni: Callable[[float], float]
    T_amb_C: Callable[[float], float]
    wind: Callable[[float], float]
    mdot: Callable[[float], float]
    theta_deg: Callable[[float], float]
    T_in_C: Callable[[float], float]


@dataclass
class DynamicResult:
    t: np.ndarray
    T_out_C: np.ndarray
    Q_useful_W: np.ndarray
    Q_loss_W: np.ndarray
    eta: np.ndarray


def _thermal_capacity(cfg, coll, T_C):
    """C_th [J/K] = 金属 + 熔盐 集总热容。"""
    r = coll.geom
    L = coll.L_total
    A_flow = math.pi / 4 * r.d_abs_in_m**2
    A_metal = math.pi / 4 * (r.d_abs_out_m**2 - r.d_abs_in_m**2)
    m_salt = coll.htf.rho(T_C) * A_flow * L
    m_metal = cfg["metal"]["rho_kg_m3"] * A_metal * L
    return m_metal * cfg["metal"]["cp_J_kgK"] + m_salt * coll.htf.cp(T_C)


def _net_power(T_C, t, f: Forcing, coll):
    """瞬时功率分量 (W): (q_abs, q_loss, q_transport)。"""
    dni = f.dni(t)
    theta = f.theta_deg(t)
    q_abs = coll.optics.absorbed_power_per_length(theta, dni) * coll.L_total
    q_loss = hce_loss_empirical(T_C) * coll.L_total
    q_transport = f.mdot(t) * coll.htf.cp(T_C) * (T_C - f.T_in_C(t))
    return q_abs, q_loss, q_transport


def steady_state_temp(f: Forcing, cfg, coll, t=0.0):
    """代数稳态温度（集总模型不动点）。"""
    def g(T):
        qa, ql, qt = _net_power(T, t, f, coll)
        return qa - ql - qt
    T_lo = f.T_in_C(t)
    T_hi = max(T_lo + 1.0, coll.htf.T_max_C)
    return brentq(g, T_lo, T_hi)


def simulate(f: Forcing, cfg, coll, t_span=(0, 7200), dt_out=60,
             T0_C=None, method=None) -> DynamicResult:
    T0 = T0_C if T0_C is not None else f.T_in_C(t_span[0])
    method = method or cfg["sim"].get("ode_method", "BDF")

    def rhs(t, y):
        T = y[0]
        qa, ql, qt = _net_power(T, t, f, coll)
        return [(qa - ql - qt) / _thermal_capacity(cfg, coll, T)]

    t_eval = np.arange(t_span[0], t_span[1] + dt_out, dt_out)
    sol = solve_ivp(rhs, t_span, [T0], method=method, t_eval=t_eval, rtol=1e-6, atol=1e-3)
    T = sol.y[0]
    parts = [_net_power(T[i], sol.t[i], f, coll) for i in range(len(T))]
    qa = np.array([p[0] for p in parts])
    ql = np.array([p[1] for p in parts])
    qu = qa - ql
    Q_solar = np.array([f.dni(ti) * coll.aperture_m * coll.L_total for ti in sol.t])
    eta = np.divide(qu, Q_solar, out=np.zeros_like(qu), where=Q_solar > 0)
    return DynamicResult(t=sol.t, T_out_C=T, Q_useful_W=qu, Q_loss_W=ql, eta=eta)
