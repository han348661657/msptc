import pytest
from msptc.environment import co2_avoided_tonnes


def test_co2_avoided():
    assert co2_avoided_tonnes(3000.0, 0.58) == pytest.approx(1740.0)


def test_co2_zero_when_no_generation():
    assert co2_avoided_tonnes(0.0, 0.58) == 0.0
