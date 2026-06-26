"""风载-海拔耦合：风致镜面斜率误差 σ_slope,wind。

σ_slope,wind = c_w · q · (W/W_ref)^a ,  动压 q = ½·ρ_air·v²
ρ_air 取自 atmosphere.AirProperties（海拔相关）→ 高原 ρ 低 → q 低 → σ_wind 低 → γ 高。
c_w、a 为结构标定参数（须文献溯源，做敏感性带）；c_w=None 关闭风载项。
"""


def dynamic_pressure(rho_air: float, v_wind_ms: float) -> float:
    """风动压 q = ½·ρ·v² (Pa)。"""
    return 0.5 * rho_air * v_wind_ms ** 2


def sigma_slope_wind(rho_air: float, v_wind_ms: float, aperture_m: float,
                     c_w, aperture_exp: float, w_ref_m: float) -> float:
    """风致斜率误差 (rad)。c_w 为 None 时返回 0（风载项关闭）。"""
    if c_w is None:
        return 0.0
    q = dynamic_pressure(rho_air, v_wind_ms)
    return c_w * q * (aperture_m / w_ref_m) ** aperture_exp
