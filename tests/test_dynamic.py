# tests/test_dynamic.py
import numpy as np
import pytest
from pathlib import Path
from msptc.io import load_config
from msptc.htf import SolarSalt
from msptc.optics.analytical import AnalyticalOptics
from msptc.collector import Collector
from msptc.dynamic import simulate, Forcing, DynamicResult, steady_state_temp

def build():
    cfg = load_config(str(Path(__file__).parent.parent / "config" / "default.json"))
    coll = Collector(cfg, AnalyticalOptics(cfg["optics"], cfg["collector"]), SolarSalt())
    return cfg, coll

def const_forcing(dni):
    return Forcing(dni=lambda t: dni, T_amb_C=lambda t: 25.0,
                   wind=lambda t: 3.0, mdot=lambda t: 8.0,
                   theta_deg=lambda t: 10.0, T_in_C=lambda t: 290.0)

def test_dynamic_converges_to_algebraic_steady():
    cfg, coll = build()
    f = const_forcing(900.0)
    res = simulate(f, cfg, coll, t_span=(0, 7200), dt_out=60)
    assert isinstance(res, DynamicResult)
    T_ss = steady_state_temp(f, cfg, coll, t=0.0)
    assert res.T_out_C[-1] == pytest.approx(T_ss, abs=2.0)

def test_thermal_inertia_lag_on_dni_drop():
    cfg, coll = build()
    f = const_forcing(900.0)
    f.dni = lambda t: 900.0 if t < 1800 else 300.0
    res = simulate(f, cfg, coll, t_span=(0, 5400), dt_out=60)
    i_drop = np.argmin(np.abs(res.t - 1800))
    # 温度不瞬变：下降后 60s 内变化有限(热惯性)
    assert res.T_out_C[i_drop] - res.T_out_C[i_drop + 1] < 30.0
    # 最终趋于更低温
    assert res.T_out_C[-1] < res.T_out_C[i_drop]
