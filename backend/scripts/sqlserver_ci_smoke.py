"""Exercise migration-sensitive report paths against the configured SQL Server."""

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine
from app.main import create_app


def main() -> None:
    settings = get_settings()
    if engine.dialect.name != "mssql":
        raise RuntimeError("SQL Server smoke test requires an mssql DATABASE_URL")

    with engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
        if revision != "0057_sla_clock_lifecycle":
            raise RuntimeError(f"Unexpected database revision: {revision}")

    with TestClient(create_app(settings)) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"login": "ci-admin", "password": "SupportHub-CI-Password!2026"},
        )
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        hr_export = client.get("/api/v1/reports/agent-kpis.xlsx", headers=headers)
        hr_export.raise_for_status()
        if not hr_export.headers.get("content-type", "").startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ):
            raise RuntimeError("HR KPI export did not return an XLSX workbook")

        ticket_export = client.get("/api/v1/reports/tickets.csv", headers=headers)
        ticket_export.raise_for_status()
        if not ticket_export.headers.get("content-type", "").startswith("text/csv"):
            raise RuntimeError("Ticket export did not return CSV content")

    print("SQL Server migration and export smoke checks passed.")


if __name__ == "__main__":
    main()
