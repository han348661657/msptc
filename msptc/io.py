# msptc/io.py
"""配置加载、结果导出、绘图字体配置。"""
import json
import os

REQUIRED_SECTIONS = ("site", "collector", "receiver", "optics", "htf", "sim", "metal")


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for sec in REQUIRED_SECTIONS:
        if sec not in cfg:
            raise ValueError(f"缺少配置段: {sec}")
    return cfg


def export_csv(df, name: str, outdir: str = "output") -> str:
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, name)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def setup_cn_font():
    """中文字体配置（移植项目8）。"""
    from matplotlib import rcParams
    from matplotlib.font_manager import findfont, FontProperties
    for font in ["STHeiti", "Heiti TC", "Arial Unicode MS", "SimHei"]:
        fp = FontProperties(family=font)
        try:
            findfont(fp, fallback_to_default=False)
            rcParams["font.family"] = [font, "sans-serif"]
            break
        except ValueError:
            pass
    rcParams["axes.unicode_minus"] = False
    rcParams["mathtext.fontset"] = "stix"
