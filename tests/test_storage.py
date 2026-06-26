import pytest
from msptc.storage import (
    storage_hot_temp, storage_delivery_temp, TwoTankStorage,
)
from msptc.htf import SolarSalt, TherminolVP1

CFG = {"storage": {"hours": 6.0, "dT_approach_C": 15.0,
                   "tank_UA_W_K": 5000.0, "solar_multiple": 1.0}}


# ── 温度惩罚纯函数 ──────────────────────────────────────────────

def test_direct_storage_no_temp_penalty():
    assert storage_hot_temp(540.0, indirect=False, dT_approach_C=15.0, T_max_C=600.0) == 540.0
    assert storage_delivery_temp(540.0, indirect=False, dT_approach_C=15.0) == 540.0


def test_indirect_storage_double_approach_penalty():
    # 充热: min(390,400)-15 = 375; 放热: 375-15 = 360
    t_store = storage_hot_temp(390.0, indirect=True, dT_approach_C=15.0, T_max_C=400.0)
    assert t_store == pytest.approx(375.0)
    assert storage_delivery_temp(t_store, indirect=True, dT_approach_C=15.0) == pytest.approx(360.0)


def test_indirect_storage_capped_by_oil_max():
    # 即使场温 420°C，受油上限 400°C 约束
    assert storage_hot_temp(420.0, indirect=True, dT_approach_C=15.0, T_max_C=400.0) == pytest.approx(385.0)


# ── 双罐能量缓冲 ────────────────────────────────────────────────

def test_charge_then_discharge_conserves_energy():
    s = TwoTankStorage(CFG, SolarSalt(), P_thermal_rated_W=1.0e6, indirect=False)
    s.charge(T_field_hot_C=540.0, Q_avail_W=5.0e5, dt_s=3600.0)
    delivered = s.discharge(Q_demand_W=5.0e5, dt_s=3600.0)
    # 无散热损(此测试不调 apply_losses)时放出 ≤ 充入
    assert delivered == pytest.approx(5.0e5, rel=1e-9)


def test_charge_beyond_capacity_dumps_excess():
    # 容量 = 6h × 1MW = 2.16e10 J；充 3MW×3h=3.24e10 J 应弃热
    s = TwoTankStorage(CFG, SolarSalt(), P_thermal_rated_W=1.0e6, indirect=False)
    _, dumped_W = s.charge(T_field_hot_C=540.0, Q_avail_W=3.0e6, dt_s=3 * 3600.0)
    assert dumped_W > 0
    assert s.soc() == pytest.approx(1.0, rel=1e-6)


def test_discharge_limited_by_stored_energy():
    s = TwoTankStorage(CFG, SolarSalt(), P_thermal_rated_W=1.0e6, indirect=False)
    s.charge(T_field_hot_C=540.0, Q_avail_W=1.0e5, dt_s=3600.0)  # 充少量
    delivered = s.discharge(Q_demand_W=1.0e6, dt_s=3600.0)        # 求大量
    assert delivered < 1.0e6  # 受存量限制


def test_indirect_outlet_temp_lower_than_field():
    s = TwoTankStorage(CFG, TherminolVP1(), P_thermal_rated_W=1.0e6, indirect=True)
    s.charge(T_field_hot_C=390.0, Q_avail_W=5.0e5, dt_s=3600.0)
    assert s.outlet_temp_C() == pytest.approx(360.0)  # 390-15-15
