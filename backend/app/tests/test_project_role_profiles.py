from app.modules.iam.seed import PROFILE_MAP
from scripts.preview_project_handover_profiles import (
    CANDIDATE_PROFILE_CODES,
    permission_delta,
)


def test_project_role_profiles_are_seeded_without_company_wide_project_access():
    assert set(CANDIDATE_PROFILE_CODES) <= PROFILE_MAP.keys()
    for code in CANDIDATE_PROFILE_CODES:
        assert "project.manage" not in PROFILE_MAP[code]

    assert "project.manage.assigned" in PROFILE_MAP["PROJECT_MANAGER"]
    assert "project.assignment.respond" in PROFILE_MAP["IMPLEMENTATION_MANAGER"]
    assert "implementation.task.assign" in PROFILE_MAP["IMPLEMENTATION_TEAM_LEADER"]
    assert "implementation.task.worklog" in PROFILE_MAP["IMPLEMENTATION_ENGINEER"]
    assert "implementation.task.manage" not in PROFILE_MAP["IMPLEMENTATION_ENGINEER"]
    assert "implementation.task.execute" in PROFILE_MAP["IMPLEMENTATION_ENGINEER"]
    assert "handover.activate_support" not in PROFILE_MAP["SUPPORT_HANDOVER_REVIEWER"]


def test_profile_preview_reports_permission_deltas_without_applying_a_mapping():
    delta = permission_delta(
        {"project.manage", "project.portfolio.view"}, "PROJECT_MANAGER"
    )
    assert "project.manage" in delta["lost"]
    assert "project.manage.assigned" in delta["gained"]
    assert delta["retained"] == ["project.portfolio.view"]
