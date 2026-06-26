"""热损参数分析：温度扫描 + 双曲型拟合(对照项目8)。"""
import numpy as np
from scipy.optimize import curve_fit
from msptc.receiver import hce_steady


def sweep_temperature(T_htf_C_arr, geom, htf, mdot, q_abs_per_m, T_amb_C, wind):
    """扫 HTF 温度，返回 (T, q_loss[W/m])。"""
    q = np.array([hce_steady(float(T), mdot, q_abs_per_m, T_amb_C, wind, geom, htf).q_loss_per_m
                  for T in T_htf_C_arr])
    return np.asarray(T_htf_C_arr, dtype=float), q


def fit_hyperbolic(vr, q_loss_rate):
    """拟合 q = 1/(1+β·vr)，返回 β（对照项目8双曲型热损）。"""
    def model(v, beta):
        return 1.0 / (1.0 + beta * v)
    popt, _ = curve_fit(model, vr, q_loss_rate, p0=[1.0], maxfev=10000)
    return float(popt[0])
