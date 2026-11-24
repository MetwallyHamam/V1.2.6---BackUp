from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import Settings
from app.db.compatibility import (
    EXPECTED_DATABASE_REVISION,
    DatabaseCompatibility,
    check_database_compatibility,
)
from app.main import create_app


def test_compatibility_reports_missing_migration_history() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    result = check_database_compatibility(engine)
    assert result.compatible is False
    assert result.status == "MIGRATION_HISTORY_MISSING"


def test_compatibility_reports_exact_missing_schema_item() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(255))"))
        connection.execute(
            text("INSERT INTO alembic_version VALUES (:revision)"),
            {"revision": EXPECTED_DATABASE_REVISION},
        )
    result = check_database_compatibility(engine)
    assert result.status == "SCHEMA_INCOMPLETE"
    assert result.missing_table
    assert result.missing_columns == ()


def test_compatibility_rejects_outdated_revision() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(255))"))
        connection.execute(text("INSERT INTO alembic_version VALUES ('0049_dynamic_contract_sla')"))
    result = check_database_compatibility(engine)
    assert result.compatible is False
    assert result.status == "MIGRATION_REQUIRED"
    assert result.current_revision == "0049_dynamic_contract_sla"
    assert EXPECTED_DATABASE_REVISION == "0295_project_lifecycle"


def test_incompatible_database_blocks_business_routes_with_controlled_error() -> None:
    settings = Settings(app_env="test", _env_file=None)
    app = create_app(settings)
    with TestClient(app) as client:
        app.state.database_compatibility = DatabaseCompatibility(
            False, "MIGRATION_REQUIRED", "0049_dynamic_contract_sla"
        )
        response = client.post("/api/v1/auth/login", json={"login": "x", "password": "x"})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "DATABASE_MIGRATION_REQUIRED"
        health = client.get("/api/v1/health")
        assert health.status_code == 200
