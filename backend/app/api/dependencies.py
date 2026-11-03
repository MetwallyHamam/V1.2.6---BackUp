from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    PasswordChangeRequiredError,
)
from app.db.session import get_db
from app.modules.iam.models import User
from app.modules.iam.security import decode_access_token
from app.modules.iam.service import effective_permissions

bearer = HTTPBearer(auto_error=False)


def authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if not credentials:
        raise AuthenticationError("AUTHENTICATION_REQUIRED", "Authentication is required.")
    user_id = decode_access_token(credentials.credentials, settings)
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise AuthenticationError("ACCOUNT_INACTIVE", "The account is inactive.")
    return user


def current_user(user: User = Depends(authenticated_user)) -> User:
    if user.require_password_change:
        raise PasswordChangeRequiredError()
    return user


def require_permission(code: str) -> Callable[..., User]:
    def dependency(
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if code not in effective_permissions(db, user).permissions:
            raise AuthorizationError(details={"required_permission": code})
        return user

    return dependency


def require_any_permission(*codes: str) -> Callable[..., User]:
    required = set(codes)

    def dependency(
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if required.isdisjoint(effective_permissions(db, user).permissions):
            raise AuthorizationError(details={"required_permissions": sorted(required)})
        return user

    return dependency
