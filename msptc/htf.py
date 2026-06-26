"""Solar Salt (60% NaNO3 / 40% KNO3) 物性关联式。

来源: Zavoico (2001) SAND2001-2100; Bauer et al. T 单位 °C, 有效区间约 260-600°C。
"""
import math
import warnings

_T_MIN_C, _T_MAX_C = 238.0, 600.0


class SolarSalt:
    freeze_point_C = 238.0
    T_min_C = _T_MIN_C
    T_max_C = _T_MAX_C

    def _check(self, T_C):
        if T_C < self.T_min_C or T_C > self.T_max_C:
            warnings.warn(f"Solar Salt 温度 {T_C}°C 超出有效区间 [{self.T_min_C}, {self.T_max_C}]",
                          UserWarning, stacklevel=3)

    # Private no-check helpers (used internally to avoid duplicate warnings)
    def _rho(self, T_C):
        return 2090.0 - 0.636 * T_C

    def _cp(self, T_C):
        return 1443.0 + 0.172 * T_C

    def _mu(self, T_C):
        return (22.714 - 0.120 * T_C + 2.281e-4 * T_C**2 - 1.474e-7 * T_C**3) * 1e-3

    def _k(self, T_C):
        return 0.443 + 1.9e-4 * T_C

    def rho(self, T_C):   # kg/m^3
        self._check(T_C)
        return self._rho(T_C)

    def cp(self, T_C):    # J/(kg·K)
        self._check(T_C)
        return self._cp(T_C)

    def mu(self, T_C):    # Pa·s
        self._check(T_C)
        return self._mu(T_C)

    def k(self, T_C):     # W/(m·K)
        self._check(T_C)
        return self._k(T_C)

    def prandtl(self, T_C):
        self._check(T_C)
        return self._cp(T_C) * self._mu(T_C) / self._k(T_C)


class TherminolVP1:
    """Therminol VP1 (联苯/二苯醚共晶) 物性关联式。

    来源: Therminol VP-1 数据表(Eastman/Solutia)，cp/μ/k 由 scripts/fit_htf_props.py
    重拟合；中温区(172-222°C)以 Forristall(2003) NREL/TP-550-34169 Table 3.1 核验。
    ρ 沿用 Wagner & Gilman(2011) 关联式(误差<1%)。
    T 单位 °C，有效区间 12–400°C（>400°C 热裂解）。精度: cp±2%, μ±10%, k±2%。
    """
    freeze_point_C = 12.0
    T_min_C = 12.0
    T_max_C = 400.0

    def _check(self, T_C):
        if T_C < self.T_min_C or T_C > self.T_max_C:
            warnings.warn(f"Therminol VP1 温度 {T_C}°C 超出有效区间 "
                          f"[{self.T_min_C}, {self.T_max_C}]", UserWarning, stacklevel=3)

    def _rho(self, T_C):
        return 1083.25 - 0.90797 * T_C + 0.00078116 * T_C**2 - 2.367e-6 * T_C**3

    def _cp(self, T_C):
        # 3 次多项式拟合 Therminol VP-1 数据表 + Forristall Table 3.1（见 scripts/fit_htf_props.py）
        return (1477.7123064186394 + 3.8130037478420693 * T_C
                - 6.065114791997186e-3 * T_C**2 + 6.172294888589026e-6 * T_C**3)

    def _mu(self, T_C):
        # VFT 形式重拟合 Therminol VP-1 数据表（见 scripts/fit_htf_props.py）
        return 1e-3 * math.exp(4470.806231306911 / (T_C + 550.6530910139268)
                               - 6.888282290983753)

    def _k(self, T_C):
        # 2 次多项式拟合 Therminol VP-1 数据表 + Forristall Table 3.1（见 scripts/fit_htf_props.py）
        return 0.1426505333408285 - 1.4289156840445062e-4 * T_C - 1.3265126525680074e-8 * T_C**2

    def rho(self, T_C):   # kg/m^3
        self._check(T_C); return self._rho(T_C)

    def cp(self, T_C):    # J/(kg·K)
        self._check(T_C); return self._cp(T_C)

    def mu(self, T_C):    # Pa·s
        self._check(T_C); return self._mu(T_C)

    def k(self, T_C):     # W/(m·K)
        self._check(T_C); return self._k(T_C)

    def prandtl(self, T_C):
        self._check(T_C); return self._cp(T_C) * self._mu(T_C) / self._k(T_C)


def make_htf(htf_type: str):
    """按配置 htf.type 返回 HTF 物性对象。"""
    t = htf_type.lower()
    if t == "solar_salt":
        return SolarSalt()
    if t == "therminol_vp1":
        return TherminolVP1()
    raise ValueError(f"未知 HTF 类型: {htf_type}")
