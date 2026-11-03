import getpass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.iam.models import Profile, User, UserProfile
from app.modules.iam.security import hash_password
from app.modules.iam.service import normalize


def recover_administrator(db: Session, login: str, email: str | None = None) -> str:
    password = getpass.getpass("New administrator password: ")
    confirmation = getpass.getpass("Repeat administrator password: ")
    if password != confirmation:
        raise ValueError("Passwords do not match.")
    if len(password) < 12:
        raise ValueError("The password must contain at least 12 characters.")

    normalized = normalize(login)
    user = db.scalar(
        select(User).where(
            or_(User.username_normalized == normalized, User.email_normalized == normalized)
        )
    )
    if user:
        user.password_hash = hash_password(password)
        user.failed_login_count = 0
        user.locked_until = None
        user.is_active = True
        user.require_password_change = True
        db.commit()
        return f"Administrator login recovered for '{user.username}'."

    if not email:
        raise ValueError("The account does not exist; provide --email to create it.")
    profile = db.scalar(select(Profile).where(Profile.code == "ADMINISTRATOR"))
    if not profile:
        raise RuntimeError("Administrator profile is missing. Run seed before recovering access.")
    normalized_email = normalize(email)
    if db.scalar(select(User.id).where(User.email_normalized == normalized_email)):
        raise ValueError("That email belongs to a different account.")
    user = User(
        full_name="System Administrator",
        username=login,
        username_normalized=normalized,
        email=email,
        email_normalized=normalized_email,
        password_hash=hash_password(password),
        user_type="EMPLOYEE",
        is_active=True,
        require_password_change=True,
    )
    db.add(user)
    db.flush()
    db.add(
        UserProfile(
            user_id=user.id,
            profile_id=profile.id,
            is_primary=True,
            assigned_by_user_id=user.id,
            assignment_reason="Administrative access recovery",
        )
    )
    db.commit()
    return f"Administrator '{user.username}' created. A password change is required at login."
