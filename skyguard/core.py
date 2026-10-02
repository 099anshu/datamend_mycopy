"""SkyGuard AI core: loaders, cleaning, features, LSTM-AE, injection, diagnosis, repair, metrics."""
import os, glob, warnings
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
import numpy as np, pandas as pd, torch, torch.nn as nn
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
warnings.filterwarnings("ignore")
SEED = 42
UNITS = {"temp": "°C", "rh": "%", "solar": "W/m²", "precip": "mm", "tmax": "°C", "rain": "mm"}
RANGES = {"temp": (-60, 60), "rh": (0, 100), "solar": (0, 1500), "precip": (0, 500), "tmax": (-10, 60), "rain": (0, 1500)}
LH = dict(spike=1, dropout=6, flatline=12, drift=24, noise=12)
LD = dict(spike=1, dropout=3, flatline=5, drift=10, noise=5)
CFG = {
 "demo": dict(name="Demo (synthetic hourly)", freq="h", window=48, target="temp", period=24, lens=LH),
 "uscrn": dict(name="USCRN hourly, USA", freq="h", window=48, target="temp", period=24, lens=LH),
 "imd_tmax": dict(name="IMD max temperature, India", freq="D", window=14, target="tmax", period=1, lens=LD),
 "imd_rain": dict(name="IMD rainfall, India", freq="D", window=14, target="rain", period=1, lens=LD)}
USCRN_COLS = ("WBANNO UTC_DATE UTC_TIME LST_DATE LST_TIME CRX_VN LONGITUDE LATITUDE T_CALC T_HR_AVG T_MAX T_MIN P_CALC "
 "SOLARAD SOLARAD_FLAG SOLARAD_MAX SOLARAD_MAX_FLAG SOLARAD_MIN SOLARAD_MIN_FLAG SUR_TEMP_TYPE SUR_TEMP SUR_TEMP_FLAG "
 "SUR_TEMP_MAX SUR_TEMP_MAX_FLAG SUR_TEMP_MIN SUR_TEMP_MIN_FLAG RH_HR_AVG RH_HR_AVG_FLAG SOIL_MOISTURE_5 SOIL_MOISTURE_10 "
 "SOIL_MOISTURE_20 SOIL_MOISTURE_50 SOIL_MOISTURE_100 SOIL_TEMP_5 SOIL_TEMP_10 SOIL_TEMP_20 SOIL_TEMP_50 SOIL_TEMP_100").split()

# ---------- loaders (dataset-specific parsing -> wide frame + meta) ----------
def load_demo(n=24 * 500):
    r = np.random.default_rng(SEED); d = np.arange(n); h = d % 24
    t = 15 + 10 * np.sin(2 * np.pi * (d / 24 / 365 - .25)) + 6 * np.sin(2 * np.pi * (h - 9) / 24) + r.normal(0, .7, n)
    rh = np.clip(70 - 2.2 * (t - 15) + r.normal(0, 3, n), 5, 100)
    sol = np.clip(800 * np.sin(np.pi * (h - 6) / 12), 0, None) * (.8 + .2 * np.sin(2 * np.pi * d / 24 / 365)) + r.normal(0, 15, n)
    df = pd.DataFrame({"temp": t, "rh": rh, "solar": np.clip(sol, 0, None)}, index=pd.date_range("2023-01-01", periods=n, freq="h"))
    return df, dict(location_id="demo_station", lat=19.07, lon=72.88, files="synthetic")

def load_uscrn(folder="data/raw/uscrn"):
    files = sorted(glob.glob(f"{folder}/**/*.txt", recursive=True))
    if not files: raise FileNotFoundError("No USCRN .txt files in data/raw/uscrn. Run: python scripts/download_data.py uscrn")
    d = pd.concat([pd.read_csv(f, sep=r"\s+", header=None, names=USCRN_COLS) for f in files])
    ts = pd.to_datetime(d.UTC_DATE.astype(str) + d.UTC_TIME.astype(str).str.zfill(4), format="%Y%m%d%H%M")
    o = pd.DataFrame({"temp": d.T_HR_AVG.values, "rh": d.RH_HR_AVG.values, "solar": d.SOLARAD.values, "precip": d.P_CALC.values}, index=ts)
    o = o.mask(o <= -9998)                                   # NOAA missing codes
    o.loc[(d.RH_HR_AVG_FLAG != 0).values, "rh"] = np.nan    # honour source quality flags
    o.loc[(d.SOLARAD_FLAG != 0).values, "solar"] = np.nan
    return o, dict(location_id=f"WBAN_{d.WBANNO.iloc[0]}", lat=float(d.LATITUDE.iloc[0]), lon=float(d.LONGITUDE.iloc[0]), files=";".join(os.path.basename(f) for f in files))

def _nc_point(files, lat, lon):
    import xarray as xr
    parts, cell = [], None
    for f in files:                                   # IMD rainfall ships one NetCDF per year
        ds = xr.open_dataset(f); v = next(k for k in ds.data_vars if ds[k].ndim == 3)
        la = next(c for c in ds.coords if c.lower().startswith("lat")); lo = next(c for c in ds.coords if c.lower().startswith("lon"))
        if cell is None:                              # nearest cell WITH data (grid is NaN over sea / outside India)
            ok = ds[v].notnull().any([d for d in ds[v].dims if d not in (la, lo)]).values
            LA, LO = np.meshgrid(ds[la].values, ds[lo].values, indexing="ij")
            i, j = np.unravel_index(np.where(ok, (LA - lat) ** 2 + (LO - lon) ** 2, np.inf).argmin(), ok.shape); cell = (ds[la].values[i], ds[lo].values[j])
        parts.append(ds[v].sel({la: cell[0], lo: cell[1]}).to_series())
    return pd.concat(parts)

def _grid(var, folder, y0, y1, lat, lon):
    import re
    nc = []
    for f in sorted(glob.glob(f"{folder}/**/*.nc", recursive=True)):
        m = re.search(r"(\d{4})", os.path.basename(f))
        if not m or y0 <= int(m.group(1)) <= y1: nc.append(f)
    if nc: s = _nc_point(nc, lat, lon)
    else:
        import imdlib as imd
        s = imd.open_data(var, y0, y1, "yearwise", folder).get_xarray()[var].sel(lat=lat, lon=lon, method="nearest").to_series()
    s.index = pd.DatetimeIndex(s.index.get_level_values(-1) if s.index.nlevels > 1 else s.index)
    return s.sort_index().loc[str(y0):str(y1)]

def load_imd_tmax(folder="data/raw/imd_tmax", y0=2020, y1=2024, lat=19.07, lon=72.88):
    s = _grid("tmax", folder, y0, y1, lat, lon).where(lambda x: x < 60)
    return pd.DataFrame({"tmax": s}), dict(location_id=f"grid_{lat}_{lon}", lat=lat, lon=lon, files=f"IMD tmax {y0}-{y1}")

def load_imd_rain(folder="data/raw/imd_rainfall", y0=2019, y1=2023, lat=19.07, lon=72.88):
    s = _grid("rain", folder, y0, y1, lat, lon).where(lambda x: x >= 0)
    return pd.DataFrame({"rain": s}), dict(location_id=f"grid_{lat}_{lon}", lat=lat, lon=lon, files=f"IMD rainfall {y0}-{y1}")

LOADERS = {"demo": load_demo, "uscrn": load_uscrn, "imd_tmax": load_imd_tmax, "imd_rain": load_imd_rain}

# ---------- quality, cleaning, common schema ----------
def quality(df, freq):
    full = pd.date_range(df.index.min(), df.index.max(), freq=freq)
    out = {"expected_steps": len(full), "missing_steps": len(full) - len(df), "duplicate_timestamps": int(df.index.duplicated().sum())}
    for c in df:
        run = (df[c].diff() == 0).astype(int)
        out[c] = {"missing_pct": round(100 * df[c].isna().mean(), 2), "max_flat_run": int(run.groupby((run == 0).cumsum()).sum().max())}
    return out

def clean(df, freq):
    df = df[~df.index.duplicated()].sort_index().asfreq(freq)
    for c in df: lo, hi = RANGES.get(c, (-np.inf, np.inf)); df[c] = df[c].where(df[c].between(lo, hi))
    return df

def to_long(df, dataset, meta):
    l = df.reset_index(names="timestamp").melt("timestamp", var_name="variable", value_name="value")
    l["unit"] = l.variable.map(UNITS).fillna('')
    for k, v in dict(dataset=dataset, location_id=meta["location_id"], latitude=meta["lat"], longitude=meta["lon"], source_file=meta["files"][:200]).items(): l[k] = v
    l["quality_flag"] = l.value.isna().astype(int)
    return l[["timestamp", "dataset", "location_id", "latitude", "longitude", "variable", "value", "unit", "quality_flag", "source_file"]]

# ---------- feature engineering (shared across all datasets; backward-looking only) ----------
def make_features(df, freq):
    b = df.interpolate(limit=24, limit_direction="both").ffill().bfill(); f = pd.DataFrame(index=df.index); w = 24 if freq == "h" else 7
    for c in df:
        f[c] = b[c]; f[c + "_diff"] = b[c].diff().fillna(0)
        f[c + "_rmean"] = b[c].rolling(w, min_periods=1).mean(); f[c + "_rstd"] = b[c].rolling(w, min_periods=1).std().fillna(0)
    p = df.index.hour / 24 if freq == "h" else df.index.dayofyear / 365.25; m = (df.index.month - 1) / 12
    f["t_sin"], f["t_cos"], f["m_sin"], f["m_cos"] = np.sin(2 * np.pi * p), np.cos(2 * np.pi * p), np.sin(2 * np.pi * m), np.cos(2 * np.pi * m)
    return f

# ---------- LSTM autoencoder ----------
def device(): return "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"

class LSTMAE(nn.Module):
    def __init__(s, d, h=32, z=16):
        super().__init__(); s.enc = nn.LSTM(d, h, batch_first=True); s.to_z = nn.Linear(h, z)
        s.from_z = nn.Linear(z, h); s.dec = nn.LSTM(h, h, batch_first=True); s.out = nn.Linear(h, d)
    def forward(s, x):
        _, (hn, _) = s.enc(x); z = s.to_z(hn[-1]); h = s.from_z(z).unsqueeze(1).repeat(1, x.shape[1], 1)
        return s.out(s.dec(h)[0])

def windows(X, w, stride=1):
    idx = np.arange(0, len(X) - w + 1, stride); return np.stack([X[i:i + w] for i in idx]), idx

def train_model(feat, window, epochs=25, patience=3):
    torch.manual_seed(SEED); np.random.seed(SEED); n = len(feat); i1, i2 = int(n * .6), int(n * .8)   # chronological 60/20/20
    mu, sd = feat.iloc[:i1].mean(), feat.iloc[:i1].std().replace(0, 1)                                # train-only scaling
    X = ((feat - mu) / sd).values.astype("float32"); dev = device()
    tr, va = windows(X[:i1], window, 2)[0], windows(X[i1:i2], window, 2)[0]
    m = LSTMAE(X.shape[1]).to(dev); opt = torch.optim.Adam(m.parameters(), 1e-3); best, bad, state, hist = 1e9, 0, None, []
    def loss_on(a):
        with torch.no_grad(): return float(np.mean([nn.functional.mse_loss(m(torch.from_numpy(a[b:b + 256]).to(dev)), torch.from_numpy(a[b:b + 256]).to(dev)).item() for b in range(0, len(a), 256)]))
    for ep in range(epochs):
        m.train(); p = np.random.permutation(len(tr))
        for b in range(0, len(tr), 128):
            xb = torch.from_numpy(tr[p[b:b + 128]]).to(dev); l = nn.functional.mse_loss(m(xb), xb); opt.zero_grad(); l.backward(); opt.step()
        m.eval(); v = loss_on(va); hist.append(v)
        if v < best - 1e-5: best, bad, state = v, 0, {k: x.detach().clone() for k, x in m.state_dict().items()}
        else:
            bad += 1
            if bad >= patience: break
    m.load_state_dict(state); m.eval()
    return dict(model=m, mu=mu, sd=sd, window=window, i1=i1, i2=i2, dev=dev, hist=hist, val_loss=best)

@torch.no_grad()
def reconstruct(art, feat):
    X = ((feat - art["mu"]) / art["sd"]).values.astype("float32"); w = art["window"]; W, idx = windows(X, w)
    rec = np.zeros_like(X); cnt = np.zeros(len(X))
    for b in range(0, len(W), 512):
        out = art["model"](torch.from_numpy(W[b:b + 512]).to(art["dev"])).cpu().numpy()
        for k, o in enumerate(out): s = idx[b + k]; rec[s:s + w] += o; cnt[s:s + w] += 1
    return X, rec / np.maximum(cnt, 1)[:, None]

def score(art, feat):
    X, rec = reconstruct(art, feat); return pd.Series(((X - rec) ** 2).mean(1), index=feat.index)   # per-step MSE

def recon_values(art, feat, col):
    _, rec = reconstruct(art, feat); j = list(feat.columns).index(col); return pd.Series(rec[:, j] * art["sd"][col] + art["mu"][col], index=feat.index)

# ---------- synthetic anomaly injection ----------
def inject(df, col, i0, lens, seed=SEED):
    r = np.random.default_rng(seed); a = df[col].to_numpy(copy=True); sd = np.nanstd(a); gap = 3 * max(lens.values()) + 8
    slots = np.arange(i0 + 20, len(a) - max(lens.values()) - 5, gap); r.shuffle(slots); kinds = list(lens) * (len(slots) // len(lens) + 1); ev = []
    for s, k in zip(slots, kinds):
        e = s + lens[k]
        if k == "spike": a[s] += r.choice([-1, 1]) * 6 * sd
        elif k == "dropout": a[s:e] = np.nan
        elif k == "flatline": a[s:e] = a[s]
        elif k == "drift": a[s:e] += np.linspace(0, 3 * sd, lens[k])
        else: a[s:e] += r.normal(0, 1.2 * sd, lens[k])
        ev.append((int(s), int(e), k))
    out = df.copy(); out[col] = a; return out, sorted(ev)

# ---------- diagnosis / classification ----------
def diagnose(df, col, flag, score_s, ctx=168):
    groups = []
    for i in np.flatnonzero(flag):
        if groups and i - groups[-1][1] <= 2: groups[-1][1] = i
        else: groups.append([i, i])
    rows = []
    for s, e in groups:
        seg = df[col].iloc[s:e + 1]; past = df[col].iloc[max(0, s - ctx):s]; n = e - s + 1
        z = (seg - past.mean()) / (past.std() + 1e-9)
        oth = [c for c in df.columns if c != col and abs((df[c].iloc[s:e + 1].mean() - df[c].iloc[max(0, s - ctx):s].mean()) / (df[c].iloc[max(0, s - ctx):s].std() + 1e-9)) > 3]
        if seg.isna().any(): t = "dropout"
        elif n >= 4 and seg.nunique() == 1 and seg.iloc[0] != 0: t = "flatline"
        elif n <= 3: t = "spike"
        else: t = "drift" if n >= 8 and abs(np.corrcoef(np.arange(n), seg.fillna(seg.mean()))[0, 1]) > .85 else "noise"
        if oth and t in ("spike", "noise"): t = "natural_extreme"
        ev = f"peak score {score_s.iloc[s:e + 1].max():.2f}; max |z| {np.nanmax(z.abs()) if z.notna().any() else 0:.1f}; {n} step(s); max step change {seg.diff().abs().max():.1f}" + (f"; also unusual: {', '.join(oth)}" if oth else "")
        rows.append(dict(start=df.index[s], end=df.index[e], i0=s, i1=e, steps=n, type=t, peak_score=float(score_s.iloc[s:e + 1].max()), evidence=ev))
    return pd.DataFrame(rows)

# ---------- repair ----------
def repair(df, col, mask, method, art=None, freq="h", period=24):
    s = df[col].copy(); s[mask] = np.nan; lin = s.interpolate(limit_direction="both")
    if method == "linear": return lin
    out = s.copy()
    if method == "context":
        est = pd.concat([lin.shift(k * period) for k in (-3, -2, -1, 1, 2, 3)], axis=1).median(axis=1); out[mask] = est[mask]
    elif method == "knn":
        M = pd.concat([lin.shift(k) for k in (3, 2, 1, -1, -2, -3)], axis=1).values; ok = ~mask.values & ~np.isnan(M).any(1) & ~np.isnan(s.values)
        t = mask.values & ~np.isnan(M).any(1)
        if t.any(): out[t] = KNeighborsRegressor(5).fit(M[ok], s.values[ok]).predict(M[t])
    elif method == "lstm":
        d2 = df.copy(); d2[col] = lin; out[mask] = recon_values(art, make_features(d2, freq), col)[mask]
    return out.fillna(lin)

def _mae(a, b, pos):
    d = np.abs(a.iloc[pos].values - b.iloc[pos].values); return float(np.nanmean(d)) if np.isfinite(d).any() else np.nan

def repair_eval(clean_s, cor_s, reps, ev):
    rows = []
    for k in sorted({e[2] for e in ev}) + ["all"]:
        pos = np.concatenate([np.arange(s, e) for s, e, kk in ev if k in (kk, "all")])
        rows.append({"type": k, "before": _mae(cor_s, clean_s, pos), **{m: _mae(r, clean_s, pos) for m, r in reps.items()}})
    pos = np.concatenate([np.arange(s, e) for s, e, _ in ev])
    rmse = {m: float(np.sqrt(np.nanmean((r.iloc[pos].values - clean_s.iloc[pos].values) ** 2))) for m, r in reps.items()}
    return pd.DataFrame(rows).set_index("type"), rmse

def detect_metrics(truth, flag, sc, ev, i2):
    y, p = truth[i2:], flag[i2:]; pr, rc, f1, _ = precision_recall_fscore_support(y, p, average="binary", zero_division=0)
    return dict(precision=pr, recall=rc, f1=f1, roc_auc=roc_auc_score(y, sc[i2:]) if y.any() and (~y).any() else np.nan,
                event_recall=float(np.mean([flag[max(s - 1, 0):e + 1].any() for s, e, _ in ev])))

# ---------- bring-your-own-data ----------
MAX_ROWS = int(os.getenv("SKYGUARD_MAX_ROWS", 300000)); EPOCHS = int(os.getenv("SKYGUARD_EPOCHS", 25))

def load_csv(src):
    """Parse a user CSV (date column + numeric columns). Returns (frame, meta). Raises ValueError with a user-friendly message."""
    df = pd.read_csv(src)
    if df.empty: raise ValueError("The file has no rows.")
    tc = next((c for c in df.columns if str(c).strip().lower() in ("timestamp", "time", "datetime", "date")), df.columns[0])
    ts = pd.to_datetime(df[tc], errors="coerce", utc=True).dt.tz_localize(None)
    if ts.isna().mean() > .05: raise ValueError(f"Could not read dates in column '{tc}'. Use a format like 2024-06-15 13:00.")
    num = df.drop(columns=[tc]).apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
    if num.empty: raise ValueError("No numeric columns found besides the date column.")
    num = num.iloc[:, :6]; num.columns = [str(c).strip() for c in num.columns]; num.index = pd.DatetimeIndex(ts.values)
    num = num[num.index.notna()]; num = num[~num.index.duplicated()].sort_index()
    step = num.index.to_series().diff().median()
    if step <= pd.Timedelta("90min"): freq, num = "h", num.resample("h").mean()
    elif step <= pd.Timedelta("36h"): freq, num = "D", num.resample("D").mean()
    else: raise ValueError("Data must be hourly, daily, or finer. Weekly/monthly data is not supported yet.")
    if len(num) < (800 if freq == "h" else 400): raise ValueError(f"Too short: need at least {800 if freq == 'h' else 400} {'hours' if freq == 'h' else 'days'} to learn normal behaviour (got {len(num)}).")
    if len(num) > MAX_ROWS: raise ValueError(f"Too long: limit is {MAX_ROWS:,} rows.")
    return num, dict(location_id="upload", lat=np.nan, lon=np.nan, files="upload", freq=freq)

def upload_cfg(freq, target):
    h = freq == "h"; return dict(name="Your data", freq=freq, window=48 if h else 14, target=target, period=24 if h else 1, lens=LH if h else LD)
