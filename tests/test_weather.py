import warnings
from datetime import datetime, timezone
from pathlib import Path

import pytest

from msptc.weather import load_tmy3, TMYData, WeatherRecord

FIXTURE = str(Path(__file__).parent / "fixtures" / "tmy3_sample.csv")


def _load_fixture():
    # fixture 仅 24 行 → load_tmy3 会对 ≠8760 发 UserWarning，测试中忽略
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return load_tmy3(FIXTURE)


def test_load_returns_tmydata():
    data = _load_fixture()
    assert isinstance(data, TMYData)
    assert len(data.records) == 24
    assert all(isinstance(r, WeatherRecord) for r in data.records)


def test_site_metadata_parsed():
    site = _load_fixture().site
    assert site["lat_deg"] == pytest.approx(36.42)
    assert site["lon_deg"] == pytest.approx(95.22)
    assert site["elev_m"] == pytest.approx(2801)
    assert site["tz_hours"] == pytest.approx(8)


def test_hour14_maps_to_utc_0530_and_fields():
    # Hour=14 是第 14 条记录(index 13)；区间中点当地 13:30，tz=8 → UTC 05:30
    rec = _load_fixture().records[13]
    assert rec.dt_utc == datetime(2010, 1, 1, 5, 30, tzinfo=timezone.utc)
    assert rec.dni == pytest.approx(862.575)
    assert rec.t_amb_C == pytest.approx(-3.7)
    assert rec.wind == pytest.approx(2.6)


def test_negative_values_clamped_to_zero(tmp_path):
    bad = tmp_path / "neg.csv"
    bad.write_text(
        "Source,Location ID,City,State,Country,Latitude,Longitude,Time Zone,Elevation,,,,,\n"
        "TMY3,,X,Y,CN,30,100,8,1000,,,,,\n"
        "Year,Month,Day,Hour,GHI,DNI,DHI,Tdry,Twet,RH,Pres,Wspd,Wdir,Albedo\n"
        "2010,1,1,12,0,-50,0,5,0,40,900,-2,180,0\n"
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rec = load_tmy3(str(bad)).records[0]
    assert rec.dni == 0.0
    assert rec.wind == 0.0


def test_missing_required_column_raises(tmp_path):
    bad = tmp_path / "nodni.csv"
    bad.write_text(
        "Source,Location ID,City,State,Country,Latitude,Longitude,Time Zone,Elevation,,,,,\n"
        "TMY3,,X,Y,CN,30,100,8,1000,,,,,\n"
        "Year,Month,Day,Hour,GHI,DHI,Tdry,Twet,RH,Pres,Wspd,Wdir,Albedo\n"
        "2010,1,1,12,0,0,5,0,40,900,2,180,0\n"
    )
    with pytest.raises(ValueError, match="DNI"):
        load_tmy3(str(bad))


def test_file_not_found_raises():
    with pytest.raises(FileNotFoundError):
        load_tmy3("does/not/exist.csv")


def test_row_count_not_8760_warns():
    with pytest.warns(UserWarning, match="8760"):
        load_tmy3(FIXTURE)


def test_hour0_treated_as_hour24(tmp_path):
    # 非标准变体: 当日第24小时记为 Hour=0(Day 不变)，而非 Hour=24
    f = tmp_path / "hour0.csv"
    f.write_text(
        "Source,Location ID,City,State,Country,Latitude,Longitude,Time Zone,Elevation,,,,,\n"
        "TMY3,,X,Y,CN,30,100,8,1000,,,,,\n"
        "Year,Month,Day,Hour,GHI,DNI,DHI,Tdry,Twet,RH,Pres,Wspd,Wdir,Albedo\n"
        "2010,1,1,23,0,0,0,-5,0,60,900,1,180,0\n"
        "2010,1,1,0,0,10,0,-6,0,60,900,1,180,0\n"
        "2010,1,2,1,0,20,0,-7,0,60,900,1,180,0\n"
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = load_tmy3(str(f))
    # Hour=0 行应被视为 1月1日的第24小时: 区间中点 1日23:30 当地, tz=8 -> UTC 15:30 (同日)
    rec = data.records[1]
    assert rec.dt_utc == datetime(2010, 1, 1, 15, 30, tzinfo=timezone.utc)
    assert rec.dni == pytest.approx(10.0)


def test_hour_out_of_range_raises(tmp_path):
    bad = tmp_path / "badhour.csv"
    bad.write_text(
        "Source,Location ID,City,State,Country,Latitude,Longitude,Time Zone,Elevation,,,,,\n"
        "TMY3,,X,Y,CN,30,100,8,1000,,,,,\n"
        "Year,Month,Day,Hour,GHI,DNI,DHI,Tdry,Twet,RH,Pres,Wspd,Wdir,Albedo\n"
        "2010,1,1,25,0,0,0,5,0,40,900,2,180,0\n"
    )
    with pytest.raises(ValueError, match="Hour"):
        load_tmy3(str(bad))
