"""Agents + tool registry. Each agent owns tools; the Supervisor runs them in order and logs every call.
The same tool names are exposed over MCP in mcp_server/server.py."""
import os, time, logging, sqlite3, numpy as np, pandas as pd
from . import core

TOOLS = ["load_weather_data", "validate_data", "clean_data", "engineer_features", "train_model", "inject_anomalies",
         "detect_anomalies", "classify_anomaly", "repair_anomaly", "validate_repair", "save_results", "generate_report"]
AGENTS = {"Data Agent": ["load_weather_data", "validate_data", "clean_data"], "Feature Agent": ["engineer_features"],
          "Detection Agent": ["train_model", "inject_anomalies", "detect_anomalies"], "Diagnosis Agent": ["classify_anomaly"],
          "Repair Agent": ["repair_anomaly", "validate_repair"], "Report Agent": ["save_results", "generate_report"]}
log = logging.getLogger('skyguard')
METHODS = ["linear", "context", "knn", "lstm"]

class Pipeline:
    def __init__(self, source="demo", progress=None, out="outputs", data=None, target=None):
        self.up, self.labelled = data, source != "upload"
        self.c = core.CFG[source] if self.labelled else core.upload_cfg(data[1]["freq"], target or data[0].columns[0])
        self.src, self.progress, self.out = source, progress, out
        self.logs, self.run_id, self.r = [], time.strftime("run_%Y%m%d_%H%M%S"), {}; self.t = self.c["target"]; os.makedirs(out, exist_ok=True)

    def call(self, agent, tool):                       # the "MCP-style" invoke step
        t0 = time.time(); st, det = "ok", ""
        try: res = getattr(self, tool)()
        except Exception as e: st, det, res = "error", str(e), None
        self.logs.append(dict(run_id=self.run_id, agent=agent, tool=tool, status=st, timestamp=time.strftime("%H:%M:%S"), seconds=round(time.time() - t0, 2), detail=det or str(res)[:160]))
        log.info("%s | %s | %s | %s", self.run_id, agent, tool, st)
        if self.progress: self.progress(agent, tool, st)
        if st == "error": raise RuntimeError(f"{tool}: {det}")
        return res

    def run_all(self):                                 # Supervisor
        for agent, tools in AGENTS.items():
            for tool in tools: self.call(agent, tool)
        return self.results()

    # --- Data Agent
    def load_weather_data(self):
        self.raw, self.meta = self.up if self.up else core.LOADERS[self.src](); d = self.raw
        return dict(rows=len(d), start=str(d.index.min()), end=str(d.index.max()), variables=list(d.columns))
    def validate_data(self): self.quality = core.quality(self.raw, self.c["freq"]); return self.quality
    def clean_data(self):
        self.clean = core.clean(self.raw, self.c["freq"]); os.makedirs("data/processed", exist_ok=True)
        self.long = core.to_long(self.clean, self.src, self.meta); self.labelled and self.long.to_csv(f"data/processed/{self.src}_common.csv.gz", index=False)
        return dict(rows=len(self.clean), common_schema_rows=len(self.long))
    # --- Feature Agent
    def engineer_features(self): self.feat = core.make_features(self.clean, self.c["freq"]); return dict(n_features=self.feat.shape[1], names=list(self.feat.columns))
    # --- Detection Agent
    def train_model(self):
        self.art = core.train_model(self.feat, self.c["window"], epochs=core.EPOCHS); a = self.art; sc = core.score(a, self.feat)
        self.thr = float(np.percentile(sc.iloc[a["i1"]:a["i2"]], 99))      # validation-based threshold (99th percentile)
        return dict(device=a["dev"], epochs=len(a["hist"]), val_loss=round(a["val_loss"], 5), threshold=round(self.thr, 4),
                    train_end=str(self.feat.index[a["i1"]]), val_end=str(self.feat.index[a["i2"]]))
    def inject_anomalies(self):
        self.truth = np.zeros(len(self.clean), bool)
        if not self.labelled: self.cor, self.ev = self.clean.copy(), []; return dict(events=0, note="your data: nothing injected")
        self.cor, self.ev = core.inject(self.clean, self.t, self.art["i2"], self.c["lens"])
        for s, e, _ in self.ev: self.truth[s:e] = True
        return dict(events=len(self.ev))
    def detect_anomalies(self):
        a = self.art; self.sc = core.score(a, core.make_features(self.cor, self.c["freq"])); miss = self.cor[self.t].isna().values
        self.flag = ((self.sc.values > self.thr) | miss)
        if self.labelled: self.flag[:a["i2"]] = False
        self.metrics = core.detect_metrics(self.truth, self.flag, self.sc.where(~miss, self.sc.max()).values, self.ev, a["i2"]) if self.labelled else {}
        return {k: round(float(v), 3) for k, v in self.metrics.items()}
    # --- Diagnosis Agent
    def classify_anomaly(self):
        self.diag = core.diagnose(self.cor, self.t, self.flag, self.sc); return dict(detected=len(self.diag), types=self.diag.type.value_counts().to_dict() if len(self.diag) else {})
    # --- Repair Agent
    def repair_anomaly(self):
        m = pd.Series(self.flag, index=self.cor.index)
        self.reps = {k: core.repair(self.cor, self.t, m, k, self.art, self.c["freq"], self.c["period"]) for k in METHODS}; return dict(methods=METHODS, points=int(m.sum()))
    def validate_repair(self):
        if self.labelled: self.rtab, self.rmse = core.repair_eval(self.clean[self.t], self.cor[self.t], self.reps, self.ev)
        else:  # no ground truth: hide random healthy points, repair them, compare (self-supervised check)
            ok = np.flatnonzero(~self.flag & self.clean[self.t].notna().values); pick = np.random.default_rng(core.SEED).choice(ok, min(300, len(ok)), replace=False)
            m = self.flag.copy(); m[pick] = True; m = pd.Series(m, index=self.cor.index); tr = self.clean[self.t]
            reps = {k: core.repair(self.cor, self.t, m, k, self.art, self.c['freq'], self.c['period']) for k in METHODS}
            self.rtab = pd.DataFrame([{'type': 'all', 'before': np.nan, **{k: core._mae(v, tr, pick) for k, v in reps.items()}}]).set_index('type')
            self.rmse = {k: float(np.sqrt(np.nanmean((v.iloc[pick].values - tr.iloc[pick].values) ** 2))) for k, v in reps.items()}
        self.best = self.rtab.loc["all", METHODS].astype(float).idxmin(); return dict(best_method=self.best, rmse=self.rmse)
    # --- Report Agent
    def save_results(self):
        con = sqlite3.connect(f"{self.out}/skyguard.db"); L = self.long.copy(); L["timestamp"] = L.timestamp.astype(str)
        L.to_sql("observations", con, if_exists="replace", index=False)
        d = self.diag.copy() if len(self.diag) else pd.DataFrame(columns=["start", "end", "type", "peak_score"])
        d.assign(run_id=self.run_id, event_id=range(len(d)), status="repaired", start=d.start.astype(str), end=d.end.astype(str)).drop(columns=["i0", "i1"], errors="ignore").to_sql("anomaly_events", con, if_exists="replace", index=False)
        fl = np.flatnonzero(self.flag); pd.DataFrame(dict(timestamp=self.cor.index[fl].astype(str), original=self.cor[self.t].values[fl], repaired=self.reps[self.best].values[fl],
            clean_truth=self.clean[self.t].values[fl], method=self.best)).to_sql("repaired_data", con, if_exists="replace", index=False)
        pd.DataFrame([dict(location=self.meta["location_id"], variable=c, missing_rate=float(self.raw[c].isna().mean()), anomaly_count=len(self.diag), status="ok") for c in self.raw]).to_sql("sensor_health", con, if_exists="replace", index=False)
        pd.DataFrame(self.logs).to_sql("agent_logs", con, if_exists="append", index=False)
        pd.DataFrame([dict(experiment_id=self.run_id, dataset=self.src, model_version="lstm-ae-v1", metrics=str({k: round(float(v), 3) for k, v in self.metrics.items()}))]).to_sql("experiments", con, if_exists="append", index=False)
        con.close(); return dict(db=f"{self.out}/skyguard.db")
    def generate_report(self):
        m, rt = self.metrics, self.rtab.round(3)
        self.report = (f"# SkyGuard AI report: {self.c['name']}\n\nRun `{self.run_id}`. Period {self.raw.index.min()} to {self.raw.index.max()}, {len(self.raw)} rows. Threshold {self.thr:.4f} (99th pct of validation scores).\n\n"
            f"## Detection (test split)\n" + "".join(f"- {k}: {float(v):.3f}\n" for k, v in m.items()) + f"\n## Repair MAE by anomaly type\n\n{rt.to_markdown()}\n\nBest method: **{self.best}**.\n\n" +
            ("Note: anomalies are synthetic and controlled; detected events may include valid natural extremes.\n" if self.labelled else "Note: flagged points are candidates. Verify against the sensor or source before accepting repairs.\n"))
        open(f"{self.out}/report_{self.src}.md", "w").write(self.report); return dict(report=f"{self.out}/report_{self.src}.md")

    def results(self):
        return dict(name=self.c["name"], target=self.t, unit=core.UNITS.get(self.t, ""), labelled=self.labelled, clean=self.clean[self.t], cor=self.cor[self.t], reps=self.reps, flag=self.flag, sc=self.sc, thr=self.thr,
                    i2=self.art["i2"], diag=self.diag, ev=self.ev, metrics=self.metrics, rtab=self.rtab, rmse=self.rmse, best=self.best, logs=pd.DataFrame(self.logs), report=self.report,
                    quality=self.quality, hist=self.art["hist"], meta=self.meta)
