import pytest
from msptc.market import tou_price, mean_price, value_factor

MARKET = {"peak_hours": [10, 11, 18, 19, 20], "valley_hours": [0, 1, 2, 3, 4, 5],
          "price_peak": 1.2, "price_flat": 0.6, "price_valley": 0.3}


def test_tou_price_periods():
    assert tou_price(10, MARKET) == 1.2
    assert tou_price(0, MARKET) == 0.3
    assert tou_price(14, MARKET) == 0.6
    assert tou_price(25, MARKET) == 0.3      # 25%24=1 → 谷


def test_mean_price_between_valley_and_peak():
    assert 0.3 < mean_price(MARKET) < 1.2


def test_value_factor_flat_is_one():
    mp = mean_price(MARKET)
    assert value_factor(2000 * 1000 * mp, 2000.0, mp) == pytest.approx(1.0)


def test_value_factor_peak_above_one():
    mp = mean_price(MARKET)
    assert value_factor(2000 * 1000 * 1.2, 2000.0, mp) > 1.0
