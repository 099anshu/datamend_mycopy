"""Research evaluation framework for TimeRCD anomaly detection on TSDB datasets.

This package is intentionally isolated from the FastAPI application. It does
not import ``main`` and does not call any HTTP endpoints; it calls the
existing ``TimeRCDDetector`` directly.
"""