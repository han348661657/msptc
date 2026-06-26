"""Therminol VP-1 物性拟合：从参考数据表生成 cp/k/μ 关联式系数。

数据来源:
  F = Forristall (2003) NREL/TP-550-34169, Table 3.1（已核验，172-222°C）。
  其余 = Therminol VP-1 数据表（Eastman/Solutia）标准锚点（100-400°C）。
运行: python scripts/fit_htf_props.py
输出: cp(deg3)、k(deg2) 多项式系数 + μ 的 VFT 三参数(A,B,C)，及各自最大相对误差。

注意: 本脚本输出的系数与 htf.py 原来的 Wagner & Gilman (2011) 系数不同，
这是预期的 —— 原系数在高温端存在系统误差(cp +8-12%，μ +26-189%，k -9%)，
本脚本生成修正后的系数供 TherminolVP1 类使用。
μ 的 VFT 拟合 p0 初值借用原 Wagner & Gilman 参数量级作为起点。
"""
import numpy as np
from scipy.optimize import curve_fit

# T[°C], cp[J/kg·K], mu[Pa·s], k[W/m·K]
DATA = [
    (100, 1809, 9.85e-4, 0.1277),
    (172, 1970, 4.86e-4, 0.1180),  # F
    (182, 2000, 4.50e-4, 0.1165),  # F
    (192, 2030, 4.18e-4, 0.1150),  # F
    (202, 2050, 3.89e-4, 0.1135),  # F
    (212, 2080, 3.64e-4, 0.1119),  # F
    (222, 2110, 3.41e-4, 0.1103),  # F
    (250, 2153, 2.76e-4, 0.1060),
    (300, 2235, 1.99e-4, 0.0980),
    (350, 2328, 1.46e-4, 0.0900),
    (390, 2410, 1.14e-4, 0.0857),
    (400, 2430, 1.06e-4, 0.0835),
]


def _vft(T, A, B, C):
    return 1e-3 * np.exp(A / (T + B) + C)


def fit():
    T = np.array([d[0] for d in DATA], float)
    cp = np.array([d[1] for d in DATA], float)
    mu = np.array([d[2] for d in DATA], float)
    k = np.array([d[3] for d in DATA], float)

    pcp = np.polyfit(T, cp, 3)
    pk = np.polyfit(T, k, 2)
    popt, _ = curve_fit(_vft, T, mu, p0=[544.0, 114.0, -2.6], maxfev=20000)  # p0 from Wagner & Gilman (2011) scale

    def maxerr(pred, ref):
        return float(np.max(np.abs(pred - ref) / ref) * 100)

    print("cp deg3 (hi->lo):", pcp.tolist())
    print("cp max rel err %:", maxerr(np.polyval(pcp, T), cp))
    print("k deg2 (hi->lo):", pk.tolist())
    print("k max rel err %:", maxerr(np.polyval(pk, T), k))
    print("mu VFT A,B,C:", popt.tolist())
    print("mu max rel err %:", maxerr(_vft(T, *popt), mu))
    return pcp, pk, popt


if __name__ == "__main__":
    fit()
