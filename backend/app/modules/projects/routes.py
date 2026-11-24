import json
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select, true, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_any_permission, require_permission
from app.core.clock import server_now
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import (
    Account,
    Branch,
    Client,
    Organization,
    Product,
    ProductModule,
    SupportTeam,
    SupportTeamMember,
)
from app.modules.contracts.service import evaluate_entitlement
from app.modules.iam.models import AuditLog, Department, User
from app.modules.iam.service import effective_permissions
from app.modules.projects.access import authorized_project_ids, require_project_access
from app.modules.projects.lifecycle import transition_project
from app.modules.projects.models import (
    CompanyProject,
    ProjectAssignmentRequest,
    ProjectBranchScope,
    ProjectDepartment,
    ProjectEvidence,
    ProjectMilestone,
    ProjectModuleScope,
    ProjectPhase,
    ProjectPhaseModuleScope,
    ProjectPhaseProductScope,
    ProjectProductScope,
    ProjectStatusTransition,
    ProjectTask,
    ProjectTaskAssignee,
    ProjectTaskDependency,
    ProjectTeam,
    ProjectTemplate,
    ProjectTemplateVersion,
)
from app.modules.projects.schemas import (
    AssignmentRequestWrite,
    AssignmentResponseWrite,
    MilestoneScheduleWrite,
    MilestoneWrite,
    PhaseWrite,
    ProjectCoverageCheck,
    ProjectCreate,
    ProjectHoldWrite,
    ProjectRead,
    ProjectResumeWrite,
    ProjectTransitionWrite,
    ProjectUpdate,
    ProjectWizardCreate,
    ProjectWizardResult,
)

router = APIRouter(prefix="/projects", tags=["project portfolio"])


def _row_values(row: Any) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def _project_read(db: Session, row: CompanyProject) -> ProjectRead:
    branch_ids = list(
        db.scalars(
            select(ProjectBranchScope.branch_id).where(ProjectBranchScope.project_id == row.id)
        )
    )
    return ProjectRead.model_validate(row).model_copy(update={"branch_ids": branch_ids})


def _audit(
    db: Session, actor: User, project_id: int, action: str, values: dict[str, object]
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="company_project",
            entity_id=str(project_id),
            action=action,
            new_values_json=json.dumps(values, default=str),
        )
    )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "PROJECT_CONFLICT",
            "Project number or related project record conflicts with existing data.",
        ) from exc


def _get_project(db: Session, project_id: int) -> CompanyProject:
    row = db.get(CompanyProject, project_id)
    if not row:
        raise NotFoundError("Project does not exist.")
    return row


def _validate_scope(db: Session, data: ProjectCreate) -> None:
    account = db.get(Account, data.account_id)
    organization = db.get(Organization, data.organization_id)
    client = db.get(Client, data.client_id)
    if not account or not organization or not client:
        raise NotFoundError("Selected Account, Organization, or Client does not exist.")
    if organization.account_id != account.id or client.organization_id != organization.id:
        raise ConflictError(
            "INVALID_PROJECT_SCOPE", "Account, Organization, and Client must form one hierarchy."
        )
    branches = (
        list(db.scalars(select(Branch).where(Branch.id.in_(set(data.branch_ids)))))
        if data.branch_ids
        else []
    )
    if len(branches) != len(set(data.branch_ids)) or any(
        row.client_id != client.id for row in branches
    ):
        raise ConflictError(
            "INVALID_PROJECT_BRANCH_SCOPE",
            "Every selected Branch must belong to the selected Client.",
        )
    if not db.get(Department, data.owning_department_id) or not db.get(
        User, data.project_manager_user_id
    ):
        raise ConflictError(
            "INVALID_PROJECT_OWNER", "Select an existing owning department and project manager."
        )


@router.get("", response_model=list[ProjectRead])
def list_projects(
    status_filter: str | None = Query(default=None, alias="status"),
    department_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.portfolio.view")),
) -> list[ProjectRead]:
    statement = select(CompanyProject).where(
        CompanyProject.id.in_(authorized_project_ids(db, actor))
    )
    if status_filter:
        statement = statement.where(CompanyProject.status == status_filter.upper())
    if department_id:
        statement = statement.where(CompanyProject.owning_department_id == department_id)
    return [
        _project_read(db, row)
        for row in db.scalars(statement.order_by(CompanyProject.updated_at.desc()))
    ]


@router.get("/portfolio-summary")
def portfolio_summary(
    db: Session = Depends(get_db), actor: User = Depends(require_permission("project.portfolio.view"))
) -> dict[str, int]:
    visible_ids = authorized_project_ids(db, actor)
    total = (
        db.scalar(
            select(func.count())
            .select_from(CompanyProject)
            .where(CompanyProject.id.in_(visible_ids))
        )
        or 0
    )
    at_risk = (
        db.scalar(
            select(func.count())
            .select_from(CompanyProject)
            .where(
                CompanyProject.health.in_(["AT_RISK", "CRITICAL"]),
                CompanyProject.id.in_(visible_ids),
            )
        )
        or 0
    )
    pending = (
        db.scalar(
            select(func.count())
            .select_from(ProjectAssignmentRequest)
            .where(
                ProjectAssignmentRequest.status == "PENDING",
                ProjectAssignmentRequest.project_id.in_(visible_ids),
            )
        )
        or 0
    )
    return {"total": total, "at_risk": at_risk, "pending_assignment_requests": pending}


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.create")),
) -> ProjectRead:
    _validate_scope(db, data)
    values = data.model_dump(exclude={"branch_ids"})
    values["project_number"] = data.project_number.strip().upper()
    values["name"] = data.name.strip()
    row = CompanyProject(
        **values,
        primary_branch_id=data.branch_ids[0] if data.branch_ids else None,
        created_by_user_id=actor.id,
    )
    db.add(row)
    db.flush()
    db.add(
        ProjectDepartment(
            project_id=row.id,
            department_id=data.owning_department_id,
            role="PROJECT_MANAGEMENT",
            is_primary=True,
        )
    )
    for branch_id in set(data.branch_ids):
        db.add(ProjectBranchScope(project_id=row.id, branch_id=branch_id))
    _audit(
        db,
        actor,
        row.id,
        "project.created",
        {"project_number": row.project_number, "branch_ids": data.branch_ids},
    )
    _commit(db)
    db.refresh(row)
    return _project_read(db, row)


@router.post("/wizard/coverage", dependencies=[Depends(require_permission("client.view"))])
def wizard_coverage(
    data: ProjectCoverageCheck,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("project.create")),
) -> list[dict[str, Any]]:
    if db.get(Client, data.client_id) is None:
        raise NotFoundError("Client does not exist.")
    products = db.scalars(select(Product).where(Product.id.in_(set(data.product_ids)))).all()
    modules = db.scalars(
        select(ProductModule).where(ProductModule.id.in_(set(data.module_ids)))
    ).all()
    catalog: list[tuple[int, int | None, str]] = [
        (product.id, None, product.name) for product in products
    ]
    catalog.extend((module.product_id, module.id, module.name) for module in modules)
    results = []
    for product_id, module_id, name in catalog:
        coverage, _contract, _reason = evaluate_entitlement(
            db, client_id=data.client_id, product_id=product_id, product_module_id=module_id
        )
        results.append({"name": name, "kind": "Module" if module_id else "Product", "status": coverage})
    return results


@router.post("/wizard", response_model=ProjectWizardResult, status_code=status.HTTP_201_CREATED)
def create_project_from_wizard(
    data: ProjectWizardCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.create")),
) -> ProjectWizardResult:
    source_version = None
    if data.source_template_version_id is not None:
        source_version = db.scalar(
            select(ProjectTemplateVersion)
            .join(ProjectTemplate, ProjectTemplate.id == ProjectTemplateVersion.template_id)
            .where(
                ProjectTemplateVersion.id == data.source_template_version_id,
                ProjectTemplateVersion.published_at.is_not(None),
                ProjectTemplate.owner_user_id == actor.id,
            )
        )
        if source_version is None:
            raise NotFoundError("Published project template version does not exist.")
    _validate_scope(
        db,
        ProjectCreate(
            project_number=data.project_number,
            name=data.name,
            description=data.description,
            account_id=data.account_id,
            organization_id=data.organization_id,
            client_id=data.client_id,
            branch_ids=data.branch_ids,
            owning_department_id=data.owning_department_id,
            project_manager_user_id=data.project_manager_user_id,
            priority=data.priority,
            planned_start_date=data.planned_start_date,
            planned_end_date=data.planned_end_date,
        ),
    )
    department = db.get(Department, data.requested_department_id)
    intake_owner = db.get(User, data.intake_owner_user_id)
    if not department or not department.is_active:
        raise ConflictError(
            "INVALID_IMPLEMENTATION_DEPARTMENT", "Select an active delivery department."
        )
    if not intake_owner or not intake_owner.is_active:
        raise ConflictError("INVALID_INTAKE_OWNER", "Select an active intake owner.")
    team = db.get(SupportTeam, data.requested_team_id) if data.requested_team_id else None
    if team and (not team.is_active or team.department_id != department.id):
        raise ConflictError(
            "INVALID_PROJECT_TEAM", "The selected team must be active in the requested department."
        )
    project_products = {
        x.id: x for x in db.scalars(select(Product).where(Product.id.in_(set(data.product_ids))))
    }
    if len(project_products) != len(set(data.product_ids)):
        raise NotFoundError("One or more selected products do not exist.")
    project_modules = {
        x.id: x
        for x in db.scalars(
            select(ProductModule).where(ProductModule.id.in_(set(data.module_ids or [-1])))
        )
    }
    if len(project_modules) != len(set(data.module_ids)) or any(
        x.product_id not in project_products for x in project_modules.values()
    ):
        raise ConflictError(
            "INVALID_PROJECT_MODULE", "Every module must belong to a selected product."
        )
    all_user_ids = {data.project_manager_user_id, data.intake_owner_user_id}
    for phase_input in data.phases:
        for task_input in phase_input.tasks:
            all_user_ids.add(task_input.owner_user_id)
            all_user_ids.update(task_input.assignee_user_ids)
    active_users = set(
        db.scalars(select(User.id).where(User.id.in_(all_user_ids), User.is_active == true()))
    )
    if active_users != all_user_ids:
        raise NotFoundError("Every project and task owner must be an active user.")
    if team:
        team_users = set(
            db.scalars(
                select(SupportTeamMember.user_id).where(SupportTeamMember.team_id == team.id)
            )
        )
        if team.leader_user_id:
            team_users.add(team.leader_user_id)
        task_users = all_user_ids - {data.project_manager_user_id}
        if not task_users.issubset(team_users):
            raise ConflictError(
                "ENGINEER_OUTSIDE_TEAM",
                "Task assignees and intake owner must belong to the selected team.",
            )

    row = CompanyProject(
        project_number=data.project_number.strip().upper(),
        name=data.name.strip(),
        description=data.description,
        account_id=data.account_id,
        organization_id=data.organization_id,
        client_id=data.client_id,
        primary_branch_id=data.branch_ids[0] if data.branch_ids else None,
        owning_department_id=data.owning_department_id,
        project_manager_user_id=data.project_manager_user_id,
        intake_owner_user_id=data.intake_owner_user_id,
        status="AWAITING_IMPLEMENTATION_ACCEPTANCE" if data.publish else "DRAFT",
        priority=data.priority,
        planned_start_date=data.planned_start_date,
        planned_end_date=data.planned_end_date,
        published_at=server_now() if data.publish else None,
        published_by_user_id=actor.id if data.publish else None,
        created_by_user_id=actor.id,
    )
    db.add(row)
    db.flush()
    db.add(
        ProjectDepartment(
            project_id=row.id,
            department_id=data.owning_department_id,
            role="PROJECT_MANAGEMENT",
            is_primary=True,
        )
    )
    db.add_all(ProjectBranchScope(project_id=row.id, branch_id=x) for x in set(data.branch_ids))
    db.add_all(ProjectProductScope(project_id=row.id, product_id=x) for x in set(data.product_ids))
    db.add_all(
        ProjectModuleScope(project_id=row.id, product_module_id=x) for x in set(data.module_ids)
    )
    task_count = 0
    for sequence, phase_data in enumerate(data.phases, 1):
        phase = ProjectPhase(
            project_id=row.id,
            name=phase_data.name,
            sequence=sequence,
            planned_start_date=phase_data.planned_start_at.date(),
            planned_end_date=phase_data.planned_end_at.date(),
            planned_start_at=phase_data.planned_start_at,
            planned_end_at=phase_data.planned_end_at,
        )
        db.add(phase)
        db.flush()
        db.add_all(
            ProjectPhaseProductScope(phase_id=phase.id, product_id=x)
            for x in set(phase_data.product_ids)
        )
        db.add_all(
            ProjectPhaseModuleScope(phase_id=phase.id, product_module_id=x)
            for x in set(phase_data.module_ids)
        )
        for task_data in phase_data.tasks:
            task = ProjectTask(
                project_id=row.id,
                phase_id=phase.id,
                product_id=task_data.product_id,
                product_module_id=task_data.product_module_id,
                task_number=task_data.task_number.strip().upper(),
                title=task_data.title.strip(),
                description=task_data.description,
                classification="PLANNED",
                status="BACKLOG",
                priority=task_data.priority,
                owner_user_id=task_data.owner_user_id,
                planned_start_date=task_data.planned_start_at.date(),
                planned_end_date=task_data.planned_end_at.date(),
                planned_start_at=task_data.planned_start_at,
                planned_end_at=task_data.planned_end_at,
                estimate_minutes=task_data.estimate_minutes,
                created_by_user_id=actor.id,
            )
            db.add(task)
            db.flush()
            assignees = set(task_data.assignee_user_ids) | {task_data.owner_user_id}
            db.add_all(
                ProjectTaskAssignee(
                    task_id=task.id,
                    user_id=x,
                    allocation_percent=100,
                    planned_minutes=task_data.estimate_minutes,
                    is_accountable=x == task_data.owner_user_id,
                )
                for x in assignees
            )
            task_count += 1
    task_ids = dict(db.execute(
        select(ProjectTask.task_number, ProjectTask.id).where(ProjectTask.project_id == row.id)
    ).tuples().all())
    db.add_all(
        ProjectTaskDependency(
            task_id=task_ids[task.task_number.strip().upper()],
            depends_on_task_id=task_ids[predecessor],
        )
        for phase in data.phases
        for task in phase.tasks
        for predecessor in {value.strip().upper() for value in task.predecessor_numbers}
    )
    for document in data.documents:
        db.add(
            ProjectEvidence(
                project_id=row.id,
                evidence_type=document.document_type,
                title=document.title,
                reference_url=document.reference_url,
                notes=document.notes,
                visibility=document.visibility,
                created_by_user_id=actor.id,
            )
        )
    assignment_request_id = None
    if data.publish:
        request = ProjectAssignmentRequest(
            project_id=row.id,
            requested_department_id=data.requested_department_id,
            requested_team_id=data.requested_team_id,
            requested_start_date=data.planned_start_date,
            requested_end_date=data.planned_end_date,
            capability_notes=data.capability_notes,
            requested_by_user_id=actor.id,
        )
        db.add(request)
        db.flush()
        assignment_request_id = request.id
    _audit(
        db,
        actor,
        row.id,
        "project.wizard_published" if data.publish else "project.wizard_draft_saved",
        {
            "phase_count": len(data.phases),
            "task_count": task_count,
            "product_ids": data.product_ids,
            "module_ids": data.module_ids,
            "source_template_version_id": source_version.id if source_version else None,
        },
    )
    _commit(db)
    return ProjectWizardResult(
        project_id=row.id,
        status=row.status,
        phase_count=len(data.phases),
        task_count=task_count,
        assignment_request_id=assignment_request_id,
    )


@router.get("/options")
def project_options(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("project.portfolio.view")),
) -> dict[str, list[dict[str, Any]]]:
    return {
        "accounts": [
            {"id": x.id, "name": x.name}
            for x in db.scalars(
                select(Account).where(Account.is_active == true()).order_by(Account.name)
            )
        ],
        "organizations": [
            {"id": x.id, "account_id": x.account_id, "name": x.name}
            for x in db.scalars(
                select(Organization)
                .where(Organization.is_active == true())
                .order_by(Organization.name)
            )
        ],
        "clients": [
            {"id": x.id, "organization_id": x.organization_id, "name": x.name}
            for x in db.scalars(
                select(Client).where(Client.is_active == true()).order_by(Client.name)
            )
        ],
        "departments": [
            {"id": x.id, "name": x.name}
            for x in db.scalars(
                select(Department).where(Department.is_active == true()).order_by(Department.name)
            )
        ],
        "managers": [
            {"id": x.id, "name": x.full_name}
            for x in db.scalars(
                select(User).where(User.is_active == true()).order_by(User.full_name)
            )
        ],
        "products": [
            {"id": x.id, "name": x.name}
            for x in db.scalars(
                select(Product).where(Product.is_active == true()).order_by(Product.name)
            )
        ],
        "modules": [
            {"id": x.id, "product_id": x.product_id, "name": x.name}
            for x in db.scalars(
                select(ProductModule)
                .where(ProductModule.is_active == true())
                .order_by(ProductModule.name)
            )
        ],
        "teams": [
            {
                "id": x.id,
                "department_id": x.department_id,
                "name": x.name,
                "leader_user_id": x.leader_user_id,
                "member_user_ids": x.member_user_ids,
            }
            for x in db.scalars(
                select(SupportTeam)
                .where(SupportTeam.is_active == true())
                .order_by(SupportTeam.name)
            )
        ],
    }


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.portfolio.view")),
) -> ProjectRead:
    return _project_read(db, require_project_access(db, actor, project_id))


def require_project_manager(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_any_permission("project.manage", "project.manage.assigned")),
) -> User:
    project = _get_project(db, project_id)
    if (
        project.project_manager_user_id != actor.id
        and "project.manage" not in effective_permissions(db, actor).permissions
    ):
        raise NotFoundError("Project does not exist.")
    return actor


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_project_manager),
) -> ProjectRead:
    row = _get_project(db, project_id)
    changes = data.model_dump(exclude_unset=True)
    if (
        changes.get("planned_start_date")
        and changes.get("planned_end_date")
        and changes["planned_end_date"] < changes["planned_start_date"]
    ):
        raise ConflictError(
            "INVALID_PROJECT_DATES", "Planned end date cannot precede planned start date."
        )
    for key, value in changes.items():
        setattr(row, key, value)
    _audit(db, actor, row.id, "project.updated", changes)
    _commit(db)
    db.refresh(row)
    return _project_read(db, row)


@router.post("/{project_id}/transition", response_model=ProjectRead)
def transition_project_status(
    project_id: int,
    data: ProjectTransitionWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.manage")),
) -> ProjectRead:
    row = require_project_access(db, actor, project_id)
    if row.row_version != data.expected_version:
        raise ConflictError(
            "PROJECT_VERSION_CONFLICT",
            "This project changed since it was opened. Refresh and try again.",
        )
    transition_project(
        db,
        row,
        actor,
        data.target_status,
        reason=data.reason,
        source="PROJECT_COMMAND",
    )
    _audit(
        db,
        actor,
        row.id,
        "project.status.transitioned",
        {"to_status": data.target_status.upper(), "reason": data.reason},
    )
    _commit(db)
    db.refresh(row)
    return _project_read(db, row)


@router.post("/{project_id}/hold", response_model=ProjectRead)
def hold_project(
    project_id: int,
    data: ProjectHoldWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_project_manager),
) -> ProjectRead:
    row = require_project_access(db, actor, project_id)
    if row.row_version != data.expected_version:
        raise ConflictError(
            "PROJECT_VERSION_CONFLICT",
            "This project changed since it was opened. Refresh and try again.",
        )
    transition_project(
        db, row, actor, "ON_HOLD", reason=data.reason, source="PROJECT_HOLD"
    )
    _audit(db, actor, row.id, "project.held", {"reason": data.reason})
    _commit(db)
    db.refresh(row)
    return _project_read(db, row)


@router.post("/{project_id}/resume", response_model=ProjectRead)
def resume_project(
    project_id: int,
    data: ProjectResumeWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_project_manager),
) -> ProjectRead:
    row = require_project_access(db, actor, project_id)
    if row.row_version != data.expected_version:
        raise ConflictError(
            "PROJECT_VERSION_CONFLICT",
            "This project changed since it was opened. Refresh and try again.",
        )
    if row.status != "ON_HOLD":
        raise ConflictError("PROJECT_NOT_ON_HOLD", "Only an on-hold project can be resumed.")
    hold_transition = db.scalar(
        select(ProjectStatusTransition)
        .where(
            ProjectStatusTransition.project_id == project_id,
            ProjectStatusTransition.to_status == "ON_HOLD",
        )
        .order_by(ProjectStatusTransition.created_at.desc(), ProjectStatusTransition.id.desc())
    )
    if not hold_transition:
        raise ConflictError(
            "PROJECT_RESUME_STATE_UNKNOWN",
            "The previous governed project state could not be determined.",
        )
    transition_project(
        db,
        row,
        actor,
        hold_transition.from_status,
        reason="Resumed from governed hold.",
        source="PROJECT_RESUME",
    )
    _audit(
        db,
        actor,
        row.id,
        "project.resumed",
        {"restored_status": hold_transition.from_status},
    )
    _commit(db)
    db.refresh(row)
    return _project_read(db, row)


@router.get("/{project_id}/transitions")
def project_transition_history(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.portfolio.view")),
) -> list[dict[str, Any]]:
    require_project_access(db, actor, project_id)
    rows = db.scalars(
        select(ProjectStatusTransition)
        .where(ProjectStatusTransition.project_id == project_id)
        .order_by(ProjectStatusTransition.created_at, ProjectStatusTransition.id)
    )
    return [_row_values(row) for row in rows]


@router.get("/{project_id}/plan")
def project_plan(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.portfolio.view")),
) -> dict[str, list[dict[str, Any]]]:
    require_project_access(db, actor, project_id)
    phases = list(
        db.scalars(
            select(ProjectPhase)
            .where(ProjectPhase.project_id == project_id)
            .order_by(ProjectPhase.sequence)
        )
    )
    milestones = list(
        db.scalars(
            select(ProjectMilestone)
            .where(ProjectMilestone.project_id == project_id)
            .order_by(ProjectMilestone.due_date)
        )
    )
    requests = list(
        db.scalars(
            select(ProjectAssignmentRequest)
            .where(ProjectAssignmentRequest.project_id == project_id)
            .order_by(ProjectAssignmentRequest.created_at.desc())
        )
    )

    return {
        "phases": [_row_values(x) for x in phases],
        "milestones": [_row_values(x) for x in milestones],
        "assignment_requests": [_row_values(x) for x in requests],
    }


@router.post("/{project_id}/phases", status_code=201)
def add_phase(
    project_id: int,
    data: PhaseWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_project_manager),
) -> Any:
    _get_project(db, project_id)
    row = ProjectPhase(project_id=project_id, **data.model_dump())
    db.add(row)
    _audit(db, actor, project_id, "project.phase.created", data.model_dump())
    _commit(db)
    db.refresh(row)
    return _row_values(row)


@router.post("/{project_id}/milestones", status_code=201)
def add_milestone(
    project_id: int,
    data: MilestoneWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_project_manager),
) -> Any:
    _get_project(db, project_id)
    if data.phase_id:
        phase = db.get(ProjectPhase, data.phase_id)
        if not phase or phase.project_id != project_id:
            raise ConflictError(
                "INVALID_PROJECT_PHASE", "Milestone phase must belong to this project."
            )
    row = ProjectMilestone(project_id=project_id, **data.model_dump())
    db.add(row)
    _audit(db, actor, project_id, "project.milestone.created", data.model_dump())
    _commit(db)
    db.refresh(row)
    return _row_values(row)


@router.patch("/{project_id}/milestones/{milestone_id}/schedule")
def update_milestone_schedule(
    project_id: int,
    milestone_id: int,
    data: MilestoneScheduleWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_project_manager),
) -> Any:
    project = require_project_access(db, actor, project_id)
    milestone = db.get(ProjectMilestone, milestone_id)
    if milestone is None or milestone.project_id != project_id:
        raise NotFoundError("Project milestone does not exist.")
    if project.status != "DRAFT":
        raise ConflictError("PROJECT_PLAN_PUBLISHED", "Only draft milestones can be rescheduled.")
    if data.due_date and (
        (project.planned_start_date and data.due_date < project.planned_start_date)
        or (project.planned_end_date and data.due_date > project.planned_end_date)
    ):
        raise ConflictError("INVALID_MILESTONE_DATE", "Milestone date must be within the project plan.")
    result = db.connection().execute(
        update(CompanyProject.__table__)
        .where(
            CompanyProject.id == project_id,
            CompanyProject.status == "DRAFT",
            CompanyProject.row_version == data.expected_version,
        )
        .values(row_version=data.expected_version + 1)
    )
    if result.rowcount != 1:
        raise ConflictError("PROJECT_VERSION_CONFLICT", "The project changed. Refresh before editing.")
    previous_due_date = milestone.due_date
    milestone.due_date = data.due_date
    _audit(db, actor, project_id, "project.milestone.rescheduled", {
        "milestone_id": milestone_id,
        "previous_due_date": previous_due_date,
        "due_date": data.due_date,
    })
    _commit(db)
    db.refresh(milestone)
    return _row_values(milestone)


@router.post("/{project_id}/request-implementation", status_code=201)
def request_implementation(
    project_id: int,
    data: AssignmentRequestWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.assignment.request")),
) -> Any:
    require_project_access(db, actor, project_id)
    if not db.get(Department, data.requested_department_id):
        raise NotFoundError("Requested department does not exist.")
    if data.requested_team_id and not db.get(SupportTeam, data.requested_team_id):
        raise NotFoundError("Requested team does not exist.")
    row = ProjectAssignmentRequest(
        project_id=project_id, requested_by_user_id=actor.id, **data.model_dump()
    )
    db.add(row)
    _audit(db, actor, project_id, "project.assignment.requested", data.model_dump())
    _commit(db)
    db.refresh(row)
    return _row_values(row)


@router.get("/assignment-requests/inbox")
def assignment_request_inbox(
    request_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.assignment.respond")),
) -> list[dict[str, Any]]:
    statement = select(ProjectAssignmentRequest).where(
        ProjectAssignmentRequest.project_id.in_(authorized_project_ids(db, actor))
    )
    if "project.manage" not in effective_permissions(db, actor).permissions:
        if actor.department_id is None:
            return []
        statement = statement.where(
            ProjectAssignmentRequest.requested_department_id == actor.department_id
        )
    if request_status:
        statement = statement.where(
            ProjectAssignmentRequest.status == request_status.upper()
        )
    rows = list(
        db.scalars(
            statement.order_by(
                ProjectAssignmentRequest.created_at.asc(),
                ProjectAssignmentRequest.id.asc(),
            )
        )
    )
    result: list[dict[str, Any]] = []
    for row in rows:
        project = db.get(CompanyProject, row.project_id)
        item = _row_values(row)
        item.update(
            {
                "project_number": project.project_number if project else "",
                "project_name": project.name if project else "",
                "project_status": project.status if project else "",
                "priority": project.priority if project else "NORMAL",
                "client_id": project.client_id if project else None,
            }
        )
        result.append(item)
    return result


@router.post("/assignment-requests/{request_id}/respond")
def respond_assignment(
    request_id: int,
    data: AssignmentResponseWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.assignment.respond")),
) -> Any:
    row = db.get(ProjectAssignmentRequest, request_id)
    if not row:
        raise NotFoundError("Assignment request does not exist.")
    project = require_project_access(db, actor, row.project_id)
    if (
        "project.manage" not in effective_permissions(db, actor).permissions
        and actor.department_id != row.requested_department_id
    ):
        raise NotFoundError("Assignment request does not exist.")
    decision = data.decision.upper()
    if decision not in {"ACCEPTED", "PROPOSED", "RETURNED", "REJECTED"}:
        raise ConflictError(
            "INVALID_ASSIGNMENT_DECISION", "Select ACCEPTED, PROPOSED, RETURNED, or REJECTED."
        )
    if row.row_version != data.expected_version:
        raise ConflictError(
            "ASSIGNMENT_VERSION_CONFLICT",
            "This assignment request changed since it was opened. Refresh and try again.",
        )
    if row.status not in {"PENDING", "PROPOSED"}:
        raise ConflictError(
            "ASSIGNMENT_ALREADY_DECIDED", "This assignment request has already been decided."
        )
    if data.requested_team_id:
        team = db.get(SupportTeam, data.requested_team_id)
        if not team or team.department_id != row.requested_department_id:
            raise ConflictError(
                "INVALID_ASSIGNMENT_TEAM",
                "The proposed Team must belong to the requested department.",
            )
    row.status = decision
    row.row_version += 1
    row.response_notes = data.response_notes
    row.responded_by_user_id = actor.id
    row.responded_at = server_now()
    if data.requested_team_id:
        row.requested_team_id = data.requested_team_id
    target_status = {
        "ACCEPTED": "READY_FOR_EXECUTION",
        "PROPOSED": "INTAKE_PROPOSED",
        "RETURNED": "INTAKE_RETURNED",
        "REJECTED": "INTAKE_REJECTED",
    }[decision]
    transition_project(
        db,
        project,
        actor,
        target_status,
        reason=data.response_notes,
        source="IMPLEMENTATION_INTAKE",
    )
    if decision == "ACCEPTED":
        existing_department = db.scalar(
            select(ProjectDepartment.id).where(
                ProjectDepartment.project_id == row.project_id,
                ProjectDepartment.department_id == row.requested_department_id,
                ProjectDepartment.role == "PRIMARY_IMPLEMENTATION",
            )
        )
        if not existing_department:
            db.add(
                ProjectDepartment(
                    project_id=row.project_id,
                    department_id=row.requested_department_id,
                    role="PRIMARY_IMPLEMENTATION",
                    is_primary=True,
                )
            )
        if row.requested_team_id:
            existing_team = db.scalar(
                select(ProjectTeam.id).where(
                    ProjectTeam.project_id == row.project_id,
                    ProjectTeam.team_id == row.requested_team_id,
                    ProjectTeam.role == "IMPLEMENTATION",
                )
            )
            if not existing_team:
                db.add(
                    ProjectTeam(
                        project_id=row.project_id,
                        team_id=row.requested_team_id,
                        role="IMPLEMENTATION",
                    )
                )
    _audit(
        db,
        actor,
        row.project_id,
        "project.assignment.responded",
        {"request_id": row.id, "decision": decision},
    )
    _commit(db)
    db.refresh(row)
    return _row_values(row)
