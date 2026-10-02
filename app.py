import os, sys, tempfile, logging, numpy as np, pandas as pd, plotly.graph_objects as go, streamlit as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skyguard import core
from skyguard.core import CFG
from skyguard.pipeline import Pipeline
logging.basicConfig(level=logging.INFO)
st.set_page_config("SkyGuard AI", "🛡️", layout="centered")
BLUE, GREEN, RED, AMB, PUR, CY = "#1A73E8", "#1E8E3E", "#D93025", "#F9AB00", "#A142F4", "#12B5CB"
LIGHT = dict(bg="#F6F8FC", card="#FFFFFF", ink="#202124", sub="#5F6368", line="#E8EAED", chip="#F1F3F4", accent="#1A73E8", shadow="rgba(60,64,67,.15)")
DARK = dict(bg="#101318", card="#1C2027", ink="#E8EAED", sub="#9AA0A6", line="#2E333B", chip="#2A2F38", accent="#8AB4F8", shadow="rgba(0,0,0,.5)")
T = DARK if st.session_state.get("dark") else LIGHT
CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
html,body,.stApp,[class*="css"]{font-family:'Google Sans Text','Roboto',sans-serif}
.stApp,[data-testid="stAppViewContainer"]{background:%bg%} #MainMenu,header,footer{visibility:hidden}
.block-container{max-width:780px;padding:1rem 1rem 4rem}
.stApp h3,.stApp label,.stApp [data-testid="stCaptionContainer"],.stApp [data-testid="stMarkdownContainer"] p{color:%ink%}
.stApp [data-testid="stCaptionContainer"]{color:%sub%} h3{font-weight:500!important}
.card{background:%card%;color:%ink%;border-radius:28px;padding:18px 22px;margin:10px 0;box-shadow:0 1px 3px %shadow%}
.hero{background:linear-gradient(135deg,#1A73E8,#4285F4 60%,#8AB4F8);border-radius:32px;padding:24px;margin:6px 0 12px}
.hero *{color:#fff!important} .hero h1{margin:0;font-size:30px;font-weight:700} .hero p{margin:6px 0 0;opacity:.92}
.chip{display:inline-block;padding:5px 12px;border-radius:99px;background:rgba(255,255,255,.22);font-size:13px;margin:12px 6px 0 0}
.kpi{background:%card%;border-radius:24px;padding:16px 18px;box-shadow:0 1px 3px %shadow%}.kpi b{font-size:26px;color:%ink%}.kpi span{display:block;color:%sub%;font-size:13px}
.row{display:flex;align-items:center;gap:14px;padding:12px 4px;border-bottom:1px solid %line%}.row:last-child{border:0}
.dot{width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;flex:none}
.mid{flex:1;min-width:0}.mid b{font-size:15px;color:%ink%}.mid small{display:block;color:%sub%;font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pill{border-radius:99px;padding:3px 10px;font-size:12px;font-weight:500}
.flow{display:flex;flex-wrap:wrap;gap:6px;justify-content:space-between}.step{flex:1;min-width:92px;text-align:center;position:relative}
.step .dot{margin:0 auto 6px;width:48px;height:48px}.step b{display:block;font-size:13px;color:%ink%}.step small{color:%sub%;font-size:11.5px}
.step:not(:last-child)::after{content:"";position:absolute;top:24px;left:calc(50% + 30px);width:calc(100% - 60px);border-top:2px dashed %line%}
.tbl{border-collapse:collapse;width:100%;font-size:13.5px;color:%ink%}.tbl th,.tbl td{padding:8px 10px;text-align:right;border-bottom:1px solid %line%}.tbl th:first-child,.tbl td:first-child{text-align:left}
.stButton>button,.stDownloadButton>button{border-radius:99px;padding:.65rem 1.6rem;border:0;background:#1A73E8;color:#fff;font-weight:500;width:100%}
.stButton>button:hover,.stDownloadButton>button:hover{background:#1765CC;color:#fff}
[class*="st-key-navoff"] button{background:%chip%!important;border:1px solid %line%!important;border-radius:99px!important;padding:.35rem .25rem!important;min-height:0!important}
[class*="st-key-navoff"] button *{color:%ink%!important;font-size:13px!important}
[class*="st-key-navon"] button{background:#1A73E8!important;border:1px solid #1A73E8!important;border-radius:99px!important;padding:.35rem .25rem!important;min-height:0!important}
[class*="st-key-navon"] button *{color:#fff!important;font-size:13px!important}
div[data-baseweb="select"]>div,[data-testid="stFileUploaderDropzone"]{background:%chip%!important;border-color:%line%!important}
div[data-baseweb="select"] *,[data-testid="stFileUploaderDropzone"] *:not(button):not(button *){color:%ink%!important}
[data-testid="stExpander"] summary,[data-testid="stExpander"] summary *{color:%ink%!important}
</style>"""
for k, v in T.items(): CSS = CSS.replace(f"%{k}%", v)
st.markdown(CSS, unsafe_allow_html=True)

TC = {"spike": AMB, "dropout": RED, "flatline": BLUE, "drift": GREEN, "noise": PUR, "natural_extreme": CY}
EMO = {"spike": "⚡", "dropout": "🕳️", "flatline": "➖", "drift": "📈", "noise": "〰️", "natural_extreme": "🌪️"}
NAV = ["Home", "Series", "Anomalies", "Repairs", "Scores", "Agents", "Data"]
RAW = {"uscrn": "data/raw/uscrn", "imd_tmax": "data/raw/imd_tmax", "imd_rain": "data/raw/imd_rainfall"}
STEPS = [("📥", "Data", "load, check, clean"), ("🧩", "Features", "16-20 signals"), ("🧠", "Detect", "LSTM autoencoder"), ("🔎", "Diagnose", "type + evidence"), ("🛠️", "Repair", "4 methods, best wins"), ("📄", "Report", "log + export")]

def kpi(c, label, v, sub=""): c.markdown(f'<div class="kpi"><span>{label}</span><b>{v}</b><span>{sub}</span></div>', unsafe_allow_html=True)
def has(src): return src == "demo" or any(f != ".gitkeep" for _, _, fs in os.walk(RAW[src]) for f in fs)
def table(df): st.markdown(f'<div class="card" style="overflow-x:auto">{df.round(3).to_html(classes="tbl", border=0, na_rep="–").replace(chr(10), "")}</div>', unsafe_allow_html=True)
def show(f, h=360, legend=True):
    f.update_layout(height=h, margin=dict(l=0, r=0, t=24, b=0), paper_bgcolor=T["card"], plot_bgcolor=T["card"], font=dict(color=T["ink"]), showlegend=legend, legend=dict(orientation="h", y=-.25))
    f.update_xaxes(gridcolor=T["line"], zeroline=False); f.update_yaxes(gridcolor=T["line"], zeroline=False)
    st.plotly_chart(f, use_container_width=True, config={"displayModeBar": False})
def flow(done):
    h = "".join(f'<div class="step"><div class="dot" style="background:{GREEN + "33" if done else T["chip"]}">{e if not done else "✓"}</div><b>{n}</b><small>{d}</small></div>' for e, n, d in STEPS)
    st.markdown(f'<div class="card"><div class="flow">{h}</div></div>', unsafe_allow_html=True)
def ae_diagram():
    c, s = T["ink"], T["sub"]; items = [("Input window", BLUE), ("LSTM encoder", BLUE), ("Latent code", AMB), ("LSTM decoder", GREEN), ("Rebuilt window", GREEN)]
    g = "".join(f'<rect x="{10 + i * 140}" y="14" width="120" height="48" rx="14" fill="{col}2E" stroke="{col}"/><text x="{70 + i * 140}" y="43" text-anchor="middle" fill="{c}" font-size="13">{t}</text>' + (f'<text x="{138 + i * 140}" y="46" text-anchor="middle" fill="{s}" font-size="22">›</text>' if i < 4 else "") for i, (t, col) in enumerate(items))
    st.markdown(f'<div class="card"><svg viewBox="0 0 700 104" width="100%" font-family="Roboto,sans-serif">{g}<text x="350" y="92" text-anchor="middle" fill="{s}" font-size="13">Compare input with rebuilt window. Small difference = normal. Large difference = suspicious.</text></svg></div>', unsafe_allow_html=True)
def choice(key, options, fmt=str, default=None, per_row=None):
    cur = st.session_state.get(key); cur = cur if cur in options else (default if default in options else options[0]); per_row = per_row or len(options)
    for r0 in range(0, len(options), per_row):
        for i, (c, o) in enumerate(zip(st.columns(per_row), options[r0:r0 + per_row])):
            with c.container(key=f"nav{'on' if o == cur else 'off'}_{key}_{r0 + i}"):
                st.button(fmt(o), key=f"b_{key}_{r0 + i}", on_click=st.session_state.__setitem__, args=(key, o), use_container_width=True)
    return cur
def zoom(R, r):
    n = len(R["cor"]); pad = max(36, 4 * r.steps); a, b = max(0, r.i0 - pad), min(n, r.i1 + pad + 1); ix = R["cor"].index[a:b]; f = go.Figure()
    if R["labelled"]: f.add_scatter(x=ix, y=R["clean"].iloc[a:b], name="True value", line=dict(color=T["sub"], width=1.5, dash="dot"))
    f.add_scatter(x=ix, y=R["cor"].iloc[a:b], name="Observed", line=dict(color=BLUE, width=2))
    f.add_scatter(x=ix, y=R["reps"][R["best"]].iloc[a:b], name=f"Repaired ({R['best']})", line=dict(color=GREEN, width=2))
    f.add_vrect(x0=R["cor"].index[max(r.i0 - 1, 0)], x1=R["cor"].index[min(r.i1 + 1, n - 1)], fillcolor=RED, opacity=.15, line_width=0); f.update_yaxes(title=R["unit"]); show(f, 320)

_, tg = st.columns([6, 1]); tg.toggle("🌙", key="dark")
nav = choice("nav", NAV, default="Home")
R = st.session_state.get("res")
st.markdown('<div class="hero"><h1>🛡️ SkyGuard AI</h1><p>Finds, explains and fixes faulty readings in weather data.</p>' + (f'<span class="chip">{R["name"]}</span><span class="chip">{int(R["flag"].sum())} points flagged</span><span class="chip">best fix: {R["best"]}</span>' if R else '<span class="chip">Detect</span><span class="chip">Diagnose</span><span class="chip">Repair</span>') + '</div>', unsafe_allow_html=True)

if nav == "Home":
    flow(bool(R))
    with st.expander("How does the detector work?"): ae_diagram(); st.caption("The model only ever sees normal weather, so it can rebuild normal windows well and fails on faulty ones. That failure size is the anomaly score.")
    st.markdown("### Pick a dataset")
    NAMES = {**{k: v["name"] for k, v in CFG.items()}, "upload": "Your own CSV"}
    src = choice("src", list(NAMES), NAMES.get, "demo", 3)
    data, target, ok = None, None, (has(src) if src != "upload" else False)
    if src == "upload":
        up = st.file_uploader("CSV with a date column and numeric columns (hourly or daily)", type="csv")
        st.caption(f"Processed in memory, not kept after your session. Limit {core.MAX_ROWS:,} rows. Try sample_data/example.csv.")
        if up:
            try: data = core.load_csv(up); target = st.selectbox("Column to check", list(data[0].columns)); ok = True
            except Exception as e: st.error(f"Could not use this file: {e}")
    else: st.markdown(f'<div class="card"><b>{CFG[src]["name"]}</b><br><small style="color:{T["sub"]}">{"Ready to analyse" if ok else "No files yet. Open the Data tab for the download command."}</small></div>', unsafe_allow_html=True)
    if st.button("Run SkyGuard", disabled=not ok):
        box = st.status("Agents working…", expanded=True)
        P = Pipeline(src, progress=lambda a, t, s: box.write(f"{'✅' if s == 'ok' else '❌'} **{a}** · {t}"), data=data, target=target, out=tempfile.mkdtemp() if src == "upload" else "outputs")
        try: st.session_state.res = P.run_all(); box.update(label="Done. Explore the tabs above.", state="complete")
        except Exception as e: box.update(label=f"Failed: {e}", state="error")
        st.rerun() if st.session_state.get("res") else None
    if R:
        c = st.columns(3); m = R["metrics"]
        if R["labelled"]: kpi(c[0], "Faults caught", f'{m["event_recall"]:.0%}', "of injected events"); kpi(c[1], "F1 score", f'{m["f1"]:.2f}', "point level")
        else: kpi(c[0], "Flagged points", int(R["flag"].sum()), f'{R["flag"].mean():.1%} of data'); kpi(c[1], "Events", len(R["diag"]), "to review")
        kpi(c[2], "Repair error", f'{R["rtab"].loc["all", R["best"]]:.2f} {R["unit"]}', f'{R["best"]} (best)')
        out = pd.DataFrame({"timestamp": R["cor"].index, "original": R["cor"].values, "repaired": R["reps"][R["best"]].values, "flagged": R["flag"]})
        st.download_button("Download repaired CSV", out.to_csv(index=False), "skyguard_repaired.csv", "text/csv")
elif not R: st.markdown('<div class="card">Run SkyGuard on the Home tab first.</div>', unsafe_allow_html=True)
elif nav == "Series":
    i0 = R["i2"] if R["labelled"] else 0; sl = slice(i0, None); meth = choice("meth", list(R["reps"]), str, R["best"], 4); ix = R["cor"].index; f = go.Figure()
    if R["labelled"]: f.add_scatter(x=ix[sl], y=R["clean"][sl], name="True value", line=dict(color=T["sub"], width=1, dash="dot"))
    f.add_scatter(x=ix[sl], y=R["cor"][sl], name="Observed", line=dict(color=BLUE, width=1.4)); f.add_scatter(x=ix[sl], y=R["reps"][meth][sl], name=f"Repaired ({meth})", line=dict(color=GREEN, width=1.4))
    fl = np.flatnonzero(R["flag"]); f.add_scatter(x=ix[fl], y=R["cor"].iloc[fl], mode="markers", name="Flagged", marker=dict(color=RED, size=7))
    f.update_yaxes(title=R["unit"]); f.update_xaxes(range=[ix[i0], ix[min(len(ix) - 1, i0 + 500)]], rangeslider=dict(visible=True)); show(f, 440)
    st.caption("How to read: blue is what the sensor reported, red dots are points SkyGuard distrusts, green is the fixed series. Drag the slider to move through time.")
elif nav == "Anomalies":
    d = R["diag"]; st.markdown(f"### {len(d)} events found")
    if len(d):
        c = st.columns([2, 3]); cnt = d.type.value_counts()
        with c[0]: show(go.Figure(go.Pie(labels=[t.replace("_", " ") for t in cnt.index], values=cnt.values, hole=.62, marker=dict(colors=[TC[t] for t in cnt.index]), textinfo="value")), 260, False)
        with c[1]: f = go.Figure(go.Scatter(x=d.start, y=d.peak_score, mode="markers", text=d.type, marker=dict(size=np.clip(d.steps * 4 + 6, 6, 28), color=[TC[t] for t in d.type], opacity=.8))); f.update_yaxes(type="log", title="score"); show(f, 260, False)
        st.caption("Left: what kinds of faults were found. Right: when they happened; higher and bigger means more severe and longer.")
        top = d.nlargest(60, "peak_score"); lab = {i: f"{r.type.replace('_', ' ').title()} · {r.start:%d %b %Y %H:%M}" for i, r in top.iterrows()}
        pick = st.selectbox("Inspect an event", list(lab), format_func=lab.get); r = top.loc[pick]; zoom(R, r); st.caption(f"Evidence: {r.evidence}. Red band marks the event.")
        h = "".join(f'<div class="row"><div class="dot" style="background:{TC[x.type]}33">{EMO[x.type]}</div><div class="mid"><b>{x.type.replace("_", " ").title()}</b><small>{x.start:%d %b %Y %H:%M} · {x.steps} step(s) · {x.evidence}</small></div><span class="pill" style="background:{GREEN}22;color:{GREEN}">Repaired</span></div>' for x in top.head(30).itertuples())
        st.markdown(f'<div class="card">{h}</div>', unsafe_allow_html=True); st.caption("Natural extremes are marked separately: a big reading is not always a broken sensor.")
elif nav == "Repairs":
    t = R["rtab"].astype(float); b, a = t.loc["all", "before"], t.loc["all", R["best"]]; c = st.columns(3)
    kpi(c[0], "Best method", R["best"]); kpi(c[1], "Average error", f"{a:.2f} {R['unit']}"); kpi(c[2], "Error reduced", f"{(b - a) / b:.0%}" if np.isfinite(b) and b > 0 else "n/a", "vs. leaving faults in")
    cols = [m for m in t.columns]; pal = dict(before=RED, linear=BLUE, context=AMB, knn=PUR, lstm=GREEN); f = go.Figure([go.Bar(x=list(t.index), y=t[m], name=m, marker_color=pal.get(m, BLUE)) for m in cols]); f.update_layout(barmode="group"); f.update_yaxes(title=f"error ({R['unit']})"); show(f, 340)
    st.caption("How to read: each group is a fault type; each bar is the average gap to the true value after fixing (lower is better). Red 'before' is the damage without repair; dropouts have no 'before' because the value is missing.")
    table(t)
elif nav == "Scores":
    sc, thr, i2 = R["sc"], R["thr"], R["i2"]; lo = i2 if R["labelled"] else 0
    if R["labelled"]:
        m = R["metrics"]; c = st.columns(5)
        for col, (k, l) in zip(c, [("precision", "Precision"), ("recall", "Recall"), ("f1", "F1"), ("roc_auc", "ROC-AUC"), ("event_recall", "Events hit")]): kpi(col, l, f"{m[k]:.2f}")
        tr = np.zeros(len(sc), bool)
        for s, e, _ in R["ev"]: tr[s:e] = True
        fl = R["flag"]; tp, fp, fn = int((tr & fl)[i2:].sum()), int((~tr & fl)[i2:].sum()), int((tr & ~fl)[i2:].sum())
        f = go.Figure(go.Bar(x=[tp, fp, fn], y=["Caught", "False alarms", "Missed"], orientation="h", marker_color=[GREEN, AMB, RED])); show(f, 200, False); st.caption("Of the points checked: caught = real faults flagged, false alarms = normal points flagged, missed = real faults not flagged.")
    s = sc.iloc[max(lo, len(sc) - 5000):]; f = go.Figure(go.Scatter(x=s.index, y=s, name="Anomaly score", line=dict(color=BLUE, width=1)))
    if R["labelled"]:
        for a0, e0, _ in R["ev"][:40]: f.add_vrect(x0=sc.index[a0], x1=sc.index[min(e0, len(sc) - 1)], fillcolor=RED, opacity=.18, line_width=0)
    f.add_hline(y=thr, line=dict(color=RED, dash="dash"), annotation_text="threshold"); f.update_yaxes(type="log", title="score"); show(f, 320, False)
    st.caption("How to read: spikes above the dashed line are flagged." + (" Red bands are the faults we injected, so you can see whether the model reacted." if R["labelled"] else ""))
    c = st.columns(2)
    with c[0]: h = go.Figure(go.Histogram(x=np.log10(sc.iloc[:i2].clip(lower=1e-9)), marker_color=BLUE, nbinsx=40)); h.add_vline(x=np.log10(thr), line=dict(color=RED, dash="dash")); h.update_xaxes(title="log10 score (normal data)"); show(h, 240, False)
    with c[1]: l = go.Figure(go.Scatter(y=R["hist"], mode="lines+markers", line=dict(color=GREEN))); l.update_xaxes(title="epoch"); l.update_yaxes(title="validation loss"); show(l, 240, False)
    st.caption("Left: the threshold sits at the 99th percentile of normal scores. Right: the model got better at rebuilding normal data each epoch, then stopped early.")
elif nav == "Agents":
    L = R["logs"]; ag = list(dict.fromkeys(L.agent)); pal = [BLUE, AMB, PUR, CY, GREEN, RED]
    f = go.Figure(go.Bar(x=L.seconds, y=L.tool, orientation="h", marker_color=[pal[ag.index(a) % 6] for a in L.agent], text=L.agent, textposition="auto")); f.update_yaxes(autorange="reversed"); f.update_xaxes(title="seconds"); show(f, 380, False)
    st.caption("Each bar is one tool call made by an agent; colour = which agent. Training is usually the longest step.")
    h = "".join(f'<div class="row"><div class="dot" style="background:{(GREEN if r.status == "ok" else RED)}33">{"✓" if r.status == "ok" else "!"}</div><div class="mid"><b>{r.agent} · {r.tool}</b><small>{r.detail}</small></div><small style="color:{T["sub"]}">{r.timestamp}</small></div>' for r in L.itertuples())
    st.markdown(f'<div class="card">{h}</div>', unsafe_allow_html=True); st.download_button("Download report", R["report"], "skyguard_report.md")
if nav == "Data":
    st.markdown("### Data setup")
    for k in RAW: g = has(k); st.markdown(f'<div class="row"><div class="dot" style="background:{(GREEN if g else AMB)}33">{"✓" if g else "↓"}</div><div class="mid"><b>{CFG[k]["name"]}</b><small>{"files found" if g else "python scripts/download_data.py " + {"uscrn": "uscrn", "imd_tmax": "tmax", "imd_rain": "rain"}[k]}</small></div></div>', unsafe_allow_html=True)
    if R:
        q = R["quality"]; v = [k for k, x in q.items() if isinstance(x, dict)]; st.markdown("### Data health")
        c = st.columns(2)
        with c[0]: f = go.Figure(go.Bar(x=v, y=[q[k]["missing_pct"] for k in v], marker_color=AMB)); f.update_yaxes(title="% missing"); show(f, 240, False)
        with c[1]: f = go.Figure(go.Histogram(x=R["clean"].dropna(), marker_color=BLUE, nbinsx=40)); f.update_xaxes(title=f'{R["target"]} ({R["unit"]})'); show(f, 240, False)
        st.caption(f"Left: share of missing readings per variable. Right: spread of the checked variable. {q['missing_steps']} timestamps were absent and {q['duplicate_timestamps']} duplicated.")