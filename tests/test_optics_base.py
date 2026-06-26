import pytest
from msptc.optics.base import OpticalModel, FluxProfile

def test_cannot_instantiate_abstract():
    with pytest.raises(TypeError):
        OpticalModel()

def test_concrete_subclass_default_absorbed_power():
    class Dummy(OpticalModel):
        def __init__(self):
            self.aperture_m = 5.77
        def efficiency(self, theta_deg):
            return 0.75
        def flux_on_absorber(self, theta_deg, dni):
            return FluxProfile(peak_w_m=dni, mean_w_m=dni)
    d = Dummy()
    # θ=0: absorbed = dni*cos0*aperture*η = 900*1*5.77*0.75
    assert d.absorbed_power_per_length(0.0, 900.0) == pytest.approx(900*5.77*0.75, rel=1e-6)
