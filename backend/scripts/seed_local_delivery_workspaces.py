"""Seed only the local project delivery workspace profiles and grants."""

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.iam.models import Permission, Profile, ProfilePermission
from app.modules.iam.seed import NAMES, PROFILE_MAP

DELIVERY_PROFILES = {
    "PROJECT_MANAGER", "IMPLEMENTATION", "IMPLEMENTATION_MANAGER",
    "IMPLEMENTATION_TEAM_LEADER", "IMPLEMENTATION_ENGINEER", "SUPPORT_HANDOVER_REVIEWER",
}


def main() -> None:
    with SessionLocal() as db:
        url = db.get_bind().url
        if url.host not in {"localhost", "127.0.0.1", "::1"} or url.database != "MillensysSupportHub":
            raise SystemExit("Only local MillensysSupportHub is supported.")
        for code, permissions in PROFILE_MAP.items():
            grants = {value for value in permissions if value.startswith("workspace.")}
            if code in DELIVERY_PROFILES:
                grants.update(value for value in permissions if value.startswith("analytics."))
            if not grants and code not in DELIVERY_PROFILES:
                continue
            profile = db.scalar(select(Profile).where(Profile.code == code))
            if profile is None:
                if code not in DELIVERY_PROFILES:
                    continue
                profile = Profile(code=code, name=NAMES[code], profile_type="EMPLOYEE",
                                  is_active=True, is_system=True, default_dashboard_code="dashboard")
                db.add(profile)
                db.flush()
                grants = permissions
            existing = set(db.scalars(select(ProfilePermission.permission_id).where(
                ProfilePermission.profile_id == profile.id,
            )))
            for grant in sorted(grants):
                permission = db.scalar(select(Permission).where(Permission.code == grant))
                if permission is None:
                    permission = Permission(code=grant, module=grant.split(".")[0],
                                            description=grant.replace(".", " ").title(), is_active=True)
                    db.add(permission)
                    db.flush()
                if not permission.is_active:
                    raise SystemExit(f"Required permission is inactive: {grant}")
                if permission.id not in existing:
                    db.add(ProfilePermission(profile_id=profile.id, permission_id=permission.id))
        db.commit()
        print("Local workspace and analytics grants seeded. User assignments were unchanged.")


if __name__ == "__main__":
    main()
