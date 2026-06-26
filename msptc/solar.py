"""太阳几何与晴空 DNI。

几何复用 vendored sunposition.sunpos (SPA)，DNI 复用 REST2。
单轴跟踪入射角公式见 Duffie & Beckman / 项目8。

注意：clear_sky_reset2 接受弧度制天顶角（内部通过 * 180/π 转换为度）。
sunpos 默认返回度数，因此在调用 REST2 时需要将 zenith_deg 转换为弧度。
"""
import math
from dataclasses import dataclass
import numpy as np

from msptc.vendor.sunposition import sunpos
from msptc.vendor.clear_sky_radiation_REST2 import clear_sky_reset2

DEG = math.pi / 180.0


@dataclass
class SunState:
    azimuth_deg: float
    zenith_deg: float
    declination_deg: float
    hour_angle_deg: float


def solar_position(dt_utc, site: dict) -> SunState:
    az, zen, ra, decl, ha = sunpos(dt_utc, site["lat_deg"], site["lon_deg"], site["elev_m"])
    return SunState(float(az), float(zen), float(decl), float(ha))


def incidence_angle(sun: SunState, axis: str = "NS") -> float:
    """槽式单轴跟踪入射角 θ (deg)。NS=南北轴东西跟踪, EW=东西轴南北跟踪。夜间(zenith≥90)返回90。"""
    if sun.zenith_deg >= 90.0:
        return 90.0
    decl = sun.declination_deg * DEG
    omega = sun.hour_angle_deg * DEG
    thz = sun.zenith_deg * DEG
    if axis.upper() == "NS":
        cos_t = math.sqrt(max(0.0, math.cos(thz)**2 + math.cos(decl)**2 * math.sin(omega)**2))
    elif axis.upper() == "EW":
        cos_t = math.sqrt(max(0.0, 1.0 - math.cos(decl)**2 * math.sin(omega)**2))
    else:
        raise ValueError(f"未知跟踪轴: {axis}")
    cos_t = min(1.0, cos_t)
    return math.degrees(math.acos(cos_t))


def dni_clear_sky(zenith_deg: float, site: dict) -> float:
    """REST2 晴空 DNI (W/m^2)。

    clear_sky_reset2 接受弧度制天顶角（函数内部用 * 180/π 还原为度数进行
    气团计算，并用 np.cos(zenith_angle) 计算余弦），因此必须将 zenith_deg
    转换为弧度后再传入。
    """
    arr = lambda x: np.array([float(x)], dtype=float)
    zenith_rad = zenith_deg * DEG
    ghi, dni, dhi = clear_sky_reset2(
        arr(zenith_rad), arr(1366.1), arr(site["pressure_hpa"]),
        arr(site["water_vapour_cm"]), arr(site["ozone_atmcm"]), arr(site["no2_atmcm"]),
        arr(site["aod550"]), arr(site["angstrom"]), arr(site["albedo"]),
    )
    val = float(dni[0])
    return 0.0 if math.isnan(val) else val
