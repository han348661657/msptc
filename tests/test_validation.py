import pytest
from msptc.atmosphere import air_pressure

# 美国标准大气(1976): (高度m, 气压kPa)
STD_ATM = [(0, 101.325), (1000, 89.876), (2000, 79.501), (3000, 70.121)]


def test_pressure_vs_standard_atmosphere():
    for z, p_kPa in STD_ATM:
        assert air_pressure(z) / 1000.0 == pytest.approx(p_kPa, rel=0.01)


import copy
from msptc.io import load_config
from msptc.atmosphere import AirProperties
from msptc.system import build_collector


def _gamma_8p6(cfg, elev, c_w, a):
    cfg = copy.deepcopy(cfg)
    cfg["optics"]["intercept_model"] = "error_cone"
    cfg["collector"].update({"aperture_m": 8.6, "focal_m": 2.56})
    cfg["receiver"]["d_abs_out_m"] = 0.090
    cfg["wind"].update({"c_w": c_w, "aperture_exp": a})
    return build_collector(cfg, "solar_salt", air=AirProperties(elev)).optics.intercept


def test_altitude_synergy_robust_across_parameter_band():
    """主结论(高原 γ > 海平面 γ, 8.6m)须在 c_w、a 文献带内不翻转。"""
    cfg = load_config("config/default.json")
    for c_w in (1.0e-5, 1.7e-5, 2.5e-5):
        for a in (1.0, 1.5, 2.0):
            g_sea = _gamma_8p6(cfg, 0, c_w, a)
            g_alt = _gamma_8p6(cfg, 2801, c_w, a)
            assert g_alt > g_sea, f"翻转于 c_w={c_w}, a={a}"


def test_model_reproduces_measured_large_aperture_intercept():
    """误差锥模型(默认 config: σ_slope_grav=2.5mrad)复现 8.6m 大开口槽**第三方实测** SCE 拦截率:
    - 中广核 8.6m / 80mm 集热管: 实测 0.966(德令哈中试, 2026)
    - 龙腾 RT86 8.6m / 90mm 集热管: 实测 ≥0.98(临河示范)
    这是论文 F13 parity 的真实工业验证锚点(纯几何截距, 不计风载)。"""
    from msptc.optics.intercept import intercept_factor, sigma_total
    eb = load_config("config/default.json")["optics"]["error_budget"]
    st = sigma_total(eb["sigma_sun_mrad"] * 1e-3, eb["sigma_slope_grav_mrad"] * 1e-3,
                     eb["sigma_spec_mrad"] * 1e-3, eb["sigma_track_mrad"] * 1e-3)
    g_cgn = intercept_factor(8.6, 2.56, 0.080, st)   # 中广核 80mm
    g_lt = intercept_factor(8.6, 2.56, 0.090, st)    # 龙腾 90mm
    assert g_cgn == pytest.approx(0.966, abs=0.01), f"CGN: {g_cgn}"
    assert g_lt >= 0.975, f"Longteng: {g_lt}"


def test_error_cone_eurotrough_pure_intercept_high():
    """EuroTrough 5.77m/70mm 的**纯几何/光学截距** ~0.99;文献常引的 0.92-0.95 是
    含遮挡/污染/跟踪可用率的**集总**值,二者不可混淆(误差锥只算纯截距)。"""
    cfg = copy.deepcopy(load_config("config/default.json"))
    cfg["optics"]["intercept_model"] = "error_cone"
    g = build_collector(cfg, "solar_salt").optics.intercept
    assert 0.97 <= g <= 1.0


# ── 海拔热损机制 parity: Wang et al. (2022, Solar Energy 244:490-506) ──
from msptc.receiver import hce_steady, make_ptr70_geom
from msptc.htf import make_htf
from msptc.atmosphere import AirProperties


def _chl_rhl(elev_m, T_htf_C=400.0, wind=3.0):
    """格尔木工况受热管的 (对流热损 CHL, 辐射热损 RHL) W/m，注入海拔空气物性。"""
    r = hce_steady(T_htf_C, 8.0, 12000.0, 10.0, wind, make_ptr70_geom(),
                   make_htf("solar_salt"), air=AirProperties(elev_m), sky_model="swinbank")
    return r.q_conv_per_m, r.q_rad_per_m


def test_altitude_heatloss_mechanism_matches_wang2022b():
    """Wang2022b 实测+仿真核心机制: 海拔↑ → 对流热损 CHL 单调↓、辐射热损 RHL 单调↑(反向)。
    本槽式真空集热管模型须**独立复现该机制方向**。
    注: Wang2022b 对象为平板集热器(FPSC, 25-45℃, 开口面积口径), 其绝对 THLC(格尔木 3.74
    W/m²K)与主导项(高海拔 RHL 64.2%)**不可与本槽式真空管(290-565℃, 风强对流→对流主导)
    直接数值对标**; 此处只验证机制方向, 量级差异恰是本文填补的 gap。"""
    elevs = [0, 1000, 2295, 2801, 3649, 5000]
    chl = [_chl_rhl(e)[0] for e in elevs]
    rhl = [_chl_rhl(e)[1] for e in elevs]
    assert all(chl[i] > chl[i + 1] for i in range(len(chl) - 1)), f"CHL 未单调降: {chl}"
    assert all(rhl[i] < rhl[i + 1] for i in range(len(rhl) - 1)), f"RHL 未单调升: {rhl}"


def test_altitude_heatloss_mechanism_robust_temp_wind():
    """机制方向(CHL↓/RHL↑, 海平面→格尔木 2801m)须在工作温度与风速带内稳健不翻转。"""
    for T in (300.0, 400.0, 540.0):
        for w in (1.0, 3.0, 6.0):
            chl0, rhl0 = _chl_rhl(0, T, w)
            chl_a, rhl_a = _chl_rhl(2801, T, w)
            assert chl_a < chl0, f"CHL 翻转 @T={T},w={w}: {chl0:.1f}->{chl_a:.1f}"
            assert rhl_a > rhl0, f"RHL 翻转 @T={T},w={w}: {rhl0:.1f}->{rhl_a:.1f}"


# ── 真空管凝固时间 parity: Russo et al. (2025, Energies 18:4492) ──
import math


def test_vacuum_tube_solidification_time_matches_russo2025():
    """Russo2025 室内台架: 真空集热管内 Solar Salt 50.5 kg 从 270℃ 断电静止,
    实测完全凝固 ~4 h。本模型受热管热损(q_abs=0, 真空, 室内近似无风/无冷天空)结合
    熔盐热质应反推出**同量级**凝固时间, 借此校验凝固温区的受热管热损量级
    (freeze.py 寄生能耗的物理基础)。
    模型略偏慢(忽略 collar/弯头热桥, 而 Russo 指出 collar 散热最强、最先凝固),
    故实测 ~4h 落在模型反推时间下方; 接受带 [3.5, 6.0] h 以涵盖该不确定性。"""
    salt = make_htf("solar_salt")
    geom = make_ptr70_geom()
    m, L_fus, T0, T_fr = 50.5, 96e3, 270.0, 238.0   # Russo2025 §2-3 台架参数
    d_in = 0.066
    L = m / (salt.rho(250.0) * math.pi / 4 * d_in ** 2)   # 由盐量反推受热管总长 ≈7.6m

    def qloss(T):  # 室内: wind≈0.3, T_amb=20℃, T_sky≈T_amb(无冷天空)
        return hce_steady(float(T), 0.5, 0.0, 20.0, 0.3, geom, salt,
                          air=AirProperties(0), sky_offset_K=2.0).q_loss_per_m

    t_sens = m * salt.cp(254.0) * (T0 - T_fr) / (0.5 * (qloss(T0) + qloss(T_fr)) * L)
    t_lat = m * L_fus / (qloss(T_fr) * L)
    t_total_h = (t_sens + t_lat) / 3600.0
    assert 3.5 <= t_total_h <= 6.0, f"反推凝固时间 {t_total_h:.2f} h 偏离 Russo 实测 ~4h 量级"


# ── HTF 㶲效率排序 parity: Khandelwal et al. (2024, Applied Energy 376:124203) ──
from msptc.io import load_config
from msptc.system import design_point
from msptc.exergy import exergy_breakdown


def _eta_exergy(htf_type, T_hot_C, T_amb_C=25.0):
    cfg = load_config("config/default.json")
    T_cold = cfg["htf"]["T_cold_C"]
    d = design_point(cfg, htf_type, T_hot_C=T_hot_C, dni=900.0, T_amb_C=T_amb_C)
    Q_solar = d["P_elec_W"] / d["eta_solar_to_elec"]
    bd = exergy_breakdown(Q_solar, d["Q_useful_W"], 0.5 * (T_cold + T_hot_C),
                          d["T_to_PB_C"], d["P_elec_W"], T_amb_C)
    return bd["eta_exergy"]


def test_htf_exergy_ranking_matches_khandelwal2024():
    """Khandelwal2024 结论: 熔盐㶲效率 > 导热油(因工作温区更高、吸热更多)。
    本模型设计点㶲效率排序须复现 熔盐 > Therminol VP-1。
    注: 该文为整体联合循环(ISCC, 熔盐 49.35% > 油 48.98%), 绝对量级与本单体槽式
    (熔盐 ~29.5% > 油 ~25.6%)不可直接对标; 仅验证介质排序方向。"""
    eta_salt = _eta_exergy("solar_salt", 540.0)
    eta_oil = _eta_exergy("therminol_vp1", 390.0)
    assert eta_salt > eta_oil, f"㶲效率排序翻转: 熔盐 {eta_salt:.4f} vs 油 {eta_oil:.4f}"


# ── 成本货币口径守卫: CSP产业蓝皮书(2025) CNY 基准 ──
def test_economics_costs_are_cny_denominated():
    """防回归: economics 分项造价须为**人民币 CNY**量级, 不得退回 Turchi 美元原值
    (集热场 $170/m²、发电块 $1.1M/MW —— 直接当 CNY 用会使 LCOE 偏低 ~7×, 0.068 元/kWh,
    比煤电还便宜)。CNY 量级由 CSP产业蓝皮书(2025)锚定: 国内大规模 CSP 单位投资
    1.35-1.58 万元/kW、LCOE 0.47-0.53 元/kWh。"""
    econ = load_config("config/default.json")["economics"]
    assert econ["field_cost_per_m2"] >= 800.0, "集热场造价疑似美元值(应为 CNY, ~1200 元/m²)"
    assert econ["powerblock_cost_per_MW"] >= 5.0e6, "发电块造价疑似美元值(应为 CNY, ~7.8e6 元/MW)"
    assert econ["storage_cost_per_kWhth"] >= 80.0, "储热造价疑似美元值(应为 CNY, ~155 元/kWh_th)"
