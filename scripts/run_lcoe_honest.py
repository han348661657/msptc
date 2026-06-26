"""Paper A — honest LCOE figure (Figure_09): the freeze penalty reverses the
HTF cost ranking.

Two panels:
  (a) LCOE vs storage duration under the idealized clear-sky comparison (freeze
      excluded) vs the realistic TMY-altitude comparison at Golmud (freeze
      included). The ranking reverses.
  (b) Decomposition at 6 h storage across three regimes (clear-sky / TMY-no-freeze
      / TMY+freeze): moving to TMY irradiance preserves the salt's lead; the freeze
      charge is what reverses the ranking — so freeze, not the irradiance
      reduction, makes thermal oil cheaper.

This is the decision-relevant counterpart to the idealized storage-value sweep in
run_storage_htf_value (which excludes freeze).

Run: python -m scripts.run_lcoe_honest  (slow: full 8760-h loops).
"""
import argparse
import copy
import os
from datetime import timedelta
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from msptc.io import load_config
from msptc.solar import solar_position, incidence_angle, dni_clear_sky
from msptc.system import build_collector, design_point
from msptc.powerblock import PowerBlock
from msptc.storage import TwoTankStorage
from msptc.atmosphere import AirProperties
from msptc.market import tou_price, value_factor, mean_price, annual_step_priced
from msptc.economics import capex_total, lcoe
from msptc.freeze import freeze_parasitic_W
from msptc.weather import load_tmy3
from scripts.run_system_annual import _clearsky_records

DNI_MIN, DT_S, SM = 50.0, 3600.0, 2.5
HTF = [("solar_salt", 540.0, False), ("therminol_vp1", 390.0, True)]


def _setup_font():
    from matplotlib import rcParams
    rcParams["font.family"] = ["Times New Roman"]
    rcParams["axes.unicode_minus"] = False
    rcParams["mathtext.fontset"] = "stix"
    rcParams["pdf.fonttype"] = 42
    rcParams["ps.fonttype"] = 42


def _lcoe_one(cfg, htf, T_hot, indirect, hours, site, records, air, sky,
              account_freeze, guard):
    c = copy.deepcopy(cfg)
    coll = build_collector(c, htf, air=air, sky_model=sky)
    pb = PowerBlock(c)
    P_rated = design_point(c, htf, T_hot_C=T_hot)["Q_useful_W"] / SM
    c["storage"]["hours"] = hours
    cap_J = hours * 3600.0 * P_rated
    c["storage"]["tank_UA_W_K"] = (0.015 * cap_J / 86400.0 / max(T_hot - 25.0, 1.0)) if cap_J > 0 else 0.0
    storage = TwoTankStorage(c, coll.htf, P_rated, indirect=indirect)
    T_cold, mdot = c["htf"]["T_cold_C"], c["htf"]["mdot_kg_s"]
    market, econ = c["market"], c["economics"]
    price_hi = market["price_flat"]
    E = Ef = 0.0
    for dt, dni_m, t_amb, wind in records:
        sun = solar_position(dt, site)
        Q, Th, dni = 0.0, T_hot, 0.0
        if sun.zenith_deg < 88.0:
            th = incidence_angle(sun, site.get("axis", "NS"))
            if th < 75.0:
                dni = dni_clear_sky(sun.zenith_deg, site) if dni_m is None else dni_m
                if dni >= DNI_MIN:
                    r = coll.simulate_steady(T_cold, mdot, dni, th, t_amb, wind)
                    Q, Th = max(r.Q_useful_W, 0.0), r.T_out_C
        price = tou_price((dt + timedelta(hours=site.get("tz_hours", 8))).hour, market)
        P, _, _ = annual_step_priced(coll, pb, storage, P_rated, Th, Q, t_amb, DT_S, price, price_hi)
        E += P * DT_S
        if account_freeze:
            Ef += freeze_parasitic_W(coll.htf, coll.geom, t_amb, wind, coll.L_total,
                                     dni < DNI_MIN, air=air, sky_model=sky, guard_margin_C=guard) * DT_S
    net = (E - Ef) / 3.6e9
    ap = coll.aperture_m * coll.L_total
    capex = capex_total(econ, ap, cap_J / 3.6e6, P_rated * pb.cycle_efficiency(T_hot)[1] / 1e6, indirect)
    return lcoe(capex, econ["opex_frac"] * capex, net, econ["discount_rate"], econ["lifetime_years"])


def _write_decomposition_table(outdir, dec, storage_hours=6):
    rows = []
    basis_names = [
        "clear_sky_freeze_excluded",
        "tmy_freeze_excluded",
        "tmy_freeze_included",
    ]
    for htf, values in dec.items():
        for basis, value in zip(basis_names, values):
            rows.append({
                "basis": basis,
                "htf_type": htf,
                "storage_hours": storage_hours,
                "LCOE_CNY_MWh": value,
            })
    path = os.path.join(outdir, "Table_09_lcoe_decomposition.csv")
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _write_guard_sensitivity_table(cfg, outdir, guards, site_tmy, tmy_recs, air, sky):
    rows = []
    for guard in guards:
        for hours in (3, 6):
            values = {}
            for htf, T, ind in HTF:
                values[htf] = _lcoe_one(
                    cfg, htf, T, ind, hours, site_tmy, tmy_recs, air, sky,
                    True, guard,
                )
            delta = values["solar_salt"] - values["therminol_vp1"]
            winner = "solar_salt" if delta <= 0 else "therminol_vp1"
            for htf, value in values.items():
                rows.append({
                    "guard_margin_C": guard,
                    "storage_hours": hours,
                    "htf_type": htf,
                    "LCOE_CNY_MWh": value,
                    "delta_salt_minus_oil_CNY_MWh": delta,
                    "winner": winner,
                })
    path = os.path.join(outdir, "Table_10_freeze_guard_sensitivity.csv")
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _build_honest_lcoe_figure(hours, cs, tm, dec):
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(11, 4.3))
    style = {
        "solar_salt": ("C0", "o", "Solar Salt"),
        "therminol_vp1": ("C1", "s", "Therminol VP-1"),
    }
    for htf, (col, mk, lab) in style.items():
        axa.plot(hours, cs[htf], color=col, marker=mk, ls="--", alpha=0.45,
                 lw=1.4, label=f"{lab} - clear-sky, freeze excl.")
        axa.plot(hours, tm[htf], color=col, marker=mk, ls="-", lw=2.0,
                 label=f"{lab} - TMY, freeze incl.")

    h6 = hours.index(6)
    tmy_gap = tm["solar_salt"][h6] - tm["therminol_vp1"][h6]
    axa.axvline(6, color="0.35", ls=":", lw=1.0)
    axa.annotate(f"6 h reversal\noil lower by {tmy_gap:.0f}",
                 (6, tm["solar_salt"][h6]), textcoords="offset points",
                 xytext=(18, 22), fontsize=8, color="0.25",
                 arrowprops=dict(arrowstyle="->", color="0.35", lw=0.9))
    axa.set_xlabel("Thermal-storage hours (h)")
    axa.set_ylabel("LCOE (CNY/MWh)")
    axa.set_title("(a) Cost vs storage: realistic weather reverses the ranking")
    axa.set_xticks(hours)
    axa.legend(fontsize=7, loc="upper right", framealpha=0.9)
    axa.grid(True, alpha=0.28)

    labels = ["Clear-sky\n(freeze excl.)", "TMY\n(freeze excl.)", "TMY\n(freeze incl.)"]
    x = np.arange(3)
    w = 0.36
    bars_s = axb.bar(x - w / 2, dec["solar_salt"], w, color="C0", label="Solar Salt")
    bars_o = axb.bar(x + w / 2, dec["therminol_vp1"], w, color="C1", label="Therminol VP-1")
    for bars in (bars_s, bars_o):
        for bar in bars:
            axb.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 12,
                     f"{bar.get_height():.0f}", ha="center", va="bottom", fontsize=8)
    freeze_gap = dec["solar_salt"][2] - dec["therminol_vp1"][2]
    ymax = max(max(dec["solar_salt"]), max(dec["therminol_vp1"])) * 1.18
    axb.set_ylim(0, ymax)
    axb.text(0.98, 0.92, f"oil lower by {freeze_gap:.0f}",
             transform=axb.transAxes, ha="right", va="top", fontsize=8, color="0.25")
    axb.set_xticks(x)
    axb.set_xticklabels(labels, fontsize=8)
    axb.set_ylabel("LCOE at 6 h storage (CNY/MWh)")
    axb.set_title("(b) Attribution at 6 h: freeze flips it")
    axb.legend(fontsize=8, loc="upper left")
    axb.grid(True, alpha=0.28, axis="y")
    fig.tight_layout()
    return fig


def run(config_path="config/default.json", outdir="results/paper_a", pdf=True, year=2023,
        sensitivity_guards=None):
    _setup_font()
    cfg = load_config(config_path)
    guard = cfg.get("freeze", {}).get("guard_margin_C", 12.0)
    tmy = load_tmy3("data/CHN_QH_GEERMU_TMY3.csv")
    site_tmy = {**cfg["site"], "lat_deg": tmy.site["lat_deg"], "lon_deg": tmy.site["lon_deg"], "elev_m": tmy.site["elev_m"]}
    air = AirProperties(tmy.site["elev_m"])
    tmy_recs = [(r.dt_utc, r.dni, r.t_amb_C, r.wind) for r in tmy.records]
    site_cs = cfg["site"]
    hours = [0, 3, 6, 9, 12]

    # Panel (a): clear-sky (no freeze) vs TMY (freeze) LCOE vs storage
    cs, tm = {}, {}
    for htf, T, ind in HTF:
        cs[htf] = [_lcoe_one(cfg, htf, T, ind, h, site_cs, list(_clearsky_records(year, 10.0, 3.0)),
                             air, "swinbank", False, guard) for h in hours]
        tm[htf] = [_lcoe_one(cfg, htf, T, ind, h, site_tmy, tmy_recs, air, "swinbank", True, guard) for h in hours]

    # Decomposition at 6 h: add TMY irradiance WITHOUT freeze (isolates freeze)
    h6 = hours.index(6)
    dec = {}  # [clear-sky, TMY-no-freeze, TMY+freeze]
    for htf, T, ind in HTF:
        tnf = _lcoe_one(cfg, htf, T, ind, 6, site_tmy, tmy_recs, air, "swinbank", False, guard)
        dec[htf] = [cs[htf][h6], tnf, tm[htf][h6]]

    fig = _build_honest_lcoe_figure(hours, cs, tm, dec)
    os.makedirs(outdir, exist_ok=True)
    base = os.path.join(outdir, "Figure_09_lcoe_honest")
    fig.savefig(base + ".png", dpi=150)
    if pdf:
        fig.savefig(base + ".pdf")
    plt.close(fig)
    decomposition_path = _write_decomposition_table(outdir, dec, storage_hours=6)
    if sensitivity_guards is None:
        sensitivity_guards = [0.0, 6.0, 12.0, 18.0]
    sensitivity_path = _write_guard_sensitivity_table(
        cfg, outdir, sensitivity_guards, site_tmy, tmy_recs, air, "swinbank",
    )
    print("clear-sky LCOE:", {k: [round(x, 1) for x in v] for k, v in cs.items()})
    print("TMY+freeze LCOE:", {k: [round(x, 1) for x in v] for k, v in tm.items()})
    print("6h decomp [CS, TMY-nofreeze, TMY+freeze]:", {k: [round(x, 1) for x in v] for k, v in dec.items()})
    print("output:", base + ".png")
    print("decomposition table:", decomposition_path)
    print("guard sensitivity table:", sensitivity_path)
    return base + ".png"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Paper A honest LCOE figure (clear-sky vs TMY + ambient crossover)")
    ap.add_argument("--config", default="config/default.json")
    ap.add_argument("--outdir", default="results/paper_a")
    ap.add_argument("--no-pdf", action="store_false", dest="pdf")
    ap.add_argument("--sensitivity-guards", nargs="*", type=float, default=None,
                    help="Freeze guard margins in C for Table_10 sensitivity output")
    a = ap.parse_args()
    run(a.config, outdir=a.outdir, pdf=a.pdf, sensitivity_guards=a.sensitivity_guards)
