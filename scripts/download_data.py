"""Download datasets + write data/manifest.csv.  Examples:
  python scripts/download_data.py uscrn --station CO_Boulder_14_W --years 2021-2025
  python scripts/download_data.py uscrn --list           # list station names
  python scripts/download_data.py tmax --years 2020-2024
  python scripts/download_data.py rain                    # Zenodo ZIP, extract + inspect"""
import argparse, csv, datetime as dt, hashlib, os, re, zipfile, requests
BASE = "https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/"
ZEN = "https://zenodo.org/records/11195106/files/Rainfall_IMD_1901_2023.zip?download=1"
def fetch(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest): print("have", dest); return
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest + ".part", "wb") as f:
            for ch in r.iter_content(1 << 20): f.write(ch)
    os.replace(dest + ".part", dest); print("saved", dest)
def log(folder, url):
    new = not os.path.exists("data/manifest.csv")
    with open("data/manifest.csv", "a", newline="") as f:
        w = csv.writer(f); new and w.writerow(["file", "url", "bytes", "sha256", "downloaded"])
        for root, _, fs in os.walk(folder):
            for n in fs:
                p = os.path.join(root, n)
                if n != ".gitkeep": w.writerow([p, url, os.path.getsize(p), hashlib.sha256(open(p, "rb").read()).hexdigest(), dt.date.today()])
def main():
    a = argparse.ArgumentParser(); a.add_argument("what", choices=["uscrn", "tmax", "rain"]); a.add_argument("--station", default="CO_Boulder_14_W")
    a.add_argument("--years", default=None); a.add_argument("--list", action="store_true"); a = a.parse_args()
    y0, y1 = map(int, (a.years or {"uscrn": "2021-2025", "tmax": "2020-2024", "rain": "2019-2023"}[a.what]).split("-"))
    if a.what == "uscrn":
        if a.list:
            print(sorted(set(re.findall(r'CRNH0203-\d{4}-([^"]+)\.txt', requests.get(f"{BASE}{y1}/").text)))); return
        for y in range(y0, y1 + 1):
            m = re.findall(r'href="(CRNH0203-%d-[^"]*%s[^"]*\.txt)"' % (y, re.escape(a.station)), requests.get(f"{BASE}{y}/").text)
            if not m: print(f"no file for {a.station} in {y}; try --list"); continue
            fetch(f"{BASE}{y}/{m[0]}", f"data/raw/uscrn/{y}/{m[0]}")
        log("data/raw/uscrn", BASE)
    elif a.what == "tmax":
        import imdlib as imd
        imd.get_data("tmax", y0, y1, fn_format="yearwise", file_dir="data/raw/imd_tmax")
        log("data/raw/imd_tmax", "https://imdpune.gov.in/lrfindex.php/training/imsp/cmpg/Griddata/Max_1_Bin.html")
    else:
        z = "data/raw/imd_rainfall/Rainfall_IMD_1901_2023.zip"; fetch(ZEN, z)      # skipped if you already have the ZIP there
        with zipfile.ZipFile(z) as f:                                              # extract ONLY the chosen years (full ZIP = ~6 GB)
            for n in f.namelist():
                m = re.search(r"(\d{4})", n)
                if m and y0 <= int(m.group(1)) <= y1: f.extract(n, "data/raw/imd_rainfall"); print("extracted", n)
        import glob, xarray as xr
        for p in sorted(glob.glob("data/raw/imd_rainfall/**/*.nc", recursive=True)):
            d = xr.open_dataset(p); print(os.path.basename(p), dict(d.sizes), d[list(d.coords)[0]].values[[0, -1]])
        log("data/raw/imd_rainfall", ZEN)
main()
