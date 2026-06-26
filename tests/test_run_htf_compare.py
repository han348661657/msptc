import pandas as pd
from scripts.run_htf_compare import run_compare


def test_run_compare_produces_two_rows(tmp_path):
    path, df = run_compare(outdir=str(tmp_path))
    assert path.endswith(".csv")
    assert set(df["htf_type"]) == {"solar_salt", "therminol_vp1"}
    # 熔盐太阳能-电效率高于导热油
    salt = df[df["htf_type"] == "solar_salt"].iloc[0]
    oil = df[df["htf_type"] == "therminol_vp1"].iloc[0]
    assert salt["eta_pb_gross"] > oil["eta_pb_gross"]
