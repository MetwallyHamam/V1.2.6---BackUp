import json
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import String, cast, delete, func, select, true, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.api.dependencies import require_any_permission, require_permission
from app.core.clock import server_now, server_today
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
from app.modules.projects.numbering import format_task_number, lock_number_allocation
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
    ProjectWizardDraft,
)
from app.modules.projects.schemas import (
    AssignmentRequestWrite,
    AssignmentResponseWrite,
    AssignmentResubmitWrite,
    MilestoneRevisionDecision,
    MilestoneRevisionWrite,
    MilestoneScheduleWrite,
    MilestoneWrite,
    PhaseWrite,
    ProjectCoverageCheck,
    ProjectCreate,
    ProjectHoldWrite,
    ProjectRead,
    ProjectRegisterDecision,
    ProjectRegisterWrite,
    ProjectResumeWrite,
    ProjectTransitionWrite,
    ProjectUpdate,
    ProjectWizardCheckpointWrite,
    ProjectWizardCreate,
    ProjectWizardResult,
    TaskDependenciesWrite,
    TaskRevisionWrite,
    TaskScheduleWrite,
)

router = APIRouter(prefix="/projects", tags=["project portfolio"])


@router.get("/wizard-draft")
def get_wizard_draft(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.create")),
) -> dict[str, Any] | None:
    row = db.get(ProjectWizardDraft, actor.id)
    return {"version": row.version, "checkpoint": row.checkpoint} if row else None


@router.put("/wizard-draft")
def save_wizard_draft(
    data: ProjectWizardCheckpointWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.create")),
) -> dict[str, int]:
    if len(json.dumps(data.checkpoint).encode("utf-8")) > 512_000:
        raise ConflictError("WIZARD_DRAFT_TOO_LARGE", "The draft exceeds the storage limit.")
    version = data.expected_version + 1
    if data.expected_version == 0:
        db.add(ProjectWizardDraft(owner_user_id=actor.id, version=version, checkpoint=data.checkpoint))
    else:
        result = db.connection().execute(update(ProjectWizardDraft).where(
            ProjectWizardDraft.owner_user_id == actor.id,
            ProjectWizardDraft.version == data.expected_version,
        ).values(version=version, checkpoint=data.checkpoint))
        if result.rowcount != 1:
            raise ConflictError("WIZARD_DRAFT_CONFLICT", "Reopen the wizard to load the latest draft.")
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("WIZARD_DRAFT_CONFLICT", "Reopen the wizard to load the latest draft.") from exc
    return {"version": version}


@router.delete("/wizard-draft", status_code=204)
def delete_wizard_draft(
    expected_version: int = Query(ge=1),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.create")),
) -> None:
    result = db.connection().execute(delete(ProjectWizardDraft).where(
        ProjectWizardDraft.owner_user_id == actor.id,
        ProjectWizardDraft.version == expected_version,
    ))
    if result.rowcount != 1:
        raise ConflictError("WIZARD_DRAFT_CONFLICT", "Reopen the wizard to load the latest draft.")
    db.commit()


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


def _next_wizard_project_number(db: Session) -> str:
    year = server_today().year
    lock_number_allocation(db, f"SupportHub.ProjectNumber.{year}")
    prefix = f"{year}-"
    existing = db.scalars(select(CompanyProject.project_number).where(
        CompanyProject.project_number.startswith(prefix)
    ))
    suffixes = (number.removeprefix(prefix) for number in existing)
    last = max((int(value) for value in suffixes if value.isascii() and value.isdecimal()), default=0)
    number = f"{prefix}{last + 1:04d}"
    if len(number) > 50:
        raise ConflictError("PROJECT_NUMBER_EXHAUSTED", "Enter a manual project number.")
    return number


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
            project_number=data.project_number.strip() or "AUTO",
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
    if not department or not department.is_active:
        raise ConflictError(
            "INVALID_IMPLEMENTATION_DEPARTMENT", "Select an active delivery department."
        )
    team = db.get(SupportTeam, data.requested_team_id) if data.requested_team_id else None
    if data.requested_team_id is not None and (
        not team or not team.is_active or team.department_id != department.id
    ):
        raise ConflictError(
            "INVALID_PROJECT_TEAM", "The selected team must be active in the requested department."
        )
    if team and data.intake_owner_user_id is None:
        raise ConflictError("INVALID_INTAKE_OWNER", "Select an intake owner for the requested team.")
    if data.intake_owner_user_id is not None:
        intake_owner = db.get(User, data.intake_owner_user_id)
        if not intake_owner or not intake_owner.is_active:
            raise ConflictError("INVALID_INTAKE_OWNER", "Select an active intake owner.")
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
    for phase in data.phases:
        if any(project_modules[module_id].product_id not in phase.product_ids for module_id in phase.module_ids):
            raise ConflictError("INVALID_PHASE_MODULE", "Every phase module must belong to a phase product.")
        if any(
            task.product_module_id is not None
            and project_modules[task.product_module_id].product_id != task.product_id
            for task in phase.tasks
        ):
            raise ConflictError("INVALID_TASK_MODULE", "The task module must belong to its product.")
    all_user_ids = {data.project_manager_user_id}
    if data.intake_owner_user_id is not None:
        all_user_ids.add(data.intake_owner_user_id)
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

    project_number = data.project_number.strip().upper() or _next_wizard_project_number(db)
    tasks = [task for phase in data.phases for task in phase.tasks]
    used_numbers = {task.task_number.strip().upper() for task in tasks if task.task_number.strip()}
    serial = 0
    for task in tasks:
        while not task.task_number.strip():
            serial += 1
            candidate = format_task_number(project_number, serial)
            if candidate not in used_numbers:
                task.task_number = candidate
                used_numbers.add(candidate)
    row = CompanyProject(
        project_number=project_number,
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
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("PROJECT_NUMBER_CONFLICT", "The project number is already in use. Check the number and try again.") from exc
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
    if data.checkpoint_version is not None:
        result = db.connection().execute(delete(ProjectWizardDraft).where(
            ProjectWizardDraft.owner_user_id == actor.id,
            ProjectWizardDraft.version == data.checkpoint_version,
        ))
        if result.rowcount != 1:
            raise ConflictError("WIZARD_DRAFT_CONFLICT", "Reopen the wizard to load the latest draft.")
    _commit(db)
    return ProjectWizardResult(
        project_id=row.id,
        status=row.status,
        phase_count=len(data.phases),
        task_count=task_count,
        assignment_request_id=assignment_request_id,
    )


@router.get("/portfolio-products")
def portfolio_products(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.portfolio.view")),
) -> list[dict[str, Any]]:
    rows = db.execute(
        select(ProjectProductScope.project_id, Product.id, Product.name)
        .join(Product, Product.id == ProjectProductScope.product_id)
        .where(ProjectProductScope.project_id.in_(authorized_project_ids(db, actor)))
        .order_by(Product.name, Product.id, ProjectProductScope.project_id)
    )
    return [
        {"project_id": project_id, "product_id": product_id, "name": name}
        for project_id, product_id, name in rows
    ]


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
    changes = data.model_dump(exclude_unset=True, exclude={"expected_version"})
    if "name" in changes:
        if not changes["name"] or not changes["name"].strip():
            raise ConflictError("INVALID_PROJECT_NAME", "Enter a project name.")
        changes["name"] = changes["name"].strip()
    start = changes.get("planned_start_date", row.planned_start_date)
    end = changes.get("planned_end_date", row.planned_end_date)
    if start and end and end < start:
        raise ConflictError(
            "INVALID_PROJECT_DATES", "Planned end date cannot precede planned start date."
        )
    version = data.expected_version if data.expected_version is not None else row.row_version
    if row.row_version != version:
        raise ConflictError("PROJECT_VERSION_CONFLICT", "This project changed. Refresh before editing again.")
    if not changes:
        return _project_read(db, row)
    result = db.connection().execute(update(CompanyProject).where(
        CompanyProject.id == row.id, CompanyProject.row_version == version,
    ).values(**changes, row_version=version + 1))
    if result.rowcount != 1:
        raise ConflictError("PROJECT_VERSION_CONFLICT", "This project changed. Refresh before editing again.")
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
        update(CompanyProject)
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


REVISION_REQUESTED = "project.milestone.revision_requested"
TASK_REVISION_REQUESTED = "project.task.revision_requested"
REVISION_DECIDED = "project.milestone.revision_decided"
REVISION_STATES = {"AWAITING_IMPLEMENTATION_ACCEPTANCE", "READY_FOR_EXECUTION", "IN_EXECUTION", "ON_HOLD"}


@router.get("/my-work/delivery-exceptions")
def my_delivery_exceptions(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.portfolio.view")),
) -> list[dict[str, Any]]:
    assigned = select(CompanyProject.id).where(
        CompanyProject.project_manager_user_id == actor.id,
        CompanyProject.is_active == true(),
        CompanyProject.status.notin_(["DRAFT", "COMPLETED", "CANCELLED", "ARCHIVED"]),
    )
    milestones = db.execute(select(
        ProjectMilestone.id, ProjectMilestone.project_id, ProjectMilestone.name, ProjectMilestone.due_date,
    ).where(
        ProjectMilestone.project_id.in_(assigned), ProjectMilestone.due_date < server_today(),
        ProjectMilestone.status.notin_(["DONE", "COMPLETED", "ACHIEVED", "CANCELLED"]),
    )).all()
    items = [
        {"kind": "milestone", "id": item.id, "project_id": item.project_id,
         "title": item.name, "due_date": item.due_date, "owner_user_id": actor.id}
        for item in milestones
    ]
    if "implementation.task.view" in effective_permissions(db, actor).permissions:
        tasks = db.execute(select(
            ProjectTask.id, ProjectTask.project_id, ProjectTask.title,
            ProjectTask.planned_end_date, ProjectTask.owner_user_id,
        ).where(ProjectTask.project_id.in_(assigned), ProjectTask.status == "BLOCKED")).all()
        items.extend(
            {"kind": "task", "id": item.id, "project_id": item.project_id,
             "title": item.title, "due_date": item.planned_end_date, "owner_user_id": item.owner_user_id}
            for item in tasks
        )
    return items


@router.get("/my-work/pending-schedule-decisions")
def my_pending_schedule_decisions(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.portfolio.view")),
) -> dict[int, int]:
    proposal = aliased(AuditLog)
    decision = aliased(AuditLog)
    readable_actions = [REVISION_REQUESTED]
    if "implementation.task.view" in effective_permissions(db, actor).permissions:
        readable_actions.append(TASK_REVISION_REQUESTED)
    decided = select(decision.id).where(
        decision.entity_type == "project_milestone_revision",
        decision.action == REVISION_DECIDED,
        decision.entity_id == cast(proposal.id, String(100)),
    ).exists()
    rows = db.execute(
        select(CompanyProject.id, func.count(proposal.id))
        .join(proposal, proposal.entity_id == cast(CompanyProject.id, String(100)))
        .where(
            CompanyProject.project_manager_user_id == actor.id,
            CompanyProject.is_active == true(),
            CompanyProject.status.notin_(["COMPLETED", "CANCELLED"]),
            proposal.entity_type == "company_project",
            proposal.action.in_(readable_actions),
            ~decided,
        )
        .group_by(CompanyProject.id)
    )
    return {project_id: count for project_id, count in rows}


@router.get("/{project_id}/milestone-revisions")
def list_milestone_revisions(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.portfolio.view")),
) -> list[dict[str, Any]]:
    require_project_access(db, actor, project_id)
    requests = db.scalars(select(AuditLog).where(
        AuditLog.entity_type == "company_project",
        AuditLog.entity_id == str(project_id),
        AuditLog.action.in_([REVISION_REQUESTED, TASK_REVISION_REQUESTED])
        if "implementation.task.view" in effective_permissions(db, actor).permissions
        else AuditLog.action == REVISION_REQUESTED,
    ).order_by(AuditLog.id.desc())).all()
    decisions = {
        row.entity_id: json.loads(row.new_values_json or "{}")["decision"]
        for row in db.scalars(select(AuditLog).where(
            AuditLog.entity_type == "project_milestone_revision",
            AuditLog.action == REVISION_DECIDED,
            AuditLog.entity_id.in_([str(request.id) for request in requests]),
        ))
    }
    return [
        {**json.loads(row.new_values_json or "{}"), "id": row.id,
         "status": decisions.get(str(row.id), "PENDING"), "requested_by_user_id": row.actor_user_id}
        for row in requests
    ]


@router.post("/{project_id}/milestones/{milestone_id}/revisions", status_code=201)
def request_milestone_revision(
    project_id: int,
    milestone_id: int,
    data: MilestoneRevisionWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_project_manager),
) -> dict[str, bool]:
    project = require_project_access(db, actor, project_id)
    milestone = db.get(ProjectMilestone, milestone_id)
    if milestone is None or milestone.project_id != project_id:
        raise NotFoundError("Project milestone does not exist.")
    if project.row_version != data.expected_version or project.status not in REVISION_STATES:
        raise ConflictError("PROJECT_VERSION_CONFLICT", "Refresh the active published plan.")
    if not data.reason.strip() or data.due_date == milestone.due_date:
        raise ConflictError("INVALID_MILESTONE_REVISION", "Enter a different finish date and a reason.")
    _audit(db, actor, project_id, REVISION_REQUESTED, {
        "milestone_id": milestone_id, "previous_due_date": milestone.due_date,
        "due_date": data.due_date, "reason": data.reason.strip(), "project_version": data.expected_version,
    })
    _commit(db)
    return {"submitted": True}


@router.post("/{project_id}/tasks/{task_id}/revisions", status_code=201)
def request_task_revision(
    project_id: int,
    task_id: int,
    data: TaskRevisionWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_project_manager),
) -> dict[str, bool]:
    project = require_project_access(db, actor, project_id)
    task = db.get(ProjectTask, task_id)
    if task is None or task.project_id != project_id or "implementation.task.view" not in effective_permissions(db, actor).permissions:
        raise NotFoundError("Project task does not exist.")
    change = data.schedule or data.dependencies
    assert change is not None
    if project.row_version != change.expected_version or project.status not in REVISION_STATES:
        raise ConflictError("PROJECT_VERSION_CONFLICT", "Refresh the active published plan.")
    if not data.reason.strip():
        raise ConflictError("INVALID_TASK_REVISION", "Enter a revision reason.")
    previous: dict[str, Any] = {
        "planned_start_date": task.planned_start_date, "planned_end_date": task.planned_end_date,
    }
    if data.dependencies is not None:
        previous = {"predecessor_ids": sorted(db.scalars(select(
            ProjectTaskDependency.depends_on_task_id
        ).where(ProjectTaskDependency.task_id == task_id)))}
    _audit(db, actor, project_id, TASK_REVISION_REQUESTED, {
        "task_id": task_id, "task_number": task.task_number, "task_title": task.title,
        "reason": data.reason.strip(), "project_version": change.expected_version,
        "kind": "TASK_SCHEDULE" if data.schedule is not None else "TASK_DEPENDENCIES",
        "previous": previous, "proposed": change.model_dump(mode="json", exclude={"expected_version"}),
    })
    _commit(db)
    return {"submitted": True}


@router.post("/{project_id}/milestone-revisions/{revision_id}/decision")
def decide_milestone_revision(
    project_id: int,
    revision_id: int,
    data: MilestoneRevisionDecision,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.manage")),
) -> dict[str, str]:
    project = require_project_access(db, actor, project_id)
    proposal = db.get(AuditLog, revision_id)
    if (proposal is None or proposal.entity_type != "company_project"
        or proposal.entity_id != str(project_id)
        or proposal.action not in {REVISION_REQUESTED, TASK_REVISION_REQUESTED}):
        raise NotFoundError("Milestone revision does not exist.")
    if proposal.action == TASK_REVISION_REQUESTED and "implementation.task.view" not in effective_permissions(db, actor).permissions:
        raise NotFoundError("Task revision does not exist.")
    if proposal.actor_user_id == actor.id:
        raise ConflictError("REVISION_SELF_DECISION", "A separate reviewer must decide this revision.")
    result = db.connection().execute(update(CompanyProject).where(
        CompanyProject.id == project_id, CompanyProject.row_version == data.expected_version,
    ).values(row_version=data.expected_version + 1))
    if result.rowcount != 1:
        raise ConflictError("PROJECT_VERSION_CONFLICT", "Refresh the project before deciding.")
    if db.scalar(select(AuditLog.id).where(
        AuditLog.entity_type == "project_milestone_revision",
        AuditLog.entity_id == str(revision_id), AuditLog.action == REVISION_DECIDED,
    ).limit(1)) is not None:
        raise ConflictError("REVISION_ALREADY_DECIDED", "This revision already has a decision.")
    change = json.loads(proposal.new_values_json or "{}")
    if data.decision == "APPROVED" and (
        project.status not in REVISION_STATES or change["project_version"] != data.expected_version
    ):
        raise ConflictError("REVISION_STALE", "Submit a new revision for the current plan.")
    if data.decision == "APPROVED" and proposal.action == TASK_REVISION_REQUESTED:
        task = db.get(ProjectTask, change["task_id"])
        if task is None or task.project_id != project_id:
            raise ConflictError("REVISION_STALE", "The task is no longer in this project.")
        if change["kind"] == "TASK_SCHEDULE":
            schedule = TaskScheduleWrite.model_validate({
                **change["proposed"], "expected_version": data.expected_version,
            })
            _apply_task_schedule(db, actor, project, task, schedule)
        else:
            _apply_task_dependencies(db, actor, project_id, task.id, set(change["proposed"]["predecessor_ids"]))
    elif data.decision == "APPROVED":
        milestone = db.get(ProjectMilestone, change["milestone_id"])
        if (milestone is None or milestone.project_id != project_id
            or project.status not in REVISION_STATES or change["project_version"] != data.expected_version
            or (str(milestone.due_date) if milestone.due_date else None) != change["previous_due_date"]):
            raise ConflictError("REVISION_STALE", "Submit a new revision for the current plan.")
        due = date.fromisoformat(change["due_date"]) if change["due_date"] else None
        if due and (
            (project.planned_start_date and due < project.planned_start_date)
            or (project.planned_end_date and due > project.planned_end_date)
        ):
            raise ConflictError("INVALID_MILESTONE_DATE", "Milestone date must be within the project plan.")
        milestone.due_date = due
    db.add(AuditLog(
        actor_user_id=actor.id, entity_type="project_milestone_revision", entity_id=str(revision_id),
        action=REVISION_DECIDED, new_values_json=json.dumps({"decision": data.decision}),
    ))
    _commit(db)
    return {"status": data.decision}


REGISTER_CREATED = "project.register.created"
REGISTER_DECIDED = "project.register.decided"


@router.get("/{project_id}/register")
def list_project_register(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.portfolio.view")),
) -> list[dict[str, Any]]:
    require_project_access(db, actor, project_id)
    entries = db.scalars(select(AuditLog).where(
        AuditLog.entity_type == "company_project", AuditLog.entity_id == str(project_id),
        AuditLog.action == REGISTER_CREATED,
    ).order_by(AuditLog.id.desc())).all()
    decisions = {
        item.entity_id: json.loads(item.new_values_json or "{}")
        for item in db.scalars(select(AuditLog).where(
            AuditLog.entity_type == "project_register_entry", AuditLog.action == REGISTER_DECIDED,
            AuditLog.entity_id.in_([str(entry.id) for entry in entries]),
        ))
    }
    return [{
        **json.loads(entry.new_values_json or "{}"), "id": entry.id,
        "owner_user_id": entry.actor_user_id, "status": "OPEN", **decisions.get(str(entry.id), {}),
    } for entry in entries]


@router.post("/{project_id}/register", status_code=201)
def create_project_register_entry(
    project_id: int,
    data: ProjectRegisterWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_project_manager),
) -> dict[str, bool]:
    project = require_project_access(db, actor, project_id)
    if project.status in {"CANCELLED", "COMPLETED"}:
        raise ConflictError("PROJECT_REGISTER_CLOSED", "This project is closed.")
    _audit(db, actor, project_id, REGISTER_CREATED, data.model_dump(mode="json"))
    _commit(db)
    return {"created": True}


@router.post("/{project_id}/register/{entry_id}/decision")
def decide_project_register_entry(
    project_id: int,
    entry_id: int,
    data: ProjectRegisterDecision,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.manage")),
) -> dict[str, str]:
    project = require_project_access(db, actor, project_id)
    entry = db.get(AuditLog, entry_id)
    if (entry is None or entry.entity_type != "company_project"
        or entry.entity_id != str(project_id) or entry.action != REGISTER_CREATED):
        raise NotFoundError("Register entry does not exist.")
    kind = json.loads(entry.new_values_json or "{}")["kind"]
    if kind == "CHANGE" and entry.actor_user_id == actor.id:
        raise ConflictError("REGISTER_SELF_DECISION", "A separate reviewer must decide changes.")
    if (kind == "RISK") != (data.status == "MITIGATED"):
        raise ConflictError("INVALID_REGISTER_DECISION", "Choose a decision appropriate for this entry.")
    if data.revision_id is not None:
        revision = db.get(AuditLog, data.revision_id)
        if (data.status != "APPROVED" or revision is None or revision.entity_type != "company_project"
            or revision.entity_id != str(project_id) or revision.action not in {REVISION_REQUESTED, TASK_REVISION_REQUESTED}):
            raise ConflictError("INVALID_REGISTER_REVISION", "Link an approved change to a revision in this project.")
    result = db.connection().execute(update(CompanyProject).where(
        CompanyProject.id == project_id, CompanyProject.row_version == data.expected_version,
        CompanyProject.status == project.status,
    ).values(row_version=data.expected_version))
    if result.rowcount != 1:
        raise ConflictError("PROJECT_VERSION_CONFLICT", "Refresh the project before deciding.")
    if db.scalar(select(AuditLog.id).where(
        AuditLog.entity_type == "project_register_entry", AuditLog.entity_id == str(entry_id),
        AuditLog.action == REGISTER_DECIDED,
    ).limit(1)) is not None:
        raise ConflictError("REGISTER_ALREADY_DECIDED", "This entry already has a decision.")
    db.add(AuditLog(
        actor_user_id=actor.id, entity_type="project_register_entry", entity_id=str(entry_id),
        action=REGISTER_DECIDED, new_values_json=json.dumps({
            "status": data.status, "decision_reason": data.reason, "revision_id": data.revision_id,
        }),
    ))
    _commit(db)
    return {"status": data.status}


@router.get("/{project_id}/schedule-baseline")
def get_schedule_baseline(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.portfolio.view")),
) -> dict[str, Any] | None:
    require_project_access(db, actor, project_id)
    record = db.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "company_project",
            AuditLog.entity_id == str(project_id),
            AuditLog.action == "project.schedule.baseline_captured",
        ).order_by(AuditLog.id.desc()).limit(1)
    )
    if record is None:
        return None
    snapshot: dict[str, Any] = json.loads(record.new_values_json or "{}")
    if "implementation.task.view" not in effective_permissions(db, actor).permissions:
        snapshot.pop("Task", None)
    return {"captured_at": record.created_at, "items": snapshot}


@router.post("/{project_id}/schedule-baseline", status_code=201)
def capture_schedule_baseline(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_project_manager),
) -> dict[str, bool]:
    project = require_project_access(db, actor, project_id)
    if project.status != "DRAFT":
        raise ConflictError("PROJECT_PLAN_PUBLISHED", "Capture the baseline while the project is a draft.")
    _audit(db, actor, project_id, "project.schedule.baseline_captured", _schedule_snapshot(db, project_id))
    _commit(db)
    return {"captured": True}


def _schedule_snapshot(db: Session, project_id: int) -> dict[str, object]:
    snapshot: dict[str, object] = {}
    for kind, model in (
        ("Phase", ProjectPhase),
        ("Task", ProjectTask),
        ("Milestone", ProjectMilestone),
    ):
        items = db.scalars(select(model).where(model.project_id == project_id)).all()
        snapshot[kind] = {
            str(item.id): {
                "start": getattr(item, "planned_start_at", None)
                or getattr(item, "planned_start_date", None) or getattr(item, "due_date", None),
                "end": getattr(item, "planned_end_at", None)
                or getattr(item, "planned_end_date", None) or getattr(item, "due_date", None),
            }
            for item in items
        }
    return snapshot


@router.patch("/{project_id}/tasks/{task_id}/schedule")
def update_task_schedule(
    project_id: int,
    task_id: int,
    data: TaskScheduleWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_project_manager),
) -> dict[str, Any]:
    project = require_project_access(db, actor, project_id)
    task = db.get(ProjectTask, task_id)
    if task is None or task.project_id != project_id:
        raise NotFoundError("Project task does not exist.")
    if project.status != "DRAFT":
        raise ConflictError("PROJECT_PLAN_PUBLISHED", "Only draft task dates can be edited directly.")
    result = db.connection().execute(update(CompanyProject).where(
        CompanyProject.id == project_id, CompanyProject.status == "DRAFT",
        CompanyProject.row_version == data.expected_version,
    ).values(row_version=data.expected_version + 1))
    if result.rowcount != 1:
        raise ConflictError("PROJECT_VERSION_CONFLICT", "Refresh the draft before editing.")
    _apply_task_schedule(db, actor, project, task, data)
    _commit(db)
    db.refresh(task)
    return _row_values(task)


def _apply_task_schedule(
    db: Session, actor: User, project: CompanyProject, task: ProjectTask, data: TaskScheduleWrite,
) -> None:
    project_id, task_id = project.id, task.id
    start, end = data.planned_start_date, data.planned_end_date
    phase = db.get(ProjectPhase, task.phase_id) if task.phase_id else None
    for window in (project, phase):
        if window and (
            (window.planned_start_date and start < window.planned_start_date)
            or (window.planned_end_date and end > window.planned_end_date)
        ):
            raise ConflictError("INVALID_TASK_WINDOW", "Task dates must fit within the project and phase.")
    start_at = datetime.combine(start, task.planned_start_at.timetz()) if task.planned_start_at else None
    end_at = datetime.combine(end, task.planned_end_at.timetz()) if task.planned_end_at else None
    if start_at and end_at and start_at.replace(tzinfo=None) > end_at.replace(tzinfo=None):
        raise ConflictError("INVALID_TASK_WINDOW", "The preserved finish time precedes the start time.")
    for relation in db.scalars(select(ProjectTaskDependency).where(
        (ProjectTaskDependency.task_id == task_id) | (ProjectTaskDependency.depends_on_task_id == task_id)
    )):
        predecessor = relation.task_id == task_id
        related = db.get(ProjectTask, relation.depends_on_task_id if predecessor else relation.task_id)
        if related is None or related.project_id != project_id:
            continue
        earlier_at = related.planned_end_at if predecessor else end_at
        later_at = start_at if predecessor else related.planned_start_at
        earlier = earlier_at.date() if earlier_at else (related.planned_end_date if predecessor else end)
        later = later_at.date() if later_at else (start if predecessor else related.planned_start_date)
        if earlier and later and (earlier > later or (
            earlier == later and earlier_at and later_at
            and earlier_at.replace(tzinfo=None) > later_at.replace(tzinfo=None)
        )):
            raise ConflictError("INVALID_TASK_DEPENDENCY_DATES", "Task dates overlap a finish-to-start dependency.")
    _audit(db, actor, project_id, "project.task.rescheduled", {
        "task_id": task_id, "previous_start": task.planned_start_date, "previous_finish": task.planned_end_date,
        "planned_start_date": start, "planned_end_date": end,
    })
    task.planned_start_date, task.planned_end_date = start, end
    task.planned_start_at, task.planned_end_at = start_at, end_at


@router.put("/{project_id}/tasks/{task_id}/dependencies")
def replace_task_dependencies(
    project_id: int,
    task_id: int,
    data: TaskDependenciesWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_project_manager),
) -> dict[str, int]:
    require_project_access(db, actor, project_id)
    result = db.connection().execute(
        update(CompanyProject)
        .where(
            CompanyProject.id == project_id,
            CompanyProject.status == "DRAFT",
            CompanyProject.row_version == data.expected_version,
        )
        .values(row_version=data.expected_version + 1)
    )
    if result.rowcount != 1:
        raise ConflictError("PROJECT_VERSION_CONFLICT", "Refresh the current draft before editing.")
    _apply_task_dependencies(db, actor, project_id, task_id, set(data.predecessor_ids))
    _commit(db)
    return {"row_version": data.expected_version + 1}


def _apply_task_dependencies(
    db: Session, actor: User, project_id: int, task_id: int, proposed: set[int],
) -> None:
    task_ids = set(db.scalars(select(ProjectTask.id).where(ProjectTask.project_id == project_id)))
    if task_id not in task_ids:
        raise NotFoundError("Project task does not exist.")
    if task_id in proposed or not proposed <= task_ids:
        raise ConflictError("INVALID_TASK_DEPENDENCY", "Choose other tasks from this project.")
    edges: dict[int, set[int]] = {}
    for edge in db.scalars(
        select(ProjectTaskDependency).where(
            ProjectTaskDependency.task_id.in_(select(ProjectTask.id).where(
                ProjectTask.project_id == project_id
            ))
        )
    ):
        edges.setdefault(edge.task_id, set()).add(edge.depends_on_task_id)
    previous = edges.get(task_id, set())
    pending = list(proposed)
    visited: set[int] = set()
    while pending:
        candidate = pending.pop()
        if candidate == task_id:
            raise ConflictError("TASK_DEPENDENCY_CYCLE", "This change would create a dependency cycle.")
        if candidate not in visited:
            visited.add(candidate)
            pending.extend(edges.get(candidate, set()) - visited)
    task = db.get(ProjectTask, task_id)
    assert task is not None
    for predecessor_id in proposed - previous:
        predecessor_task = db.get(ProjectTask, predecessor_id)
        assert predecessor_task is not None
        finish_at = predecessor_task.planned_end_at
        start_at = task.planned_start_at
        finish = finish_at.date() if finish_at else predecessor_task.planned_end_date
        start = start_at.date() if start_at else task.planned_start_date
        if finish and start and (finish > start or (
            finish == start and finish_at and start_at
            and finish_at.replace(tzinfo=None) > start_at.replace(tzinfo=None)
        )):
            raise ConflictError("INVALID_TASK_DEPENDENCY_DATES", "A predecessor finishes after the task starts.")
    db.execute(delete(ProjectTaskDependency).where(
        ProjectTaskDependency.task_id == task_id,
        ProjectTaskDependency.depends_on_task_id.in_(previous - proposed),
    ))
    db.add_all(
        ProjectTaskDependency(task_id=task_id, depends_on_task_id=predecessor)
        for predecessor in proposed - previous
    )
    _audit(db, actor, project_id, "project.task.dependencies_updated", {
        "task_id": task_id, "previous": sorted(previous), "predecessor_ids": sorted(proposed),
    })


@router.post("/{project_id}/request-implementation", status_code=201)
def request_implementation(
    project_id: int,
    data: AssignmentRequestWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.assignment.request")),
) -> Any:
    project = require_project_access(db, actor, project_id)
    if (
        project.project_manager_user_id != actor.id
        and "project.manage" not in effective_permissions(db, actor).permissions
    ):
        raise NotFoundError("Project does not exist.")
    if not db.get(Department, data.requested_department_id):
        raise NotFoundError("Requested department does not exist.")
    if data.requested_team_id:
        team = db.get(SupportTeam, data.requested_team_id)
        if team is None or team.department_id != data.requested_department_id:
            raise NotFoundError("Requested team does not belong to the requested department.")
    row = ProjectAssignmentRequest(
        project_id=project_id, requested_by_user_id=actor.id, **data.model_dump()
    )
    db.add(row)
    _audit(db, actor, project_id, "project.assignment.requested", data.model_dump())
    _commit(db)
    db.refresh(row)
    return _row_values(row)


@router.post("/{project_id}/assignment-requests/{request_id}/resubmit", status_code=201)
def resubmit_assignment(
    project_id: int,
    request_id: int,
    data: AssignmentResubmitWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.assignment.request")),
) -> Any:
    project = require_project_access(db, actor, project_id)
    if project.project_manager_user_id != actor.id and "project.manage" not in effective_permissions(db, actor).permissions:
        raise NotFoundError("Project does not exist.")
    previous = db.get(ProjectAssignmentRequest, request_id)
    if previous is None or previous.project_id != project_id:
        raise NotFoundError("Assignment request does not exist.")
    if project.status not in {"INTAKE_PROPOSED", "INTAKE_RETURNED"} or previous.status not in {"PROPOSED", "RETURNED"}:
        raise ConflictError("INTAKE_NOT_RESUBMITTABLE", "Only proposed or returned intake can be resubmitted.")
    if data.requested_end_date < data.requested_start_date or not data.notes.strip():
        raise ConflictError("INVALID_INTAKE_REVISION", "Provide an ordered delivery window and a reason.")
    result = db.connection().execute(update(CompanyProject).where(
        CompanyProject.id == project_id, CompanyProject.row_version == data.expected_version,
        CompanyProject.status == project.status,
    ).values(row_version=data.expected_version))
    if result.rowcount != 1:
        raise ConflictError("PROJECT_VERSION_CONFLICT", "Refresh the project before resubmitting.")
    latest = db.scalar(select(func.max(ProjectAssignmentRequest.id)).where(
        ProjectAssignmentRequest.project_id == project_id,
    ))
    if latest != request_id:
        raise ConflictError("INTAKE_REQUEST_SUPERSEDED", "A newer request already exists.")
    request = ProjectAssignmentRequest(
        project_id=project_id, requested_by_user_id=actor.id,
        requested_department_id=previous.requested_department_id,
        requested_team_id=previous.requested_team_id,
        requested_start_date=data.requested_start_date, requested_end_date=data.requested_end_date,
        capability_notes=data.notes.strip(),
    )
    db.add(request)
    db.flush()
    transition_project(db, project, actor, "AWAITING_IMPLEMENTATION_ACCEPTANCE",
                       reason=data.notes.strip(), source="IMPLEMENTATION_INTAKE")
    _audit(db, actor, project_id, "project.assignment.resubmitted", {
        "previous_request_id": request_id, "new_request_id": request.id,
    })
    _commit(db)
    db.refresh(request)
    return _row_values(request)


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
    lock = db.connection().execute(update(CompanyProject).where(
        CompanyProject.id == project.id, CompanyProject.row_version == project.row_version,
    ).values(row_version=project.row_version))
    if lock.rowcount != 1:
        raise ConflictError("PROJECT_VERSION_CONFLICT", "Refresh the project before responding.")
    if row.status == "PROPOSED" and db.scalar(select(func.max(ProjectAssignmentRequest.id)).where(
        ProjectAssignmentRequest.project_id == row.project_id,
    )) != row.id:
        raise ConflictError("INTAKE_REQUEST_SUPERSEDED", "A newer request already exists.")
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
        snapshot = _schedule_snapshot(db, project.id)
        snapshot["Agreement"] = {
            "request_id": row.id,
            "department_id": row.requested_department_id,
            "team_id": row.requested_team_id,
            "start_date": row.requested_start_date or project.planned_start_date,
            "end_date": row.requested_end_date or project.planned_end_date,
            "project_version": project.row_version,
            "branch_ids": list(db.scalars(select(ProjectBranchScope.branch_id).where(
                ProjectBranchScope.project_id == project.id))),
            "product_ids": list(db.scalars(select(ProjectProductScope.product_id).where(
                ProjectProductScope.project_id == project.id))),
            "module_ids": list(db.scalars(select(ProjectModuleScope.product_module_id).where(
                ProjectModuleScope.project_id == project.id))),
        }
        _audit(db, actor, project.id, "project.schedule.baseline_captured", snapshot)
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
