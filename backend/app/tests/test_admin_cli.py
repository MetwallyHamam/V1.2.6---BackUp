from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.iam.admin_cli import recover_administrator
from app.modules.iam.models import Profile, User, UserProfile
from app.modules.iam.security import verify_password


def test_recover_existing_administrator(monkeypatch, database: Session) -> None:
    answers = iter(["RecoveredPassword!456", "RecoveredPassword!456"])
    monkeypatch.setattr("app.modules.iam.admin_cli.getpass.getpass", lambda _: next(answers))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    admin.failed_login_count = 5
    admin.is_active = False
    database.commit()

    message = recover_administrator(database, "admin")

    database.refresh(admin)
    assert "recovered" in message
    assert admin.is_active is True
    assert admin.failed_login_count == 0
    assert admin.locked_until is None
    assert admin.require_password_change is True
    assert verify_password("RecoveredPassword!456", admin.password_hash)


def test_create_missing_administrator(monkeypatch, database: Session) -> None:
    answers = iter(["NewAdministrator!456", "NewAdministrator!456"])
    monkeypatch.setattr("app.modules.iam.admin_cli.getpass.getpass", lambda _: next(answers))

    message = recover_administrator(database, "recovery.admin", "recovery@example.com")

    user = database.scalar(select(User).where(User.username == "recovery.admin"))
    assert user is not None
    profile_code = database.scalar(
        select(Profile.code)
        .join(UserProfile, UserProfile.profile_id == Profile.id)
        .where(UserProfile.user_id == user.id)
    )
    assert "created" in message
    assert profile_code == "ADMINISTRATOR"
    assert verify_password("NewAdministrator!456", user.password_hash)
