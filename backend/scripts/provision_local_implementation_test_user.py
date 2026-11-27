"""Provision the agreed Implementation workflow test user on local SQL Server."""

import os

from sqlalchemy import func, select, true, update

from app.db.session import SessionLocal
from app.modules.iam.models import (
    Department,
    Permission,
    Profile,
    ProfilePermission,
    User,
    UserProfile,
)
from app.modules.iam.schemas import UserCreate
from app.modules.iam.seed import NAMES, PROFILE_MAP
from app.modules.iam.service import create_user, effective_permissions


def main() -> None:
    password = os.environ.pop("SUPPORTHUB_LOCAL_IMP_TEST_PASSWORD", "")
    if len(password) < 12:
        raise SystemExit("Supply the local test password through the process environment.")
    with SessionLocal() as db:
        url = db.get_bind().url
        if url.host not in {"127.0.0.1", "localhost", "::1"} or url.database != "MillensysSupportHub":
            raise SystemExit("This command may only target local MillensysSupportHub.")
        if db.scalar(select(User.id).where(User.username_normalized == "impuser")):
            raise SystemExit("impuser already exists. No account was changed.")
        department = db.scalar(select(Department).where(
            Department.name == "Implementation", Department.is_active == true(),
        ))
        admin = db.scalar(select(User).where(User.username_normalized == "admin", User.is_active == true()))
        if department is None or admin is None or "user.manage" not in effective_permissions(db, admin).permissions:
            raise SystemExit("The local Implementation department and provisioning administrator are required.")
        profile_ids = []
        for code in ("IMPLEMENTATION",):
            profile = db.scalar(select(Profile).where(Profile.code == code))
            if profile is None:
                profile = Profile(code=code, name=NAMES[code], profile_type="EMPLOYEE",
                                  is_system=True, is_active=True, default_dashboard_code="dashboard")
                db.add(profile)
                db.flush()
            elif not profile.is_system or not profile.is_active or profile.profile_type != "EMPLOYEE":
                raise SystemExit(f"Unexpected existing profile configuration for {code}.")
            existing = set(db.scalars(select(ProfilePermission.permission_id).where(
                ProfilePermission.profile_id == profile.id,
            )))
            for grant in sorted(PROFILE_MAP[code]):
                permission = db.scalar(select(Permission).where(Permission.code == grant))
                if permission is None:
                    permission = Permission(code=grant, module=grant.split(".")[0],
                                            description=grant.replace(".", " ").title(), is_active=True)
                    db.add(permission)
                    db.flush()
                if permission.id not in existing:
                    db.add(ProfilePermission(profile_id=profile.id, permission_id=permission.id))
            profile_ids.append(profile.id)
        user = create_user(db, UserCreate(
            full_name="Implementation Workflow Test",
            username="impuser",
            email="impuser@example.com",
            password=password,
            department_id=department.id,
            primary_profile_id=profile_ids[0],
            additional_profile_ids=profile_ids[1:],
            require_password_change=False,
            participates_in_shifts=False,
            participates_in_operations=False,
        ), admin.id)
        db.connection().execute(update(UserProfile).where(UserProfile.user_id == user.id).values(
            valid_from=func.sysutcdatetime(),
        ))
        db.commit()
        print(f"Created {user.username} (ID {user.id}) in {department.name}.")


if __name__ == "__main__":
    main()
