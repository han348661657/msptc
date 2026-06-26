# msptc — Molten-Salt Parabolic-Trough CSP Simulation Core

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-%E2%89%A53.10-blue.svg)
<!-- After the first Zenodo release, add the DOI badge here:
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
-->

A configuration-driven Python simulation core for **parabolic-trough concentrating solar power (CSP)** plants using **molten salt** as the heat-transfer fluid. It chains optics → receiver thermodynamics → collector loop → thermal storage / power block → variable-DNI dynamics, with altitude-dependent air properties, freeze protection, exergy, and techno-economic / market-value analysis.

## Features

**Optics & solar resource**

| Module | Responsibility |
|--------|----------------|
| `solar.py` | Solar geometry and DNI (vendored SPA + REST2 clear-sky) |
| `optics/analytical.py` | Analytical optics (EuroTrough IAM + end losses); `intercept_model` switches fixed / error-cone |
| `optics/intercept.py` | Error-cone intercept factor γ(aperture, error budget, receiver OD) |
| `optics/wind_deflection.py` | Wind–altitude coupled mirror slope error, σ ∝ ½·ρ(z)·v² |
| `optics/soltrace.py` | SolTrace adapter (deck generation + stub) |

**Thermal core**

| Module | Responsibility |
|--------|----------------|
| `atmosphere.py` | Altitude/temperature air properties ρ/ν/k/Pr + pressure (US Std Atm 1976) |
| `htf.py` | Heat-transfer-fluid properties (Solar Salt / Therminol VP-1) |
| `receiver.py` | HCE steady state (Forristall) + PTR70 empirical heat loss |
| `collector.py` | Collector-loop node-by-node series model |
| `dynamic.py` | Lumped-capacity dynamic ODE under variable DNI |
| `heatloss.py` | Heat-loss parameter sweep + hyperbolic fit |
| `control.py` | Freeze protection + `CollectorEnv` (MPC/RL interface) |

**System & analysis**

| Module | Responsibility |
|--------|----------------|
| `storage.py` / `powerblock.py` | Two-tank thermal storage / power block |
| `system.py` | Assembler (`build_collector`, `design_point`) wiring altitude/wind/receiver |
| `weather.py` / `io.py` | TMY3 / clear-sky weather; config loading + CSV I/O |
| `freeze.py` | Molten-salt freeze-protection parasitics |
| `exergy.py` | Component-level exergy analysis |
| `economics.py` | LCOE / techno-economic analysis |
| `market.py` | Time-of-use price + value factor + price-aware dispatch |
| `environment.py` | Carbon / water dimensions |

## Installation

```bash
pip install -r requirements.txt
```

Developed and tested on **CPython 3.13.9** (Python ≥ 3.10 recommended).

## Quick start

> Run scripts as **modules** from the repository root. The `msptc` package lives at the
> repo root, so calling `python scripts/...` directly raises `ModuleNotFoundError`.

```bash
python -m scripts.run_steady           # steady-state sweep
python -m scripts.run_dynamic          # variable-DNI (cloud) dynamics
python -m scripts.run_heatloss --plot  # heat-loss analysis + figure
python -m scripts.run_heatloss_split   # altitude heat-loss CHL/RHL decomposition
python -m pytest                       # run the test suite
```

## Configuration

Edit [`config/default.json`](config/default.json) (site / geometry / HTF / optical error budget /
wind load / simulation parameters). Defaults are backward-compatible:
`optics.intercept_model` defaults to `"fixed"` and `wind.c_w` defaults to `null`
(falls back to the legacy behaviour).

## Testing

```bash
python -m pytest
```

The full suite runs without any external data; weather-dependent tests use the small
synthetic fixture at `tests/fixtures/tmy3_sample.csv`.

## Data availability

This repository **does not redistribute licensed hourly weather data** (e.g. SolarGIS / TMY).
The scripts `run_system_annual` and `run_lcoe_honest` expect an authorized TMY3-format file at:

```text
data/CHN_QH_GEERMU_TMY3.csv
```

or supplied explicitly:

```bash
python -m scripts.run_system_annual --weather tmy --tmy-file /path/to/authorized_tmy.csv
```

The expected file is a TMY3-style CSV (2 metadata rows + 1 header row + hourly records) with at
least `Year,Month,Day,Hour,DNI,Tdry,Wspd`. All other scripts and the entire test suite run
without it.

## Repository layout

```text
msptc/        Simulation core (importable package)
  optics/     Optics submodule (analytical, intercept, wind, SolTrace)
  vendor/     Vendored third-party code (see License)
scripts/      Command-line entry points (run as: python -m scripts.<name>)
tests/        Test suite (pytest) + small synthetic fixtures
config/       Default configuration (default.json)
```

## Citation

If you use this software, please cite it via [`CITATION.cff`](CITATION.cff). A Zenodo DOI will be
added here once the first release is archived.

## License

Released under the [MIT License](LICENSE).

### Third-party code

- `msptc/vendor/sunposition.py` — © 2021 Samuel Bear Powell, MIT License (Solar Position Algorithm).
- `msptc/vendor/clear_sky_radiation_REST2.py` — implementation of the REST2 clear-sky irradiance
  model after C. A. Gueymard, *Solar Energy* **82** (2008) 272–285.
