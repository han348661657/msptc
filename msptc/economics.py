"""技术经济: CRF / LCOE / 分项投资。

**货币口径: 人民币 CNY**(电价/收入/LCOE 全程 CNY, 与中国站点格尔木一致)。

config 分项造价(CNY)来源:
  - 结构/比例: Turchi & Heath (2013) NREL/TP-5500-57625(集热场 $170-250/m²,
    直接TES ~$60/kWh_th, 间接TES 含油-盐换热器 +$20-30/kWh_th, 发电块 $910-1040/kWe);
    按 ~7.1 CNY/USD 换汇为 CNY: 集热场 1200 元/m², 储热 155 元/kWh_th,
    油-盐换热器 +140 元/kWh_th, 发电块 7.8×10⁶ 元/MW。
  - **量级锚定/验证: CSP产业蓝皮书(2025)** —— 现阶段国内大规模 CSP(青海 350 MW,
    11-14 h 储热)单位投资 13 500-15 800 元/kW, 度电成本 LCOE 0.47-0.53 元/kWh;
    资本金 IRR 6.5%、贷款利率 3%(首批 50 MW 示范曾为 IRR 12.83%、电价 1.15 元/kWh)。
    本模型 LCOE 应落在该带内(见 tests/test_validation.py)。
  - Herrmann & Kearney (2002): 两罐熔盐直接TES 结构参考。
储热成本随介质架构差异(间接=导热油额外油-盐换热器)是导热油 vs 熔盐经济对比的关键机理。
所有单位成本走 config, 可替换为现场数据。
"""


def crf(discount_rate: float, lifetime_years: int) -> float:
    """资本回收系数。"""
    r, n = discount_rate, lifetime_years
    if r == 0:
        return 1.0 / n
    return r * (1 + r) ** n / ((1 + r) ** n - 1)


def storage_unit_cost(econ: dict, indirect: bool) -> float:
    """储热单位热容成本 (币/kWh_th)。间接(导热油)含油-盐换热器 → 更贵。"""
    base = econ["storage_cost_per_kWhth"]
    return base + econ["oil_salt_hx_cost_per_kWhth"] if indirect else base


def capex_total(econ: dict, aperture_area_m2: float, storage_kWhth: float,
                P_elec_rated_MW: float, indirect: bool) -> float:
    """总投资 = 集热场 + 储热(架构相关) + 发电块。"""
    field = econ["field_cost_per_m2"] * aperture_area_m2
    storage = storage_unit_cost(econ, indirect) * storage_kWhth
    pb = econ["powerblock_cost_per_MW"] * P_elec_rated_MW
    return field + storage + pb


def lcoe(capex: float, opex_annual: float, annual_net_MWh: float,
         discount_rate: float, lifetime_years: int) -> float:
    """平准化度电成本 (capex 币种 / MWh)。年净电≤0 时返回 inf。"""
    if annual_net_MWh <= 0:
        return float("inf")
    return (capex * crf(discount_rate, lifetime_years) + opex_annual) / annual_net_MWh
