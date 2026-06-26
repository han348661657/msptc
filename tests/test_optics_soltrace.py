import pytest
from msptc.optics.soltrace import SolTraceAdapter

def make():
    return SolTraceAdapter({"aperture_m": 5.77, "focal_m": 1.71, "sca_length_m": 150.0},
                           {"d_abs_out_m": 0.070})

def test_build_deck_contains_geometry():
    deck = make().build_deck()
    assert "5.77" in deck and "1.71" in deck
    assert "parabolic" in deck.lower() or "trough" in deck.lower()

def test_efficiency_not_implemented_until_soltrace():
    with pytest.raises(NotImplementedError, match="SolTrace"):
        make().efficiency(0.0)
