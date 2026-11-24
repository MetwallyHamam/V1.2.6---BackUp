"""Preview or consolidate the local Project Manager duplicate."""

import argparse

from sqlalchemy import column, inspect, select, table, true, update
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.modules.iam.models import Permission, Profile, ProfilePermission, UserProfile
from app.modules.iam.seed import PROFILE_MAP

CANONICAL = "PROJECT_MANAGER"
DUPLICATE = "PROJECT_MANAGER_LOCAL_TEST"


def consolidate(db: Session, *, apply: bool) -> None:
    profiles = {
        row.code: row
        for row in db.scalars(select(Profile).where(Profile.code.in_((CANONICAL, DUPLICATE))))
    }
    legacy = profiles.get(DUPLICATE)
    if legacy is None:
        print(f"No {DUPLICATE} profile found.")
        return
    target = profiles.get(CANONICAL)
    if target is not None and (not target.is_active or not target.is_system):
        raise SystemExit(f"{CANONICAL} must be an active system profile.")

    codes = PROFILE_MAP[CANONICAL]
    grants = {
        row.id: row.code
        for row in db.scalars(
            select(Permission).where(Permission.code.in_(codes), Permission.is_active == true())
        )
    }
    if set(grants.values()) != codes:
        raise SystemExit(
            f"Missing active permissions: {', '.join(sorted(codes - set(grants.values())))}"
        )

    assignments = select(UserProfile.user_id).where(UserProfile.profile_id == legacy.id)
    overlap = (
        db.scalar(
            select(UserProfile.id)
            .where(UserProfile.profile_id == target.id, UserProfile.user_id.in_(assignments))
            .limit(1)
        )
        if target is not None
        else False
    )
    if overlap:
        raise SystemExit("A user has both profiles. Resolve overlapping assignment dates first.")

    connection = db.connection()
    inspector = inspect(connection)
    for table_name, column_name in (
        ("dashboard_profile_access", "profile_id"),
        ("dashboard_assignments", "profile_id"),
        ("internal_operation_types", "approver_profile_id"),
    ):
        if inspector.has_table(table_name):
            reference = table(table_name, column(column_name)).c[column_name]
            if db.scalar(select(reference).where(reference == legacy.id).limit(1)) is not None:
                raise SystemExit(f"Resolve references to the duplicate in {table_name}.{column_name}.")

    source_grants = {grant.permission_id for grant in legacy.permissions}
    target_grants = set(grants)
    existing_grants = {grant.permission_id for grant in target.permissions} if target else set()
    if existing_grants - target_grants:
        raise SystemExit(f"{CANONICAL} has custom grants. Review them before consolidation.")
    print(f"Assignments to move: {len(db.scalars(assignments).all())}")
    print(f"Profile grants added: {len(target_grants - source_grants)}")
    withdrawn = db.scalars(select(Permission.code).where(
        Permission.id.in_(source_grants - target_grants)
    )).all()
    print(f"Profile grants withdrawn: {', '.join(sorted(withdrawn)) or 'none'}")
    if apply:
        if target is None:
            target = Profile(
                code=CANONICAL,
                name="Project Manager",
                profile_type="EMPLOYEE",
                is_system=True,
                default_dashboard_code="dashboard",
            )
            db.add(target)
            db.flush()
        db.add_all(
            ProfilePermission(profile_id=target.id, permission_id=permission_id)
            for permission_id in target_grants - existing_grants
        )
        db.execute(
            update(UserProfile)
            .where(UserProfile.profile_id == legacy.id)
            .values(profile_id=target.id)
        )
        db.delete(legacy)
        db.commit()
        print(f"Consolidated {DUPLICATE} into {CANONICAL}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="Move assignments and delete duplicate"
    )
    args = parser.parse_args()
    with SessionLocal(autoflush=False) as session:
        url = session.get_bind().url
        print(f"Database: {url.host or '(local file)'}/{url.database}")
        if args.apply and (
            url.host not in {"localhost", "127.0.0.1", "::1"}
            or url.database != "MillensysSupportHub"
        ):
            raise SystemExit("Apply is restricted to the designated local testing database.")
        consolidate(session, apply=args.apply)
