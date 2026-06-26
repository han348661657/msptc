"""TMY3 真实气象年解析。

把 TMY3 CSV（2 行元数据 + 1 行列头 + 8760 数据行）解析为标准化逐时记录。
时间约定: TMY3 Hour(1-24) 为当地标准时、区间结束制；取区间中点 (H-1):30 当地时，
按文件时区(Time Zone)换算为 UTC，供太阳几何计算使用。
"""
import csv
import os
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

_REQUIRED = ["Year", "Month", "Day", "Hour", "DNI", "Tdry", "Wspd"]


@dataclass
class WeatherRecord:
    dt_utc: datetime   # 区间中点换算到 UTC（tz-aware）
    dni: float         # W/m²
    t_amb_C: float     # °C
    wind: float        # m/s


@dataclass
class TMYData:
    site: dict[str, float | str]   # {name, lat_deg, lon_deg, elev_m, tz_hours}
    records: list[WeatherRecord]


def load_tmy3(path: str) -> TMYData:
    if not os.path.exists(path):
        raise FileNotFoundError(f"TMY 文件不存在: {path}")
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if len(rows) < 4:
        raise ValueError(f"TMY 文件行数不足（需 ≥4 行）: {path}")

    labels, values, header = rows[0], rows[1], rows[2]

    def meta(label):
        try:
            return values[labels.index(label)]
        except (ValueError, IndexError):
            raise ValueError(f"TMY 文件缺少必需元数据字段: {label}")

    site = {
        "name": meta("City"),
        "lat_deg": float(meta("Latitude")),
        "lon_deg": float(meta("Longitude")),
        "elev_m": float(meta("Elevation")),
        "tz_hours": float(meta("Time Zone")),
    }

    missing = [c for c in _REQUIRED if c not in header]
    if missing:
        raise ValueError(f"TMY 文件缺少必需列: {missing}")
    idx = {c: header.index(c) for c in _REQUIRED}
    tz = site["tz_hours"]

    records = []
    for n, row in enumerate(rows[3:], start=4):
        if not any(cell.strip() for cell in row):
            continue                              # 跳过空尾行
        if len(row) <= max(idx.values()):
            raise ValueError(f"TMY 第 {n} 行字段不全: {row}")
        try:
            Y = int(float(row[idx["Year"]]))
            Mo = int(float(row[idx["Month"]]))
            D = int(float(row[idx["Day"]]))
            H = int(float(row[idx["Hour"]]))
            dni = float(row[idx["DNI"]])
            tdry = float(row[idx["Tdry"]])
            wspd = float(row[idx["Wspd"]])
        except ValueError as e:
            raise ValueError(f"TMY 第 {n} 行存在非数值: {e}")
        if H == 0:
            # 非标准变体: 当日第 24 小时记为 Hour=0（Day 不变），而非标准的 Hour=24
            H = 24
        if not 1 <= H <= 24:
            raise ValueError(f"TMY 第 {n} 行 Hour 取值异常: {H}")
        local_mid = datetime(Y, Mo, D, H - 1, 30)
        dt_utc = (local_mid - timedelta(hours=tz)).replace(tzinfo=timezone.utc)
        records.append(WeatherRecord(dt_utc, max(0.0, dni), tdry, max(0.0, wspd)))

    if len(records) != 8760:
        warnings.warn(f"TMY 数据行数 {len(records)} ≠ 8760", UserWarning)
    return TMYData(site, records)
