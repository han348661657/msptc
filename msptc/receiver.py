"""集热管(HCE)稳态一维能量平衡。

Forristall (2003) NREL/TP-550-34169 简化为两节点(吸热管壁 T_abs, 玻璃管 T_glass):
  F1: q_abs = q_useful(T_abs) + q_loss_annulus(T_abs, T_glass)
  F2: q_loss_annulus(T_abs, T_glass) = q_loss_external(T_glass)
真空环隙仅辐射；玻璃外为风强制对流 + 天空辐射。
"""
import math
from dataclasses import dataclass
from typing import Callable, Union
from scipy.optimize import fsolve

SIGMA = 5.670374419e-8     # Stefan-Boltzmann
# 空气物性(膜温近似常数)
NU_AIR, K_AIR, PR_AIR = 1.6e-5, 0.026, 0.7


@dataclass
class ReceiverGeom:
    d_abs_in_m: float
    d_abs_out_m: float
    d_glass_in_m: float
    d_glass_out_m: float
    eps_abs: Union[float, Callable[[float], float]]  # 常数或 callable(T_abs_C)->float
    eps_glass: float
    vacuum: bool = True


@dataclass
class HCEResult:
    q_loss_per_m: float
    q_useful_per_m: float
    T_abs_C: float
    T_glass_C: float
    h_inner: float
    q_conv_per_m: float = 0.0   # 玻璃管外对流热损 CHL (W/m)
    q_rad_per_m: float = 0.0    # 玻璃管外辐射热损 RHL (W/m)


def _h_inner(T_htf_C, mdot, d_in, htf):
    """HTF 强制对流换热系数 (Dittus-Boelter, 湍流; 层流回退 Nu=4.36)。"""
    mu = htf.mu(T_htf_C)
    re = 4.0 * mdot / (math.pi * d_in * mu)
    pr = htf.prandtl(T_htf_C)
    nu = 4.36 if re < 2300 else 0.023 * re**0.8 * pr**0.4
    return nu * htf.k(T_htf_C) / d_in


def _h_wind(wind, d_glass_out, air=None, T_film_C=25.0):
    """玻璃管外横掠强制对流 (Churchill-Bernstein)。

    air=None 时用海平面定值常数(NU_AIR/K_AIR/PR_AIR, 向后兼容)；
    给定 AirProperties 时用海拔-温度物性(按膜温 T_film_C)。
    """
    v = max(wind, 0.1)
    if air is None:
        nu_air, k_air, pr_air = NU_AIR, K_AIR, PR_AIR
    else:
        nu_air, k_air, pr_air = air.nu(T_film_C), air.k(T_film_C), air.prandtl(T_film_C)
    re = v * d_glass_out / nu_air
    nu = (0.3 + (0.62 * re**0.5 * pr_air**(1/3)) / (1 + (0.4/pr_air)**(2/3))**0.25
          * (1 + (re/282000)**(5/8))**(4/5))
    return max(nu * k_air / d_glass_out, 5.0)


def hce_steady(T_htf_C, mdot, q_abs_per_m, T_amb_C, wind, geom: ReceiverGeom, htf,
               sky_offset_K=8.0, air=None, sky_model=None) -> HCEResult:
    T_htf = T_htf_C + 273.15
    T_amb = T_amb_C + 273.15
    if sky_model is not None:
        from msptc.atmosphere import sky_temp_C
        T_sky = sky_temp_C(T_amb_C, sky_model) + 273.15
    else:
        T_sky = T_amb - sky_offset_K
    h_in = _h_inner(T_htf_C, mdot, geom.d_abs_in_m, htf)

    A_in = math.pi * geom.d_abs_in_m
    A_abs_out = math.pi * geom.d_abs_out_m
    A_glass_out = math.pi * geom.d_glass_out_m

    def q_useful(T_abs):                       # 吸热管壁→HTF
        return h_in * A_in * (T_abs - T_htf)

    def q_annulus(T_abs, T_glass):             # 吸热管→玻璃(真空仅辐射)
        # eps_abs 支持温度相关 callable(T_abs_C) 或固定 float
        eps = geom.eps_abs(T_abs - 273.15) if callable(geom.eps_abs) else geom.eps_abs
        denom = (1.0 / eps
                 + (1 - geom.eps_glass) / geom.eps_glass * (geom.d_abs_out_m / geom.d_glass_in_m))
        return SIGMA * A_abs_out * (T_abs**4 - T_glass**4) / denom

    def q_external_split(T_glass):             # 玻璃→环境: (对流 CHL, 辐射 RHL)
        T_film_C = 0.5 * (T_glass + T_amb) - 273.15
        h_w = _h_wind(wind, geom.d_glass_out_m, air, T_film_C)
        q_conv = h_w * A_glass_out * (T_glass - T_amb)
        q_rad = SIGMA * geom.eps_glass * A_glass_out * (T_glass**4 - T_sky**4)
        return q_conv, q_rad

    def q_external(T_glass):                    # 玻璃→环境(对流海拔修正 + 辐射)
        q_conv, q_rad = q_external_split(T_glass)
        return q_conv + q_rad

    def residuals(x):
        T_abs, T_glass = x
        f1 = q_abs_per_m - q_useful(T_abs) - q_annulus(T_abs, T_glass)
        f2 = q_annulus(T_abs, T_glass) - q_external(T_glass)
        return [f1, f2]

    guess = [T_htf + 20.0, T_amb + 30.0]
    T_abs, T_glass = fsolve(residuals, guess, full_output=False)
    q_conv, q_rad = q_external_split(T_glass)
    q_loss = q_conv + q_rad
    q_use = q_abs_per_m - q_loss
    return HCEResult(q_loss_per_m=q_loss, q_useful_per_m=q_use,
                     T_abs_C=T_abs - 273.15, T_glass_C=T_glass - 273.15, h_inner=h_in,
                     q_conv_per_m=q_conv, q_rad_per_m=q_rad)


def eps_abs_PTR70(T_abs_C: float) -> float:
    """PTR70(2008) 选择涂层吸热管发射率随温度变化 (W/m)。

    ε = 0.062 + (2.00E-7)·T_abs²，T_abs 单位°C。
    来源: Burkholder & Kutscher (2009) NREL/TP-550-45633 Executive Summary。
    """
    return 0.062 + 2.00e-7 * T_abs_C**2


def make_ptr70_geom(eps_abs=eps_abs_PTR70) -> ReceiverGeom:
    """返回 Schott 2008 PTR70 标准几何体 (Burkholder 2009 p.12)。

    默认使用温度相关发射率；可传入固定 float 覆盖。
    尺寸: d_abs_in=66mm, d_abs_out=70mm, d_glass_in=114mm, d_glass_out=120mm。
    """
    return ReceiverGeom(
        d_abs_in_m=0.066, d_abs_out_m=0.070,
        d_glass_in_m=0.114, d_glass_out_m=0.120,
        eps_abs=eps_abs, eps_glass=0.89, vacuum=True,
    )


def hce_loss_empirical(T_abs_C: float) -> float:
    """PTR70(2008) 台架测试经验热损 (W/m)。

    HL = 0.141·T_abs + (6.48E-9)·T_abs⁴，T_abs 单位°C（绝对值，非温差）。
    来源: Burkholder & Kutscher (2009) NREL/TP-550-45633 Executive Summary & Figure 9。
    台架测试环境温度约 23-25°C；热损以辐射为主，依赖绝对温度而非温差。
    验证: T=100°C→14.75 W/m (实测15); T=346°C→141.5 W/m (实测141); T=506°C→495 W/m (实测495)。
    """
    a1, a4 = 0.141, 6.48e-9
    return a1 * T_abs_C + a4 * T_abs_C**4
