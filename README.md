# 🛡️ SkyGuard AI
AI-powered time-series platform that **detects, diagnoses and repairs** anomalies in weather data (USCRN hourly, IMD Tmax, IMD rainfall), built from the project master document.
LSTM-Autoencoder detector (PyTorch) → rule-based diagnosis → 4 repair methods → metrics → SQLite audit log → agents → MCP server → Google-Pay-style Streamlit app.

## 0. Run modes
- **App** (`make run`): pick Demo, a real dataset, or **Your own CSV** (date column + numeric columns, hourly or daily). Download the repaired CSV.
- **API** (`make api`, docs at /docs): `curl -H "X-API-Key: $KEY" -F file=@sample_data/example.csv "http://localhost:8000/v1/analyze?column=temperature_c"`. Set `SKYGUARD_API_KEY` to require a key.
- **Docker** (`make docker`): UI on :8501, API on :8000. **Tests**: `make test`. CI runs them on every push.
- Env vars: `SKYGUARD_MAX_ROWS` (default 300000), `SKYGUARD_EPOCHS` (default 25), `SKYGUARD_API_KEY`.

## 1. Setup on Mac (Apple Silicon M1)
```bash
cd SkyGuard-AI
bash scripts/setup_mac.sh          # Homebrew + Python 3.11 + venv + deps (PyTorch uses the M1 GPU via "mps")
source .venv/bin/activate
streamlit run app.py               # opens http://localhost:8501
```
Pick **Demo** and press **Run SkyGuard**: it works instantly with built-in synthetic data, no download needed.

## 2. Download the real datasets (raw files are never edited; `data/manifest.csv` records name, URL, size, sha256, date)
```bash
python scripts/download_data.py uscrn --list                                   # see station names
python scripts/download_data.py uscrn --station CO_Boulder_14_W --years 2021-2025   # ONE station, TXT -> data/raw/uscrn/<year>/
python scripts/download_data.py tmax --years 2020-2024                         # IMD 1° Tmax binary -> data/raw/imd_tmax/
python scripts/download_data.py rain --years 2019-2023                          # Zenodo ZIP (1901-2023, 123 yearly .nc) -> extracts only those years
# Already have the ZIP? Put it in data/raw/imd_rainfall/ first and the download is skipped.
```
If an IMD server is slow, download manually from the links below and drop files in the same folders. For rainfall, **read the printed time range** and set the 5-year window in `core.load_imd_rain` (default 2019-2023) before reporting dates.
The IMD loaders pick the grid cell nearest Mumbai (19.07N, 72.88E); change `lat/lon` in `core.py`.

## 3. Pipeline (also what the agents run)
`load → validate → clean → common schema → features (16-20) → train LSTM-AE (60/20/20 chronological, early stopping) → validation threshold → inject synthetic anomalies (test split only) → detect → classify → repair (linear / context / KNN / LSTM) → validate vs ground truth → SQLite + report`.
Outputs land in `outputs/` (`skyguard.db`, `report_<dataset>.md`) and `data/processed/<dataset>_common.csv.gz`.

## 4. MCP server
`python mcp_server/server.py` exposes the 12 tools (`load_weather_data` … `generate_report`) over stdio. Claude Desktop config is in the file header.

## 5. Push to GitHub
```bash
git init && git add . && git commit -m "SkyGuard AI: initial commit"
brew install gh && gh auth login                      # one-time login (browser)
gh repo create SkyGuard-AI --public --source=. --push
```
Without `gh`: create an empty repo on github.com, then `git remote add origin https://github.com/<you>/SkyGuard-AI.git && git branch -M main && git push -u origin main` (password = Personal Access Token). `.gitignore` already excludes raw data, so commit only code and the manifest.

## Sources
USCRN paper https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2022JD038057 · data https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/
IMD Tmax paper https://pmc.ncbi.nlm.nih.gov/articles/PMC10567792/ · data https://imdpune.gov.in/lrfindex.php/training/imsp/cmpg/Griddata/Max_1_Bin.html
IMD rainfall paper https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/851 · data https://zenodo.org/records/11195106
MCP papers https://arxiv.org/abs/2503.23278 · https://arxiv.org/abs/2505.02279

## Honest scope
Agents are a deterministic Supervisor calling registered tools (LLM planning is a drop-in next step via MCP). Not yet included: SHAP attribution, physical-inconsistency injection, KNN/ablation experiment grid, Postgres/Timescale (SQLite is used). Anomalies are synthetic; natural extremes can be valid.
