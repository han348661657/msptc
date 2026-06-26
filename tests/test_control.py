import pytest
from pathlib import Path
from msptc.io import load_config
from msptc.htf import SolarSalt
from msptc.optics.analytical import AnalyticalOptics
from msptc.collector import Collector
from msptc.control import freeze_protection, CollectorEnv


def build():
    cfg = load_config(str(Path(__file__).parent.parent / "config" / "default.json"))
    coll = Collector(cfg, AnalyticalOptics(cfg["optics"], cfg["collector"]), SolarSalt())
    return cfg, coll


def test_freeze_protection_forces_min_flow_when_cold():
    cfg, _ = build()
    mdot = freeze_protection(T_C=240.0, mdot_request=8.0, cfg=cfg)
    assert mdot <= 0.5         # 低于防凝阈值 → 最小流量/再循环
    mdot2 = freeze_protection(T_C=400.0, mdot_request=8.0, cfg=cfg)
    assert mdot2 == pytest.approx(8.0)


def test_env_reset_step_returns_state():
    cfg, coll = build()
    env = CollectorEnv(cfg, coll, dni_profile=lambda t: 900.0)
    s0 = env.reset()
    assert "T_out_C" in s0 and "dni" in s0
    s1, reward, info = env.step({"mdot": 8.0, "defocus": 0.0})
    assert "T_out_C" in s1
    assert isinstance(reward, float)


def test_env_cost_penalizes_freeze_violation():
    cfg, coll = build()
    env = CollectorEnv(cfg, coll, dni_profile=lambda t: 0.0)
    c_cold = env.cost({"T_out_C": 240.0}, {"mdot": 8.0, "defocus": 0.0})
    c_ok = env.cost({"T_out_C": 400.0}, {"mdot": 8.0, "defocus": 0.0})
    assert c_cold > c_ok
