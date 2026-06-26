"""大开口槽式光学：边缘角、几何聚光比、误差锥截距因子 γ(开口, 误差预算, 吸热管D)。

误差锥模型来源: Bendt et al. (1979) SERI/TR-34-092; Güven & Bannerot (1985)。
γ = 沿口径加权积分 erf(局部接收角 / (√2·σ_tot))。纯函数，便于单测与论文复算。
"""
import math


def rim_angle(aperture_m: float, focal_m: float) -> float:
    """抛物面边缘角 φ_r (rad): φ_r = 2·arctan(W/(4f))。"""
    return 2.0 * math.atan(aperture_m / (4.0 * focal_m))


def concentration(aperture_m: float, d_abs_out_m: float) -> float:
    """几何聚光比 C = W / (π·D_abs)（圆柱吸热管）。"""
    return aperture_m / (math.pi * d_abs_out_m)


def sigma_total(sigma_sun_rad: float, sigma_slope_rad: float,
                sigma_spec_rad: float, sigma_track_rad: float) -> float:
    """总光束 RMS 误差 (rad)。斜率误差 δ 使反射光偏转 2δ → 乘 2。

    σ_tot² = σ_sun² + (2·σ_slope)² + σ_spec² + σ_track²
    track 在此作随机项；若改作非随机偏置见 intercept_factor(track_bias_rad=…)。
    """
    return math.sqrt(sigma_sun_rad ** 2 + (2.0 * sigma_slope_rad) ** 2
                     + sigma_spec_rad ** 2 + sigma_track_rad ** 2)


def intercept_factor(aperture_m: float, focal_m: float, d_abs_out_m: float,
                     sigma_tot_rad: float, track_bias_rad: float = 0.0,
                     n: int = 400) -> float:
    """误差锥截距因子 γ ∈ (0,1]。

    沿边缘角 φ∈[0, φ_r] 梯形积分，权重 sec²(φ/2)（= 口径微元）：
      局部接收半角 Δθ(φ) = R·cos²(φ/2)/f
      局部截距     = erf(Δθ/(√2·σ_tot))         （零偏置）
                  或 ½[erf((Δθ+μ)/…)+erf((Δθ−μ)/…)] （非随机偏置 μ=track_bias）
    """
    R = 0.5 * d_abs_out_m
    phi_r = rim_angle(aperture_m, focal_m)
    s2 = math.sqrt(2.0) * sigma_tot_rad
    num = den = 0.0
    for i in range(n + 1):
        phi = phi_r * i / n
        w = 1.0 / math.cos(phi / 2.0) ** 2            # sec²(φ/2)
        dtheta = R * math.cos(phi / 2.0) ** 2 / focal_m
        if track_bias_rad == 0.0:
            loc = math.erf(dtheta / s2)
        else:
            loc = 0.5 * (math.erf((dtheta + track_bias_rad) / s2)
                         + math.erf((dtheta - track_bias_rad) / s2))
        wt = 0.5 if (i == 0 or i == n) else 1.0       # 梯形端点权重
        num += wt * loc * w
        den += wt * w
    return num / den


from msptc.optics.wind_deflection import sigma_slope_wind


def effective_intercept(optics_cfg: dict, collector_cfg: dict, receiver_cfg: dict,
                        rho_air: float = None, v_wind: float = None,
                        wind_cfg: dict = None) -> float:
    """从 config 装配 σ_tot（含可选风载-海拔项）并返回 γ。

    error_budget 单位 mrad → rad。风载仅当 rho_air/v_wind/wind_cfg.c_w 齐备且
    couple_altitude 为真时计入；否则用纯重力斜率误差。
    """
    eb = optics_cfg["error_budget"]
    sun = eb["sigma_sun_mrad"] * 1e-3
    slope_grav = eb["sigma_slope_grav_mrad"] * 1e-3
    spec = eb["sigma_spec_mrad"] * 1e-3
    track = eb["sigma_track_mrad"] * 1e-3

    slope_wind = 0.0
    if (rho_air is not None and v_wind is not None and wind_cfg is not None
            and wind_cfg.get("c_w") is not None and wind_cfg.get("couple_altitude", True)):
        slope_wind = sigma_slope_wind(rho_air, v_wind, collector_cfg["aperture_m"],
                                      wind_cfg["c_w"], wind_cfg["aperture_exp"],
                                      wind_cfg["w_ref_m"])
    slope = math.sqrt(slope_grav ** 2 + slope_wind ** 2)
    sigma_tot = sigma_total(sun, slope, spec, track)
    return intercept_factor(collector_cfg["aperture_m"], collector_cfg["focal_m"],
                            receiver_cfg["d_abs_out_m"], sigma_tot)
