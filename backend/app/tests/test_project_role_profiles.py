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


def test_workspace_grants_are_separate_from_workflow_permissions():
    project = PROFILE_MAP["PROJECT_MANAGER"]
    assert {"workspace.project_management.access", "project.create", "implementation.task.view"} <= project
    assert "workspace.implementation.access" not in project
    for code in ("IMPLEMENTATION_MANAGER", "IMPLEMENTATION_TEAM_LEADER", "IMPLEMENTATION_ENGINEER"):
        assert "workspace.implementation.access" in PROFILE_MAP[code]
        assert "workspace.project_management.access" not in PROFILE_MAP[code]
    assert "workspace.support.access" in PROFILE_MAP["L1_SUPPORT"]


def test_profile_preview_reports_permission_deltas_without_applying_a_mapping():
    delta = permission_delta(
        {"project.manage", "project.portfolio.view"}, "PROJECT_MANAGER"
    )
    assert "project.manage" in delta["lost"]
    assert "project.manage.assigned" in delta["gained"]
    assert delta["retained"] == ["project.portfolio.view"]
