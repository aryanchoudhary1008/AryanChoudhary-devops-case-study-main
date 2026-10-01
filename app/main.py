"""FinVeritas Ratio Service.

A small Flask microservice that exposes the FinVeritas financial-ratio checks over a
REST API, with Prometheus metrics for monitoring (request rate, latency, errors, uptime).

Environment variables
    APP_VERSION        version string reported by the API and metrics (set at build time)
    FAULT_RATE         0.0-1.0, fraction of /api requests that fail with HTTP 503
                       (chaos-engineering switch used to test alerting and dashboards)
    EXTRA_LATENCY_MS   artificial delay added to every /api request
"""
from __future__ import annotations

import logging
import os
import random
import time

from flask import Flask, jsonify, request
from prometheus_client import Counter, Gauge
from prometheus_flask_exporter import PrometheusMetrics
from werkzeug.exceptions import HTTPException

from app import ratios

SERVICE_NAME = "finveritas-ratio-service"
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
FAULT_RATE = float(os.getenv("FAULT_RATE", "0"))
EXTRA_LATENCY_MS = int(os.getenv("EXTRA_LATENCY_MS", "0"))
START_TIME = time.time()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(SERVICE_NAME)

app = Flask(__name__)

# Request count / latency histogram / exceptions for every endpoint, plus GET /metrics.
metrics = PrometheusMetrics(app, group_by="endpoint")
metrics.info("app_info", "FinVeritas ratio service build information", version=APP_VERSION, service=SERVICE_NAME)

START_TIME_GAUGE = Gauge("app_start_time_seconds", "Unix timestamp at which the service process started")
START_TIME_GAUGE.set(START_TIME)
CHECKS_TOTAL = Counter("ratio_checks_total", "Financial ratio checks evaluated", ["metric", "status"])
VERDICTS_TOTAL = Counter("analysis_verdicts_total", "Overall verdicts returned by /api/v1/analyze", ["verdict"])


def _payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object")
    return data


def _record(checks):
    for check in checks:
        CHECKS_TOTAL.labels(check["metric"], check["status"]).inc()
    return checks


@app.before_request
def chaos_middleware():
    """Optionally inject latency and failures into API calls (chaos-engineering experiments)."""
    if not request.path.startswith("/api/"):
        return None
    if EXTRA_LATENCY_MS > 0:
        time.sleep(EXTRA_LATENCY_MS / 1000)
    if FAULT_RATE > 0 and random.random() < FAULT_RATE:  # nosec B311 - not used for security
        log.warning("chaos: injected fault on %s", request.path)
        return jsonify({"error": "injected fault (chaos experiment)"}), 503
    return None


@app.errorhandler(ValueError)
def bad_request(err):
    return jsonify({"error": str(err)}), 400


@app.errorhandler(HTTPException)
def http_error(err):
    return jsonify({"error": err.name, "detail": err.description}), err.code


@app.get("/")
def index():
    return jsonify({
        "service": SERVICE_NAME,
        "version": APP_VERSION,
        "description": "FinVeritas financial-ratio checks as a microservice",
        "endpoints": {
            "GET /health": "liveness probe",
            "GET /ready": "readiness probe",
            "GET /metrics": "Prometheus metrics",
            "GET /api/v1/sample": "analyse the built-in sample company",
            "POST /api/v1/analyze": "run every check the supplied figures allow",
            "POST /api/v1/liquidity": "current ratio, working capital, cash ratio",
            "POST /api/v1/solvency": "debt/equity, debt/assets, interest coverage",
            "POST /api/v1/dscr": "debt service coverage ratio",
        },
    })


@app.get("/health")
@metrics.do_not_track()
def health():
    return jsonify({"status": "healthy", "version": APP_VERSION,
                    "uptime_seconds": round(time.time() - START_TIME, 1)})


@app.get("/ready")
@metrics.do_not_track()
def ready():
    return jsonify({"status": "ready"})


@app.get("/api/v1/sample")
def sample():
    result = ratios.analyze(ratios.SAMPLE_COMPANY)
    _record(result["checks"])
    VERDICTS_TOTAL.labels(result["summary"]["verdict"]).inc()
    return jsonify({"company": "Sample Manufacturing Co.", "input": ratios.SAMPLE_COMPANY, **result})


@app.post("/api/v1/analyze")
def analyze():
    result = ratios.analyze(_payload())
    _record(result["checks"])
    VERDICTS_TOTAL.labels(result["summary"]["verdict"]).inc()
    return jsonify(result)


@app.post("/api/v1/liquidity")
def liquidity():
    checks = _record(ratios.liquidity_checks(_payload()))
    return jsonify({"checks": checks, "summary": ratios.summarize(checks)})


@app.post("/api/v1/solvency")
def solvency():
    checks = _record(ratios.solvency_checks(_payload()))
    return jsonify({"checks": checks, "summary": ratios.summarize(checks)})


@app.post("/api/v1/dscr")
def debt_service():
    checks = _record(ratios.debt_service_checks(_payload()))
    return jsonify({"checks": checks, "summary": ratios.summarize(checks)})


if __name__ == "__main__":
    # Local development only; containers run the app with gunicorn (see Dockerfile).
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")))
