"""REST API. Run: uvicorn api:app --port 8000   Docs: http://localhost:8000/docs
Set SKYGUARD_API_KEY to require header  X-API-Key."""
import io, logging, os, tempfile
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from skyguard import core
from skyguard.pipeline import Pipeline
logging.basicConfig(level=logging.INFO); KEY, MAX = os.getenv("SKYGUARD_API_KEY"), 25 * 1024 * 1024
app = FastAPI(title="SkyGuard AI", version="1.0")

@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/v1/analyze")
def analyze(file: UploadFile = File(...), column: str | None = None, x_api_key: str | None = Header(None)):
    if KEY and x_api_key != KEY: raise HTTPException(401, "Invalid or missing X-API-Key")
    raw = file.file.read(MAX + 1)
    if len(raw) > MAX: raise HTTPException(413, "File larger than 25 MB")
    try: df, meta = core.load_csv(io.BytesIO(raw))
    except Exception as e: raise HTTPException(422, str(e))
    if column and column not in df.columns: raise HTTPException(422, f"column must be one of {list(df.columns)}")
    try: R = Pipeline("upload", data=(df, meta), target=column, out=tempfile.mkdtemp()).run_all()
    except Exception: logging.exception("pipeline failed"); raise HTTPException(500, "Analysis failed")
    d = R["diag"]; ev = d.nlargest(500, "peak_score").itertuples() if len(d) else []
    return {"column": R["target"], "flagged_points": int(R["flag"].sum()), "best_repair": R["best"], "repair_mae": float(R["rtab"].loc["all", R["best"]]),
            "events": [dict(start=str(r.start), end=str(r.end), type=r.type, steps=int(r.steps), score=round(r.peak_score, 3), evidence=r.evidence) for r in ev]}
