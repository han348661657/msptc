import pathlib
from msptc.io import load_config, REQUIRED_SECTIONS

def test_load_default_config_has_all_sections():
    cfg_path = pathlib.Path(__file__).parent.parent / "config" / "default.json"
    cfg = load_config(str(cfg_path))
    for sec in REQUIRED_SECTIONS:
        assert sec in cfg, f"缺少配置段: {sec}"
    assert cfg["collector"]["aperture_m"] == 5.77
    assert cfg["htf"]["type"] == "solar_salt"

def test_load_config_missing_section_raises(tmp_path):
    import json
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"site": {}}), encoding="utf-8")
    import pytest
    with pytest.raises(ValueError, match="缺少配置段"):
        load_config(str(p))

def test_config_has_powerblock_and_storage():
    from pathlib import Path
    from msptc.io import load_config
    cfg = load_config(str(Path(__file__).parent.parent / "config" / "default.json"))
    assert cfg["powerblock"]["f_2nd"] == 0.74
    assert cfg["storage"]["hours"] == 6.0
    assert cfg["storage"]["solar_multiple"] == 1.0

def test_config_has_atmosphere_and_freeze():
    from pathlib import Path
    from msptc.io import load_config
    cfg = load_config(str(Path(__file__).parent.parent / "config" / "default.json"))
    assert cfg["atmosphere"]["sky_model"] == "swinbank"
    assert cfg["freeze"]["guard_margin_C"] == 12.0

def test_config_has_economics_market_environment():
    from pathlib import Path
    from msptc.io import load_config
    cfg = load_config(str(Path(__file__).parent.parent / "config" / "default.json"))
    assert cfg["economics"]["discount_rate"] == 0.08
    assert cfg["market"]["price_peak"] == 1.2
    assert cfg["environment"]["grid_factor_kg_per_kWh"] == 0.58
