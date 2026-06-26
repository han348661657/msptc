"""海拔-温度相关空气物性 + 晴空天空温度。

理想气体下空气物性随海拔仅经密度改变；μ/k/cp/Pr 随气压不变（仅温变）。
来源: 美国标准大气(1976) 气压-高度式; Sutherland 黏度式; Swinbank(1963) 天空温度。
"""

_P0 = 101325.0          # 海平面标准气压 Pa
_R_SPECIFIC = 287.05    # 干空气比气体常数 J/(kg·K)
_MU_REF = 1.716e-5      # Sutherland 参考黏度 Pa·s @273.15K
_T_REF = 273.15
_S_SUTH = 110.4         # Sutherland 常数 K
_K_REF = 0.0241         # 空气导热 @273.15K W/(m·K)
_CP_AIR = 1005.0        # 空气定压比热 J/(kg·K)


def air_pressure(elev_m: float) -> float:
    """美国标准大气气压-高度关系 (Pa)。"""
    return _P0 * (1.0 - 2.25577e-5 * elev_m) ** 5.25588


class AirProperties:
    """给定海拔的空气物性；各方法按膜温 T_film_C 求值。"""

    def __init__(self, elev_m: float = 0.0):
        self.elev_m = elev_m
        self.pressure_Pa = air_pressure(elev_m)

    def rho(self, T_film_C: float) -> float:        # kg/m^3
        return self.pressure_Pa / (_R_SPECIFIC * (T_film_C + 273.15))

    def mu(self, T_film_C: float) -> float:         # Pa·s (Sutherland, 与气压无关)
        T = T_film_C + 273.15
        return _MU_REF * (T / _T_REF) ** 1.5 * (_T_REF + _S_SUTH) / (T + _S_SUTH)

    def nu(self, T_film_C: float) -> float:         # m^2/s
        return self.mu(T_film_C) / self.rho(T_film_C)

    def k(self, T_film_C: float) -> float:          # W/(m·K) (与气压无关)
        T = T_film_C + 273.15
        return _K_REF * (T / _T_REF) ** 0.86

    def prandtl(self, T_film_C: float) -> float:    # (与气压无关)
        return self.mu(T_film_C) * _CP_AIR / self.k(T_film_C)


def sky_temp_C(T_amb_C: float, model: str = "swinbank") -> float:
    """晴空天空温度 (°C)。Swinbank(1963): T_sky[K]=0.0552·T_amb[K]^1.5。"""
    T_amb_K = T_amb_C + 273.15
    if model == "swinbank":
        T_sky_K = 0.0552 * T_amb_K ** 1.5
    elif model == "offset8":
        T_sky_K = T_amb_K - 8.0
    else:
        raise ValueError(f"未知天空温度模型: {model}")
    return T_sky_K - 273.15
