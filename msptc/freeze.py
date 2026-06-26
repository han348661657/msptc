"""熔盐高原防冻寄生能耗模型。

冰点 238°C 的熔盐在高寒夜间需电伴热维持液态；导热油(冰点 12°C)几乎不触发。
维持热损 = 把 HTF 维持在 T_guard 时受热管的净热损(海拔/天空温度修正)，复用 hce_steady。
高原干冷天空更冷 → 维持能耗更大，构成熔盐在高原的额外劣势。
"""
from msptc.receiver import hce_steady

MIN_FLOW_KG_S = 0.5     # 防冻再循环最小流量


def freeze_guard_temp_C(htf, guard_margin_C=12.0):
    """需维持的最低温度 = HTF 冰点 + 裕度。"""
    return htf.freeze_point_C + guard_margin_C


def freeze_parasitic_W(htf, geom, T_amb_C, wind, L_total_m, idle,
                       air=None, sky_model="swinbank", guard_margin_C=12.0):
    """单时步防冻电伴热功率 (W)。idle=True: 当前无有用集热。

    用 hce_steady 在 q_abs=0、HTF=T_guard 下求受热管净热损，电伴热须补偿之。
    """
    if not idle:
        return 0.0
    T_guard_C = freeze_guard_temp_C(htf, guard_margin_C)
    if T_amb_C >= T_guard_C:
        return 0.0
    res = hce_steady(T_guard_C, MIN_FLOW_KG_S, 0.0, T_amb_C, wind, geom, htf,
                     air=air, sky_model=sky_model)
    return max(res.q_loss_per_m, 0.0) * L_total_m
