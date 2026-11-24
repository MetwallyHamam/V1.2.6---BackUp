from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.iam.models import User
from app.modules.iam.seed import seed

engine = create_engine(
    "sqlite+pysqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
TEST_SETTINGS = Settings(
    app_env="test",
    secret_key="test-secret-key-with-more-than-thirty-two-characters",
    database_url="sqlite+pysqlite://",
    escalation_scheduler_enabled=False,
    maintenance_scheduler_enabled=False,
    password_reset_allowed_domains="",
)


@pytest.fixture(autouse=True)
def database(monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
    monkeypatch.setattr("app.modules.notifications.routes.SessionLocal", TestingSession)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    monkeypatch.setenv("DEV_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("DEV_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("DEV_ADMIN_PASSWORD", "DevelopmentPassword!123")
    get_settings.cache_clear()
    with TestingSession() as session:
        seed(session)
        admin = session.scalar(select(User).where(User.username == "admin"))
        admin.require_password_change = False
        session.commit()
        yield session
    get_settings.cache_clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    app = create_app(TEST_SETTINGS)

    def override_db() -> Generator[Session, None, None]:
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "admin", "password": "DevelopmentPassword!123"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
