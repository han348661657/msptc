from scripts.run_aperture_sweep import run_aperture_sweep, APERTURE_CONFIGS


def test_sweep_has_row_per_config_and_elevation(tmp_path):
    df = run_aperture_sweep(outdir=str(tmp_path), elevations=[0, 2801], c_w=1.7e-5)
    assert len(df) == len(APERTURE_CONFIGS) * 2 * 2   # config × elev × htf
    assert {"gamma", "concentration", "eta_solar_to_elec", "elev_m", "aperture_m"} <= set(df.columns)


def test_gamma_drops_with_aperture_same_receiver(tmp_path):
    df = run_aperture_sweep(outdir=str(tmp_path), elevations=[0], c_w=1.7e-5)
    d = df[(df["htf_type"] == "solar_salt") & (df["d_abs_out_m"] == 0.070)]
    g577 = d[d["aperture_m"] == 5.77]["gamma"].values[0]
    g86 = d[d["aperture_m"] == 8.6]["gamma"].values[0]
    assert g86 < g577


def test_larger_receiver_recovers_gamma(tmp_path):
    df = run_aperture_sweep(outdir=str(tmp_path), elevations=[0], c_w=1.7e-5)
    d = df[(df["htf_type"] == "solar_salt") & (df["aperture_m"] == 8.6)]
    g70 = d[d["d_abs_out_m"] == 0.070]["gamma"].values[0]
    g90 = d[d["d_abs_out_m"] == 0.090]["gamma"].values[0]
    assert g90 > g70


def test_altitude_synergy_for_large_aperture(tmp_path):
    df = run_aperture_sweep(outdir=str(tmp_path), elevations=[0, 2801], c_w=1.7e-5)
    d = df[(df["htf_type"] == "solar_salt") & (df["aperture_m"] == 8.6) & (df["d_abs_out_m"] == 0.090)]
    g_sea = d[d["elev_m"] == 0]["gamma"].values[0]
    g_alt = d[d["elev_m"] == 2801]["gamma"].values[0]
    assert g_alt > g_sea
