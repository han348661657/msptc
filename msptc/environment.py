"""环境: CO₂ 避免量(替代电网发电)。

CO2_avoided = 年净电量 × 电网排放因子。中国电网因子≈0.58 kg CO₂/kWh(config, 可换省级)。
干冷假设 → 不计耗水(留 future work)。
"""


def co2_avoided_tonnes(annual_net_MWh: float, grid_factor_kg_per_kWh: float) -> float:
    """年 CO₂ 避免量 (公吨)。"""
    return annual_net_MWh * 1000.0 * grid_factor_kg_per_kWh / 1000.0
