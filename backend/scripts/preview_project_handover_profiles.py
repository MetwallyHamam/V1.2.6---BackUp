"""Print the current PROJECT_HANDOVER assignment inventory as read-only JSON."""

import json
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.db.session import SessionLocal
from app.modules.clients.models import SupportTeam, SupportTeamMember
from app.modules.iam.models import (
    Department,
    DepartmentMembership,
    Profile,
    User,
    UserProfile,
)
from app.modules.iam.seed import PROFILE_MAP
from app.modules.iam.service import effective_permissions

CANDIDATE_PROFILE_CODES = (
    "PROJECT_MANAGER",
    "IMPLEMENTATION_MANAGER",
    "IMPLEMENTATION_TEAM_LEADER",
    "IMPLEMENTATION_ENGINEER",
    "SUPPORT_HANDOVER_REVIEWER",
)


def permission_delta(current: set[str], proposed_profile: str) -> dict[str, list[str]]:
    proposed = PROFILE_MAP[proposed_profile]
    return {
        "gained": sorted(proposed - current),
        "lost": sorted(current - proposed),
        "retained": sorted(current & proposed),
    }


def preview(db: Session) -> dict[str, Any]:
    now = server_now()
    today = now.date()
    active_profiles = (
        select(UserProfile.user_id, Profile.code)
        .join(Profile, Profile.id == UserProfile.profile_id)
        .where(
            Profile.is_active.in_([True]),
            UserProfile.is_active.in_([True]),
            UserProfile.valid_from <= now,
            or_(UserProfile.valid_to.is_(None), UserProfile.valid_to > now),
        )
        .subquery()
    )
    holders = db.scalars(
        select(User)
        .join(active_profiles, active_profiles.c.user_id == User.id)
        .where(active_profiles.c.code == "PROJECT_HANDOVER", User.is_active.in_([True]))
        .order_by(User.id)
    ).all()
    rows = []
    for user in holders:
        departments = db.scalars(
            select(Department.code)
            .join(DepartmentMembership, DepartmentMembership.department_id == Department.id)
            .where(
                Department.is_active.in_([True]),
                DepartmentMembership.user_id == user.id,
                DepartmentMembership.effective_from <= today,
                or_(
                    DepartmentMembership.effective_until.is_(None),
                    DepartmentMembership.effective_until >= today,
                ),
            )
        )
        teams = db.scalars(
            select(SupportTeam)
            .outerjoin(SupportTeamMember, SupportTeamMember.team_id == SupportTeam.id)
            .where(
                SupportTeam.is_active.in_([True]),
                or_(SupportTeamMember.user_id == user.id, SupportTeam.leader_user_id == user.id),
            )
            .order_by(SupportTeam.code)
        ).unique()
        permissions = set(effective_permissions(db, user, now).permissions)
        rows.append(
            {
                "user_id": user.id,
                "primary_department_id": user.department_id,
                "active_department_codes": sorted(set(departments)),
                "active_teams": [
                    {"code": team.code, "is_leader": team.leader_user_id == user.id}
                    for team in teams
                ],
                "active_profiles": sorted(
                    db.scalars(
                        select(active_profiles.c.code).where(active_profiles.c.user_id == user.id)
                    )
                ),
                "effective_permissions": sorted(permissions),
                "has_company_wide_project_access": "project.manage" in permissions,
                "proposed_profiles": [],
                "candidate_profile_deltas": {
                    code: permission_delta(permissions, code)
                    for code in CANDIDATE_PROFILE_CODES
                },
                "mapping_status": "REQUIRES_REVIEW",
            }
        )
    return {"as_of": now.isoformat(), "holder_count": len(rows), "holders": rows}


if __name__ == "__main__":
    with SessionLocal(autoflush=False) as session:
        print(json.dumps(preview(session), indent=2))
