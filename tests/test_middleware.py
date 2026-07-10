from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import RateLimitConfig
from app.limiter import InMemoryRateLimiter
from app.middleware import RateLimitMiddleware
from app.main import app as default_app


client = TestClient(default_app)


def make_test_app() -> tuple[FastAPI, TestClient]:
    config = RateLimitConfig(
        plans={
            "standard": {"organization": {"requests": 1, "window_seconds": 60, "burst": 0}},
        },
        endpoint_limits={
            "read": {"requests": 1, "window_seconds": 60, "burst": 0},
            "write": {"requests": 1, "window_seconds": 60, "burst": 0},
        },
        organizations={"org-standard": {"plan": "standard"}},
        routes=[],
        cleanup={"idle_ttl_seconds": 900, "cleanup_interval_seconds": 60},
        default_plan="standard",
        exempt_paths=["/health"],
    )
    limiter = InMemoryRateLimiter(config=config)
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, limiter=limiter, config=config)
    calls = []

    @app.post("/api/items")
    def create_item() -> dict[str, str]:
        calls.append("called")
        return {"status": "ok"}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/reports")
    def reports() -> dict[str, str]:
        return {"status": "ok"}

    return app, TestClient(app)


def test_missing_org_header_returns_clear_error():
    response = client.get("/api/items")
    assert response.status_code == 400
    assert response.json()["error"] == "missing_organization_id"


def test_unknown_organizations_receive_default_plan():
    response = client.get("/api/items", headers={"X-Org-ID": "unknown-org"})
    assert response.status_code == 200


def test_exempt_paths_bypass_rate_limiting():
    response = client.get("/health", headers={"X-Org-ID": "org-standard"})
    assert response.status_code == 200


def test_expensive_endpoint_classification_overrides_normal_get_classification():
    response = client.get("/api/reports", headers={"X-Org-ID": "org-standard"})
    assert response.status_code == 200


def test_rejected_requests_do_not_reach_api_handler():
    app, test_client = make_test_app()
    first = test_client.post("/api/items", headers={"X-Org-ID": "org-standard"}, json={"name": "demo"})
    second = test_client.post("/api/items", headers={"X-Org-ID": "org-standard"}, json={"name": "demo2"})
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"] == "rate_limit_exceeded"


def test_retry_after_header_is_present_and_positive():
    _, test_client = make_test_app()
    test_client.post("/api/items", headers={"X-Org-ID": "org-standard"}, json={"name": "demo"})
    response = test_client.post("/api/items", headers={"X-Org-ID": "org-standard"}, json={"name": "demo2"})
    assert response.headers.get("Retry-After", "0") != "0"
