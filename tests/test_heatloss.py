import numpy as np
import pytest
from pathlib import Path
from msptc.io import load_config
from msptc.htf import SolarSalt
from msptc.receiver import ReceiverGeom
from msptc.heatloss import sweep_temperature, fit_hyperbolic


def geom_from_cfg():
    r = load_config(str(Path(__file__).parent.parent / "config" / "default.json"))["receiver"]
    return ReceiverGeom(d_abs_in_m=r["d_abs_in_m"], d_abs_out_m=r["d_abs_out_m"],
                        d_glass_in_m=r["d_glass_in_m"], d_glass_out_m=r["d_glass_out_m"],
                        eps_abs=r["eps_abs"], eps_glass=r["eps_glass"], vacuum=r["vacuum"])


def test_sweep_temperature_increases():
    T, q = sweep_temperature(np.array([300., 400., 500.]), geom_from_cfg(), SolarSalt(),
                             mdot=8.0, q_abs_per_m=3000.0, T_amb_C=25.0, wind=3.0)
    assert q[2] > q[1] > q[0]


def test_fit_hyperbolic_returns_positive_beta():
    vr = np.array([0.2, 0.4, 0.6, 0.8, 1.0])
    q = 1.0 / (1.0 + 2.0 * vr)        # true β=2
    beta = fit_hyperbolic(vr, q)
    assert beta == pytest.approx(2.0, rel=0.1)
