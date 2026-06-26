import pytest
from msptc.powerblock import PowerBlock, PowerResult

CFG = {"powerblock": {"T_cond_C": 45.0, "dT_pinch_C": 28.0,
                      "f_2nd": 0.74, "parasitic_frac": 0.10}}


def test_oil_design_point_efficiency():
    # 导热油送入 393°C → 毛效率 ~0.375 (文献 SEGS 槽式油机)
    pb = PowerBlock(CFG)
    eg, _ = pb.cycle_efficiency(393.0)
    assert 0.36 < eg < 0.39


def test_salt_design_point_efficiency():
    # 熔盐送入 540°C → 毛效率 ~0.44 (文献先进熔盐机组)
    pb = PowerBlock(CFG)
    eg, _ = pb.cycle_efficiency(540.0)
    assert 0.42 < eg < 0.46


def test_salt_more_efficient_than_oil():
    pb = PowerBlock(CFG)
    assert pb.cycle_efficiency(540.0)[0] > pb.cycle_efficiency(393.0)[0]


def test_net_below_gross():
    pb = PowerBlock(CFG)
    eg, en = pb.cycle_efficiency(500.0)
    assert en == pytest.approx(eg * 0.90, rel=1e-9)


def test_electric_power_scales_with_thermal():
    pb = PowerBlock(CFG)
    r = pb.electric_power(500.0, 1.0e6)
    assert isinstance(r, PowerResult)
    assert r.P_elec_W == pytest.approx(r.eta_net * 1.0e6, rel=1e-9)


def test_below_condenser_returns_zero():
    # 送入温度低于冷凝温度+夹点 → 零功率，不出现负效率
    pb = PowerBlock(CFG)
    eg, en = pb.cycle_efficiency(50.0)
    assert eg == 0.0 and en == 0.0
    assert pb.electric_power(50.0, 1.0e6).P_elec_W == 0.0
