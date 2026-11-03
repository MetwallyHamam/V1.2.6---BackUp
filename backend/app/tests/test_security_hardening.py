import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


def test_api_responses_include_security_headers(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_untrusted_host_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Host": "malicious.example"})
    assert response.status_code == 400


def test_invalid_correlation_id_is_replaced(client: TestClient) -> None:
    response = client.get(
        "/api/v1/health", headers={"X-Correlation-ID": "not-a-valid-correlation-id"}
    )
    assert response.status_code == 200
    correlation = response.headers["x-correlation-id"]
    assert str(uuid.UUID(correlation)) == correlation


def test_oversized_request_is_rejected_before_handler(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        headers={"Content-Length": "10485761"},
        content=b"{}",
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_production_rejects_default_secret_and_sqlite() -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY must be replaced"):
        Settings(app_env="production", _env_file=None)


def test_production_rejects_http_frontend_origin() -> None:
    with pytest.raises(ValidationError, match="FRONTEND_ORIGIN must contain only HTTPS"):
        Settings(
            app_env="production",
            secret_key="a-secure-production-secret-with-more-than-32-characters",
            database_url="mssql+pymssql://user:password@database/support",
            frontend_origin="http://support.example.com",
            _env_file=None,
        )


def test_production_api_rejects_plain_http() -> None:
    settings = Settings(
        app_env="production",
        secret_key="a-secure-production-secret-with-more-than-32-characters",
        database_url="mssql+pymssql://user:password@database/support",
        frontend_origin="https://support.example.com",
        escalation_scheduler_enabled=False,
        dev_admin_username="",
        dev_admin_email="",
        dev_admin_password="",
        database_compatibility_check_enabled=False,
        _env_file=None,
    )
    with TestClient(create_app(settings), base_url="http://support.example.com") as test_client:
        response = test_client.get("/api/v1/health")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "HTTPS_REQUIRED"
