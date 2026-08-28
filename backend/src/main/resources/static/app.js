/* DataMend testing frontend - drives the Spring Boot proxy and ML service. */

const CORRUPTION_PARAMS = {
    mcar:            [{ name: "p",            value: 0.1 }],
    rdo:             [{ name: "p",            value: 0.1 }],
    seq_missing:     [{ name: "p",            value: 0.1 }, { name: "seq_len", value: 32 }],
    block_missing:   [{ name: "factor",       value: 0.1 }, { name: "block_len", value: 32 }, { name: "block_width", value: 3 }],
    mar_logistic:    [{ name: "obs_rate",     value: 0.5 }, { name: "missing_rate", value: 0.1 }],
    mnar_x:          [{ name: "offset",       value: 0.0 }],
    mnar_t:          [{ name: "cycle",        value: 20 }, { name: "pos", value: 10 }, { name: "scale", value: 3 }],
    mnar_nonuniform: [{ name: "p",            value: 0.1 }, { name: "increase_factor", value: 0.5 }],
};

const DEFAULTS = {
    dataset: "ETTh1",
    columns: "HUFL,HULL,MUFL,MULL,LUFL,LULL,OT",
    detector: "timercd",
    threshold: "0.8",
    strategy: "reject",
};

let activeEventSource = null;
let activePollInterval = null;

const elements = {
    dataset: document.getElementById("dataset"),
    columns: document.getElementById("columns"),
    detector: document.getElementById("detector"),
    threshold: document.getElementById("threshold"),
    corruptionEnabled: document.getElementById("corruption-enabled"),
    corruptionMethod: document.getElementById("corruption-method"),
    corruptionParams: document.getElementById("corruption-params"),
    strategy: document.getElementById("mvh-strategy"),
    btnAnalyze: document.getElementById("btn-analyze"),
    btnScores: document.getElementById("btn-scores"),
    btnReset: document.getElementById("btn-reset"),
    status: document.getElementById("status"),
    summary: document.getElementById("summary"),
    jsonOutput: document.getElementById("json-output"),
};

function renderCorruptionParams() {
    const method = elements.corruptionMethod.value;
    const params = CORRUPTION_PARAMS[method] || [];
    elements.corruptionParams.innerHTML = "";
    for (const param of params) {
        const label = document.createElement("label");
        label.textContent = param.name;
        const input = document.createElement("input");
        input.type = "number";
        input.step = "any";
        input.value = String(param.value);
        input.dataset.paramName = param.name;
        label.appendChild(input);
        elements.corruptionParams.appendChild(label);
    }
}

function readCorruption() {
    if (!elements.corruptionEnabled.checked) {
        return null;
    }
    const params = {};
    for (const input of elements.corruptionParams.querySelectorAll("input")) {
        params[input.dataset.paramName] = parseFloat(input.value);
    }
    return {
        enabled: true,
        method: elements.corruptionMethod.value,
        params: params,
    };
}

function buildPayload() {
    return {
        analysisId: "ui-" + Date.now(),
        datasetName: elements.dataset.value.trim() || DEFAULTS.dataset,
        columns: elements.columns.value
            .split(",")
            .map(function (column) { return column.trim(); })
            .filter(Boolean),
        detector: elements.detector.value.trim() || DEFAULTS.detector,
        threshold: parseFloat(elements.threshold.value),
        corruption: readCorruption(),
        missingValueHandling: {
            strategy: elements.strategy.value,
        },
    };
}

function setStatus(text, isError) {
    elements.status.textContent = text || "";
    elements.status.className = "status" + (isError ? " error" : "");
}

function setBusy(busy) {
    elements.btnAnalyze.disabled = busy;
    elements.btnScores.disabled = busy;
}

function renderSummary(summaryRows) {
    elements.summary.innerHTML = "";
    for (const row of summaryRows) {
        const div = document.createElement("div");
        div.className = "row";
        const key = document.createElement("span");
        key.className = "key";
        key.textContent = row.key + ": ";
        div.appendChild(key);
        div.appendChild(document.createTextNode(String(row.value)));
        elements.summary.appendChild(div);
    }
}

function renderJson(data) {
    elements.jsonOutput.textContent = JSON.stringify(data, null, 2);
}

function cleanupAsyncStreams() {
    if (activeEventSource) {
        activeEventSource.close();
        activeEventSource = null;
    }
    if (activePollInterval) {
        clearInterval(activePollInterval);
        activePollInterval = null;
    }
}

function analyzeSummary(data) {
    return [
        { key: "analysisId", value: data.id || data.analysisId || "n/a" },
        { key: "status", value: data.status },
        { key: "detector", value: data.detector || "n/a" },
        { key: "anomalies count", value: Array.isArray(data.anomalies) ? data.anomalies.length : 0 },
        { key: "startedAt", value: data.startedAt || "n/a" },
        { key: "completedAt", value: data.completedAt || "n/a" },
    ];
}

function scoresSummary(data) {
    return [
        { key: "status", value: data.status },
        { key: "timestamps / scores", value: Array.isArray(data.scores) ? data.scores.length : "n/a" },
        { key: "missingRate", value: data.missingRate === undefined ? "n/a" : data.missingRate },
        { key: "missingValueHandling", value: data.missingValueHandling === undefined ? "n/a" : data.missingValueHandling },
    ];
}

async function handleAnalyze() {
    cleanupAsyncStreams();
    setBusy(true);
    setStatus("Initiating asynchronous analysis...");

    const payload = buildPayload();
    try {
        const response = await fetch("/api/v1/ml/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const initialBody = await response.json();
        if (!response.ok) {
            setStatus("HTTP " + response.status + " - " + (initialBody.detail || initialBody.error || "Analysis request failed"), true);
            renderSummary([{ key: "HTTP status", value: response.status }]);
            renderJson(initialBody);
            setBusy(false);
            return;
        }

        const analysisId = initialBody.analysisId;
        setStatus("Analysis submitted (ID: " + analysisId + "). Listening for real-time events via SSE...");
        renderSummary([
            { key: "analysisId", value: analysisId },
            { key: "status", value: "RUNNING" },
        ]);
        renderJson(initialBody);

        let completed = false;

        // Try SSE connection first
        if (window.EventSource) {
            const eventSource = new EventSource("/api/v1/analyses/" + encodeURIComponent(analysisId) + "/events");
            activeEventSource = eventSource;

            eventSource.addEventListener("status", (e) => {
                const data = JSON.parse(e.data);
                setStatus("Analysis status: " + data.status + "...");
            });

            eventSource.addEventListener("completed", (e) => {
                completed = true;
                const result = JSON.parse(e.data);
                setStatus("Analysis COMPLETED! (Found " + (result.anomalies ? result.anomalies.length : 0) + " anomalies)");
                renderSummary(analyzeSummary(result));
                renderJson(result);
                cleanupAsyncStreams();
                setBusy(false);
            });

            eventSource.addEventListener("failed", (e) => {
                completed = true;
                const errData = JSON.parse(e.data);
                setStatus("Analysis FAILED: " + (errData.error || "Execution error"), true);
                renderSummary([{ key: "status", value: "FAILED" }, { key: "error", value: errData.error }]);
                renderJson(errData);
                cleanupAsyncStreams();
                setBusy(false);
            });

            eventSource.onerror = () => {
                // If SSE disconnects before completion, fallback to polling
                if (!completed) {
                    eventSource.close();
                    activeEventSource = null;
                    startPolling(analysisId);
                }
            };
        } else {
            startPolling(analysisId);
        }

    } catch (err) {
        setStatus("Network error: " + err.message, true);
        renderJson({ error: err.message });
        setBusy(false);
    }
}

function startPolling(analysisId) {
    if (activePollInterval) return;
    setStatus("Polling /api/v1/analyses/" + analysisId + " for results...");

    activePollInterval = setInterval(async () => {
        try {
            const res = await fetch("/api/v1/analyses/" + encodeURIComponent(analysisId));
            if (!res.ok) return;
            const data = await res.json();

            if (data.status === "COMPLETED") {
                clearInterval(activePollInterval);
                activePollInterval = null;
                setStatus("Analysis COMPLETED! (Found " + (data.anomalies ? data.anomalies.length : 0) + " anomalies)");
                renderSummary(analyzeSummary(data));
                renderJson(data);
                setBusy(false);
            } else if (data.status === "FAILED") {
                clearInterval(activePollInterval);
                activePollInterval = null;
                setStatus("Analysis FAILED", true);
                renderSummary(analyzeSummary(data));
                renderJson(data);
                setBusy(false);
            }
        } catch (e) {
            console.error("Polling error", e);
        }
    }, 1500);
}

async function handleScores() {
    cleanupAsyncStreams();
    setBusy(true);
    setStatus("Requesting raw scores (/api/v1/ml/scores)...");
    const payload = buildPayload();

    try {
        const response = await fetch("/api/v1/ml/scores", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        let body;
        try {
            body = await response.json();
        } catch (err) {
            body = { error: "(non-JSON response)" };
        }

        if (!response.ok) {
            setStatus("HTTP " + response.status + " - " + (body.detail || body.error || "Scores request failed"), true);
            renderSummary([{ key: "HTTP status", value: response.status }]);
            renderJson(body);
            return;
        }

        setStatus("HTTP " + response.status + " - OK (Fetched " + (body.scores ? body.scores.length : 0) + " timestamps)");
        renderSummary([{ key: "HTTP status", value: response.status }].concat(scoresSummary(body)));
        renderJson(body);
    } catch (err) {
        setStatus("Network error: " + err.message, true);
        renderSummary([{ key: "HTTP status", value: "n/a (network)" }]);
        renderJson({ error: err.message });
    } finally {
        setBusy(false);
    }
}

function reset() {
    cleanupAsyncStreams();
    elements.dataset.value = DEFAULTS.dataset;
    elements.columns.value = DEFAULTS.columns;
    elements.detector.value = DEFAULTS.detector;
    elements.threshold.value = DEFAULTS.threshold;
    elements.corruptionEnabled.checked = false;
    elements.corruptionMethod.value = "mcar";
    elements.strategy.value = DEFAULTS.strategy;
    renderCorruptionParams();
    setStatus("Reset");
    elements.summary.innerHTML = "";
    elements.jsonOutput.textContent = "(no request yet)";
}

function init() {
    renderCorruptionParams();
    elements.corruptionEnabled.addEventListener("change", function () {
        renderCorruptionParams();
    });
    elements.corruptionMethod.addEventListener("change", function () {
        renderCorruptionParams();
    });
    elements.btnAnalyze.addEventListener("click", handleAnalyze);
    elements.btnScores.addEventListener("click", handleScores);
    elements.btnReset.addEventListener("click", reset);
}

document.addEventListener("DOMContentLoaded", init);

