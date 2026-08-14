/* DataMend testing frontend - drives the Spring Boot proxy for ml-service. */

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

function analyzeSummary(data) {
    return [
        { key: "status", value: data.status },
        { key: "anomaly count", value: Array.isArray(data.anomalies) ? data.anomalies.length : "n/a" },
        { key: "missingRate", value: data.missingRate === undefined ? "n/a" : data.missingRate },
        { key: "missingValueHandling", value: data.missingValueHandling === undefined ? "n/a" : data.missingValueHandling },
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

async function post(endpoint, payload, summaryFn) {
    setBusy(true);
    setStatus("Requesting " + endpoint + " ...");
    try {
        const response = await fetch(endpoint, {
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
            setStatus("HTTP " + response.status + " - " + (body.detail || body.error || "request failed"), true);
            renderSummary([{ key: "HTTP status", value: response.status }]);
            renderJson(body);
            return;
        }

        setStatus("HTTP " + response.status + " - OK");
        renderSummary([{ key: "HTTP status", value: response.status }].concat(summaryFn(body)));
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
    elements.btnAnalyze.addEventListener("click", function () {
        post("/api/v1/ml/analyze", buildPayload(), analyzeSummary);
    });
    elements.btnScores.addEventListener("click", function () {
        post("/api/v1/ml/scores", buildPayload(), scoresSummary);
    });
    elements.btnReset.addEventListener("click", reset);
}

document.addEventListener("DOMContentLoaded", init);
