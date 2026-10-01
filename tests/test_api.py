import pytest

from app import main


@pytest.fixture
def client():
    main.app.config.update(TESTING=True)
    with main.app.test_client() as client:
        yield client


def test_index_lists_endpoints(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_json()
    assert body["service"] == "finveritas-ratio-service"
    assert "POST /api/v1/analyze" in body["endpoints"]


def test_health_and_ready(client):
    assert client.get("/health").get_json()["status"] == "healthy"
    assert client.get("/ready").status_code == 200


def test_sample_analysis(client):
    response = client.get("/api/v1/sample")
    assert response.status_code == 200
    assert len(response.get_json()["checks"]) == 7


def test_liquidity_endpoint(client):
    response = client.post("/api/v1/liquidity", json={
        "current_assets": 300, "current_liabilities": 100, "cash_and_equivalents": 40})
    assert response.status_code == 200
    checks = {c["metric"]: c for c in response.get_json()["checks"]}
    assert checks["current_ratio"]["value"] == 3.0
    assert checks["current_ratio"]["status"] == "PASS"


def test_solvency_endpoint(client):
    response = client.post("/api/v1/solvency", json={"total_debt": 400, "total_equity": 100})
    assert response.status_code == 200
    assert response.get_json()["summary"]["verdict"] == "HIGH_RISK"


def test_dscr_endpoint(client):
    response = client.post("/api/v1/dscr", json={"net_operating_income": 300, "annual_debt_service": 100})
    assert response.get_json()["checks"][0]["status"] == "PASS"


def test_analyze_endpoint(client):
    response = client.post("/api/v1/analyze", json={"current_assets": 50, "current_liabilities": 100})
    assert response.status_code == 200
    assert response.get_json()["summary"]["verdict"] == "HIGH_RISK"


def test_invalid_body_returns_400(client):
    response = client.post("/api/v1/analyze", data="not json", content_type="text/plain")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_non_numeric_field_returns_400(client):
    response = client.post("/api/v1/liquidity", json={"current_assets": "lots", "current_liabilities": 1})
    assert response.status_code == 400


def test_unknown_route_returns_json_404(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Not Found"


def test_metrics_endpoint_exposes_custom_metrics(client):
    client.get("/api/v1/sample")
    text = client.get("/metrics").get_data(as_text=True)
    assert "flask_http_request_duration_seconds" in text
    assert "app_info" in text
    assert "app_start_time_seconds" in text
    assert "ratio_checks_total" in text


def test_chaos_fault_injection(client, monkeypatch):
    monkeypatch.setattr(main, "FAULT_RATE", 1.0)
    assert client.get("/api/v1/sample").status_code == 503
    # Probes are never affected, so Kubernetes keeps the pod in service.
    assert client.get("/health").status_code == 200
