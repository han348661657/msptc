import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pytest
from matplotlib import rcParams
from scripts.run_paper_figures import (
    run_paper_figures, _fig_F1_efficiency_dual, _fig_F2_exergy_waterfall,
    _fig_F3_freeze_vs_altitude, _fig_F8_value_heatmap,
    _fig_F4_heatloss_dual_panel, _fig_F5_annual_comparison,
    _fig_F6_lcoe_vs_storage,
)
from scripts.run_storage_htf_value import run_storage_htf_value
from scripts.run_altitude_sweep import run_altitude_sweep
from scripts.run_aperture_sweep import run_aperture_sweep


def _two_days():
    start = datetime(2023, 6, 1, 0, 30, tzinfo=timezone.utc)
    for h in range(48):
        yield start + timedelta(hours=h)


def _write_annual_tables(outdir):
    rows = (
        "htf_type,P_elec_MWh\n"
        "solar_salt,100\n"
        "therminol_vp1,90\n"
    )
    for name in (
        "Table_04_system_annual_clearsky_sea_level.csv",
        "Table_05_system_annual_clearsky_golmud.csv",
        "Table_06_system_annual_tmy_sea_level.csv",
        "Table_07_system_annual_tmy_golmud.csv",
    ):
        with open(os.path.join(outdir, name), "w", encoding="utf-8") as f:
            f.write(rows)


def test_figures_created(tmp_path):
    _write_annual_tables(str(tmp_path))
    # 价值扫描内部跑年度循环, patch 为 2 天加速
    with patch("scripts.run_system_annual._hours_of_year",
               side_effect=lambda *a, **k: _two_days()):
        paths = run_paper_figures(outdir=str(tmp_path), pdf=False)
    # Manuscript package generates Fig. 1-6 here; Fig. 7 is produced by run_lcoe_honest.
    assert len(paths) >= 6
    assert os.path.exists(os.path.join(str(tmp_path), "Table_01_altitude_sweep.csv"))
    assert os.path.exists(os.path.join(str(tmp_path), "Table_02_storage_htf_value.csv"))
    assert os.path.exists(os.path.join(str(tmp_path), "Table_08_heatloss_split.csv"))
    assert os.path.exists(os.path.join(str(tmp_path), "Figure_05_annual_comparison.png"))
    names = {os.path.basename(p) for p in paths}
    assert "Figure_07_valuefactor_vs_storage.png" not in names
    assert "Figure_08_value_heatmap.png" not in names
    for p in paths:
        assert os.path.exists(p) and p.endswith(".png")


def test_F1_efficiency_uses_two_panel_layout(tmp_path, monkeypatch):
    df_alt = run_altitude_sweep(outdir=str(tmp_path), csv_name="Table_01_altitude_sweep.csv")
    saved = {}
    rcParams["font.family"] = ["DejaVu Sans"]

    def fake_save(fig, fname, outdir, pdf=True):
        saved["axes_titles"] = [ax.get_title() for ax in fig.axes]
        saved["font_family"] = list(rcParams["font.family"])
        saved["mathtext_fontset"] = rcParams["mathtext.fontset"]
        saved["pdf_fonttype"] = rcParams["pdf.fonttype"]
        return os.path.join(outdir, fname)

    monkeypatch.setattr("scripts.run_paper_figures._save", fake_save)
    p = _fig_F1_efficiency_dual(df_alt, outdir=str(tmp_path), pdf=False)

    assert os.path.basename(p) == "Figure_01_efficiency_vs_altitude.png"
    assert saved["axes_titles"] == [
        "Absolute Efficiency Level",
        "Altitude Effect vs. Sea Level",
    ]
    assert saved["font_family"][0] == "Times New Roman"
    assert saved["mathtext_fontset"] == "stix"
    assert saved["pdf_fonttype"] == 42


def test_F2_exergy_waterfall(tmp_path):
    p = _fig_F2_exergy_waterfall("config/default.json", outdir=str(tmp_path), pdf=False)
    assert os.path.exists(p)


def test_F3_freeze_vs_altitude(tmp_path):
    p = _fig_F3_freeze_vs_altitude("config/default.json", outdir=str(tmp_path), pdf=False)
    assert os.path.exists(p)
    assert os.path.getsize(p) > 1000  # 非空 PNG


def test_F3_freeze_uses_log_power_and_ratio_panels(tmp_path, monkeypatch):
    saved = {}

    def fake_save(fig, fname, outdir, pdf=True):
        saved["axes_count"] = len(fig.axes)
        saved["yscales"] = [ax.get_yscale() for ax in fig.axes]
        saved["ylabels"] = [ax.get_ylabel() for ax in fig.axes]
        saved["titles"] = [ax.get_title() for ax in fig.axes]
        return os.path.join(outdir, fname)

    monkeypatch.setattr("scripts.run_paper_figures._save", fake_save)
    _fig_F3_freeze_vs_altitude("config/default.json", outdir=str(tmp_path), pdf=False)

    assert saved["axes_count"] == 2
    assert saved["yscales"][0] == "log"
    assert "Salt / Oil" in saved["ylabels"][1]
    assert all("dual" not in title.lower() for title in saved["titles"])
    assert all("$" not in title and r"\rm" not in title for title in saved["titles"])


def test_F6_lcoe_vs_storage_uses_mechanism_delta_panel(tmp_path, monkeypatch):
    df = run_storage_htf_value(outdir=str(tmp_path), storage_hours=[0, 3, 6])
    saved = {}

    def fake_save(fig, fname, outdir, pdf=True):
        saved["axes_count"] = len(fig.axes)
        saved["ylabels"] = [ax.get_ylabel() for ax in fig.axes]
        saved["titles"] = [ax.get_title() for ax in fig.axes]
        return os.path.join(outdir, fname)

    monkeypatch.setattr("scripts.run_paper_figures._save", fake_save)
    p = _fig_F6_lcoe_vs_storage(df, outdir=str(tmp_path), pdf=False)

    assert os.path.basename(p) == "Figure_06_lcoe_vs_storage.png"
    assert saved["axes_count"] == 2
    assert saved["ylabels"][0] == "LCOE (CNY/MWh)"
    assert "Salt - Oil" in saved["ylabels"][1]
    assert saved["titles"] == ["", ""]


def test_F4_heatloss_dual_panel(tmp_path):
    df_alt = run_altitude_sweep(outdir=str(tmp_path), csv_name="Table_01_altitude_sweep.csv")
    p = _fig_F4_heatloss_dual_panel(df_alt, outdir=str(tmp_path), pdf=False)
    assert os.path.basename(p) == "Figure_04_heatloss_vs_altitude.png"
    assert os.path.exists(p)
    assert os.path.getsize(p) > 1000


def test_F5_fails_with_commands_when_annual_tables_missing(tmp_path):
    with pytest.raises(RuntimeError) as exc:
        _fig_F5_annual_comparison(str(tmp_path), pdf=False)

    message = str(exc.value)
    assert "Figure_05_annual_comparison.png" in message
    assert "python -m scripts.run_system_annual --weather clearsky --outdir" in message
    assert "python -m scripts.run_system_annual --weather tmy --altitude --outdir" in message
    assert "Table_04_system_annual_clearsky_sea_level.csv" in message


def test_F5_accepts_legacy_system_annual_sea_alt_names(tmp_path):
    rows = (
        "htf_type,P_elec_MWh\n"
        "solar_salt,100\n"
        "therminol_vp1,90\n"
    )
    for name in (
        "system_annual_clearsky_sea_2023.csv",
        "system_annual_clearsky_alt_2023.csv",
        "system_annual_tmy_sea_2023.csv",
        "system_annual_tmy_alt_2023.csv",
    ):
        with open(os.path.join(str(tmp_path), name), "w", encoding="utf-8") as f:
            f.write(rows)

    p = _fig_F5_annual_comparison(str(tmp_path), pdf=False)

    assert os.path.basename(p) == "Figure_05_annual_comparison.png"
    assert os.path.exists(p)


def test_F8_value_heatmap(tmp_path):
    with patch("scripts.run_system_annual._hours_of_year",
               side_effect=lambda *a, **k: _two_days()):
        df = run_storage_htf_value(outdir=str(tmp_path), storage_hours=[0, 6])
    p = _fig_F8_value_heatmap(df, outdir=str(tmp_path), pdf=False)
    assert os.path.exists(p)


from scripts.run_paper_figures import (
    run_aperture_figures, _fig_F11_altitude_synergy, _fig_F9_gamma_vs_aperture,
    _fig_F10_concentration_heatloss,
)


def test_F11_altitude_synergy_uses_gain_curve_with_sensitivity_band(tmp_path, monkeypatch):
    df_ap = run_aperture_sweep(outdir=str(tmp_path), elevations=[0, 2801], c_w=1.7e-5,
                               csv_name="Table_01_aperture_sweep.csv")
    saved = {}

    def fake_save(fig, fname, outdir, pdf=True):
        ax = fig.axes[0]
        saved["fname"] = fname
        saved["axes_count"] = len(fig.axes)
        saved["patch_count"] = len(ax.patches)
        saved["collection_count"] = len(ax.collections)
        saved["line_labels"] = [line.get_label() for line in ax.lines]
        saved["ylabel"] = ax.get_ylabel()
        saved["texts"] = [text.get_text() for text in ax.texts]
        return os.path.join(outdir, fname)

    monkeypatch.setattr("scripts.run_paper_figures._save", fake_save)
    p = _fig_F11_altitude_synergy(df_ap, outdir=str(tmp_path), pdf=False)

    assert os.path.basename(p) == "Figure_03_altitude_synergy.png"
    assert saved["axes_count"] == 1
    assert saved["patch_count"] == 0
    assert saved["collection_count"] >= 1
    assert "Central coefficients" in saved["line_labels"]
    assert saved["ylabel"] == "Altitude gain Δγ (x 10^-3)"
    assert any("70 mm absorber" in text for text in saved["texts"])
    assert "⁻" not in saved["ylabel"]


def test_F9_gamma_vs_aperture_includes_80mm_and_no_title(tmp_path, monkeypatch):
    saved = {}

    def fake_save(fig, fname, outdir, pdf=True):
        ax = fig.axes[0]
        saved["fname"] = fname
        saved["title"] = ax.get_title()
        saved["legend_labels"] = [text.get_text() for text in ax.get_legend().texts]
        return os.path.join(outdir, fname)

    monkeypatch.setattr("scripts.run_paper_figures._save", fake_save)
    p = _fig_F9_gamma_vs_aperture("config/default.json", outdir=str(tmp_path), pdf=False)

    assert os.path.basename(p) == "Figure_01_gamma_vs_aperture.png"
    assert saved["title"] == ""
    assert "Absorber OD 80 mm" in saved["legend_labels"]


def test_F10_concentration_heatloss_uses_two_panel_layout(tmp_path, monkeypatch):
    df_ap = run_aperture_sweep(outdir=str(tmp_path), elevations=[0], c_w=1.7e-5,
                               csv_name="Table_01_aperture_sweep.csv")
    saved = {}

    def fake_save(fig, fname, outdir, pdf=True):
        saved["fname"] = fname
        saved["axes_count"] = len(fig.axes)
        saved["titles"] = [ax.get_title() for ax in fig.axes]
        return os.path.join(outdir, fname)

    monkeypatch.setattr("scripts.run_paper_figures._save", fake_save)
    p = _fig_F10_concentration_heatloss(df_ap, outdir=str(tmp_path), pdf=False)

    assert os.path.basename(p) == "Figure_02_concentration_heatloss.png"
    assert saved["axes_count"] == 2
    assert saved["titles"] == ["", ""]


def test_paper_b_figures_use_times_new_roman(tmp_path, monkeypatch):
    df_ap = run_aperture_sweep(outdir=str(tmp_path), elevations=[0], c_w=1.7e-5,
                               csv_name="Table_01_aperture_sweep.csv")
    saved = {}

    def fake_save(fig, fname, outdir, pdf=True):
        saved["font_family"] = list(rcParams["font.family"])
        saved["mathtext_fontset"] = rcParams["mathtext.fontset"]
        saved["pdf_fonttype"] = rcParams["pdf.fonttype"]
        return os.path.join(outdir, fname)

    monkeypatch.setattr("scripts.run_paper_figures._save", fake_save)
    _fig_F9_gamma_vs_aperture("config/default.json", outdir=str(tmp_path), pdf=False)

    assert saved["font_family"][0] == "Times New Roman"
    assert saved["mathtext_fontset"] == "stix"
    assert saved["pdf_fonttype"] == 42


def test_aperture_figures_created(tmp_path):
    paths = run_aperture_figures(outdir=str(tmp_path), pdf=False, c_w=1.7e-5)
    names = {os.path.basename(p) for p in paths}
    # Figure_04_efficiency_vs_aperture 已从 Paper B 投稿包移除(效率章移交 companion paper)。
    assert {"Figure_01_gamma_vs_aperture.png", "Figure_02_concentration_heatloss.png",
            "Figure_03_altitude_synergy.png",
            "Figure_05_intercept_validation.png"} <= names
    assert "Figure_04_efficiency_vs_aperture.png" not in names
    assert os.path.exists(os.path.join(str(tmp_path), "Table_01_aperture_sweep.csv"))
    for p in paths:
        assert os.path.exists(p)
