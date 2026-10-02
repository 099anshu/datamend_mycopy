import io, numpy as np, pandas as pd, pytest
from skyguard import core
from skyguard.pipeline import Pipeline

def make_csv(n=1500, step="h", datecol="timestamp"):
    t = pd.date_range("2024-01-01", periods=n, freq=step); d = np.arange(n)
    return pd.DataFrame({datecol: t, "temp": 15 + 6 * np.sin(2 * np.pi * d / 24) + np.random.default_rng(1).normal(0, .5, n)}).to_csv(index=False)

def test_load_csv_hourly():
    df, meta = core.load_csv(io.StringIO(make_csv())); assert meta["freq"] == "h" and "temp" in df and len(df) == 1500
def test_load_csv_bad_dates():
    with pytest.raises(ValueError): core.load_csv(io.StringIO("date,v\nnope,1\nbad,2\nworse,3\n"))
def test_load_csv_too_short():
    with pytest.raises(ValueError): core.load_csv(io.StringIO(make_csv(100)))
def test_load_csv_monthly_rejected():
    with pytest.raises(ValueError): core.load_csv(io.StringIO(make_csv(60, "MS")))
def test_features_are_backward_looking():
    df, _ = core.load_csv(io.StringIO(make_csv())); a = core.make_features(df, "h"); df2 = df.copy(); df2.iloc[-1] = 999
    pd.testing.assert_frame_equal(a.iloc[:-1], core.make_features(df2, "h").iloc[:-1])
def test_inject_then_linear_repair_helps():
    df, _ = core.load_csv(io.StringIO(make_csv(3000))); cor, ev = core.inject(df, "temp", 2000, core.LH); assert ev
    mask = cor["temp"].isna() | (cor["temp"] - df["temp"]).abs().gt(3); rep = core.repair(cor, "temp", mask, "linear")
    pos = np.concatenate([np.arange(s, e) for s, e, _ in ev]); assert core._mae(rep, df["temp"], pos) <= core._mae(cor["temp"].fillna(0), df["temp"], pos)
def test_pipeline_demo_end_to_end(tmp_path):
    R = Pipeline("demo", out=str(tmp_path)).run_all(); assert R["flag"].sum() > 0 and R["best"] in ("linear", "context", "knn", "lstm") and (tmp_path / "skyguard.db").exists()
def test_pipeline_upload_mode(tmp_path):
    R = Pipeline("upload", data=core.load_csv(io.StringIO(make_csv(2000))), target="temp", out=str(tmp_path)).run_all(); assert not R["labelled"] and "best" in R
