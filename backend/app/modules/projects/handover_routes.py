import json
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select, true, update
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now, server_today
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import Client
from app.modules.iam.models import AuditLog, Department, User
from app.modules.iam.service import effective_permissions
from app.modules.notifications.models import Notification
from app.modules.projects.access import authorized_project_ids, require_project_access
from app.modules.projects.handover_schemas import (
    HandoverDecisionWrite,
    HandoverItemUpdate,
    HandoverRoutingWrite,
    ResidualCloseWrite,
    ResidualItemWrite,
    StabilizationCompleteWrite,
    StabilizationPlanWrite,
)
from app.modules.projects.lifecycle import transition_project
from app.modules.projects.models import (
    CompanyProject,
    ProjectDepartment,
    ProjectEvidence,
    ProjectHandoverDecision,
    ProjectHandoverItem,
    ProjectHandoverResidualItem,
    ProjectHandoverSection,
    ProjectStabilizationPlan,
    ProjectSupportHandover,
)

router = APIRouter(tags=["project support handover"])
DEFAULT_SECTIONS = [
    (
        "SCOPE",
        "Supported scope and branches",
        [("Supported products, services and branches", True, True)],
    ),
    (
        "ACCESS",
        "Operational access readiness",
        [("Support access is tested and approved", True, True)],
    ),
    (
        "DOCUMENTATION",
        "Runbooks and knowledge",
        [
            ("Runbook and troubleshooting guide", True, True),
            ("Training and operational contacts", True, True),
        ],
    ),
    (
        "QUALITY",
        "Deployment and UAT",
        [("Deployment evidence", True, True), ("UAT acceptance evidence", True, True)],
    ),
    (
        "RESIDUAL",
        "Known issues and residual work",
        [("Known issues and accountable owners", True, False)],
    ),
]


def _values(row: Any) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def _project(db: Session, project_id: int, actor: User) -> CompanyProject:
    return require_project_access(db, actor, project_id)


def _handover(db: Session, project_id: int, actor: User) -> ProjectSupportHandover:
    require_project_access(db, actor, project_id)
    row = db.scalar(
        select(ProjectSupportHandover).where(ProjectSupportHandover.project_id == project_id)
    )
    if not row:
        raise NotFoundError("Support handover has not been initialized.")
    return row


def _audit(
    db: Session, actor: User, project_id: int, action: str, values: dict[str, object]
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="project_support_handover",
            entity_id=str(project_id),
            action=action,
            new_values_json=json.dumps(values, default=str),
        )
    )


def _recalculate(db: Session, handover: ProjectSupportHandover) -> list[ProjectHandoverItem]:
    items = list(
        db.scalars(
            select(ProjectHandoverItem)
            .join(
                ProjectHandoverSection, ProjectHandoverSection.id == ProjectHandoverItem.section_id
            )
            .where(ProjectHandoverSection.handover_id == handover.id)
        )
    )
    required = [item for item in items if item.is_required]
    missing = [item for item in required if item.status != "READY"]
    handover.readiness_percent = (
        (len(required) - len(missing)) * 100 // len(required)
        if required
        else 100
    )
    section_ids = list(
        db.scalars(
            select(ProjectHandoverSection.id).where(
                ProjectHandoverSection.handover_id == handover.id
            )
        )
    )
    for section_id in section_ids:
        section = db.get(ProjectHandoverSection, section_id)
        section_items = [item for item in items if item.section_id == section_id]
        if section:
            section.status = (
                "READY"
                if section_items
                and all(item.status == "READY" for item in section_items if item.is_required)
                else "IN_PROGRESS"
                if any(item.status != "NOT_READY" for item in section_items)
                else "NOT_STARTED"
            )
    return missing


def _receiving_departments(db: Session, project_id: int) -> list[ProjectDepartment]:
    return list(db.scalars(select(ProjectDepartment).where(
        ProjectDepartment.project_id == project_id, ProjectDepartment.role == "SUPPORT",
    )))


def _require_receiving_scope(db: Session, actor: User, project_id: int) -> None:
    departments = _receiving_departments(db, project_id)
    if departments and actor.department_id not in {row.department_id for row in departments} and (
        "project.manage" not in effective_permissions(db, actor).permissions
    ):
        raise NotFoundError("Support handover is outside your receiving department.")

@router.get("/projects/{project_id}/handover-routing")
def get_handover_routing(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("handover.view")),
) -> dict[str, Any]:
    project = require_project_access(db, actor, project_id)
    permissions = effective_permissions(db, actor).permissions
    can_edit = (
        "handover.prepare" in permissions
        and (project.project_manager_user_id == actor.id or "project.manage" in permissions)
        and project.status in {"DELIVERY_REVIEW", "HANDOVER_PREPARATION"}
    )
    receivers = _receiving_departments(db, project_id)
    receiver = db.get(Department, receivers[0].department_id) if len(receivers) == 1 else None
    return {
        "department": {"id": receiver.id, "name": receiver.name} if receiver else None,
        "can_edit": can_edit and len(receivers) <= 1,
        "options": [
            {"id": department.id, "name": department.name}
            for department in db.scalars(select(Department).where(Department.is_active == true()).order_by(Department.name))
        ] if can_edit and len(receivers) <= 1 else [],
    }


@router.put("/projects/{project_id}/handover-routing")
def set_handover_routing(
    project_id: int,
    data: HandoverRoutingWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("handover.prepare")),
) -> dict[str, int]:
    project = require_project_access(db, actor, project_id)
    if project.project_manager_user_id != actor.id and "project.manage" not in effective_permissions(db, actor).permissions:
        raise NotFoundError("Project does not exist.")
    result = db.connection().execute(update(CompanyProject).where(
        CompanyProject.id == project_id,
        CompanyProject.status.in_(["DELIVERY_REVIEW", "HANDOVER_PREPARATION"]),
    ).values(row_version=CompanyProject.row_version))
    if result.rowcount != 1:
        raise ConflictError("HANDOVER_ROUTING_CLOSED", "Set the receiving department before Support review.")
    receivers = _receiving_departments(db, project_id)
    previous = receivers[0].department_id if len(receivers) == 1 else None
    if len(receivers) > 1 or previous != data.expected_department_id:
        raise ConflictError("HANDOVER_ROUTING_CONFLICT", "Refresh the project before changing routing.")
    department = db.get(Department, data.department_id)
    if department is None or not department.is_active:
        raise NotFoundError("Receiving department does not exist.")
    if receivers:
        receivers[0].department_id = department.id
    else:
        db.add(ProjectDepartment(project_id=project_id, department_id=department.id, role="SUPPORT"))
    _audit(db, actor, project_id, "project.handover.routed", {
        "previous_department_id": previous, "department_id": department.id,
    })
    db.commit()
    return {"department_id": department.id}


@router.get("/project-handover-inbox")
def handover_inbox(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("handover.review")),
) -> list[dict[str, Any]]:
    statement = (
        select(ProjectSupportHandover, CompanyProject)
        .join(CompanyProject, CompanyProject.id == ProjectSupportHandover.project_id)
        .where(
            CompanyProject.id.in_(authorized_project_ids(db, actor)),
            ProjectSupportHandover.status.in_(["SUBMITTED", "ACCEPTED", "CONDITIONALLY_ACCEPTED", "ACTIVE"]),
        )
        .order_by(ProjectSupportHandover.updated_at.desc(), ProjectSupportHandover.id.desc())
        .limit(50)
    )
    if "project.manage" not in effective_permissions(db, actor).permissions:
        if actor.department_id is None:
            return []
        statement = statement.where(CompanyProject.id.in_(select(ProjectDepartment.project_id).where(
            ProjectDepartment.department_id == actor.department_id,
            ProjectDepartment.role == "SUPPORT",
        )))
    return [{
        "project_id": project.id, "project_number": project.project_number, "project_name": project.name,
        "status": handover.status, "readiness_percent": handover.readiness_percent,
        "submitted_at": handover.submitted_at,
    } for handover, project in db.execute(statement)]


@router.post("/projects/{project_id}/handover/initialize", status_code=status.HTTP_201_CREATED)
def initialize(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("handover.prepare")),
) -> dict[str, Any]:
    project = _project(db, project_id, actor)
    existing = db.scalar(
        select(ProjectSupportHandover).where(ProjectSupportHandover.project_id == project_id)
    )
    if existing:
        raise ConflictError("HANDOVER_ALREADY_INITIALIZED", "Support handover already exists.")
    if project.status not in {"DELIVERY_REVIEW", "ACTIVE"}:
        raise ConflictError(
            "HANDOVER_PROJECT_NOT_READY",
            "Complete Implementation delivery review before preparing Support handover.",
        )
    transition_project(
        db,
        project,
        actor,
        "HANDOVER_PREPARATION",
        source="SUPPORT_HANDOVER",
    )
    handover = ProjectSupportHandover(project_id=project_id, created_by_user_id=actor.id)
    db.add(handover)
    db.flush()
    for order, (code, title, items) in enumerate(DEFAULT_SECTIONS, 1):
        section = ProjectHandoverSection(
            handover_id=handover.id, code=code, title=title, display_order=order
        )
        db.add(section)
        db.flush()
        for item_title, required, evidence in items:
            db.add(
                ProjectHandoverItem(
                    section_id=section.id,
                    title=item_title,
                    is_required=required,
                    requires_evidence=evidence,
                )
            )
    _audit(db, actor, project_id, "project.handover.initialized", {})
    db.commit()
    return {"id": handover.id, "status": handover.status}


@router.get("/projects/{project_id}/handover")
def get_handover(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("handover.view")),
) -> dict[str, Any]:
    handover = _handover(db, project_id, actor)
    sections = list(
        db.scalars(
            select(ProjectHandoverSection)
            .where(ProjectHandoverSection.handover_id == handover.id)
            .order_by(ProjectHandoverSection.display_order)
        )
    )
    section_values = []
    for section in sections:
        item = _values(section)
        item["items"] = [
            _values(x)
            for x in db.scalars(
                select(ProjectHandoverItem)
                .where(ProjectHandoverItem.section_id == section.id)
                .order_by(ProjectHandoverItem.id)
            )
        ]
        section_values.append(item)
    decisions = list(
        db.scalars(
            select(ProjectHandoverDecision)
            .where(ProjectHandoverDecision.handover_id == handover.id)
            .order_by(ProjectHandoverDecision.created_at.desc())
        )
    )
    plan = db.scalar(
        select(ProjectStabilizationPlan).where(ProjectStabilizationPlan.handover_id == handover.id)
    )
    residual = list(
        db.scalars(
            select(ProjectHandoverResidualItem)
            .where(ProjectHandoverResidualItem.handover_id == handover.id)
            .order_by(ProjectHandoverResidualItem.target_date)
        )
    )
    result = _values(handover)
    result.update(
        {
            "sections": section_values,
            "decisions": [_values(x) for x in decisions],
            "stabilization_plan": _values(plan) if plan else None,
            "residual_items": [_values(x) for x in residual],
        }
    )
    return result


@router.patch("/handover-items/{item_id}")
def update_item(
    item_id: int,
    data: HandoverItemUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("handover.prepare")),
) -> dict[str, Any]:
    item = db.get(ProjectHandoverItem, item_id)
    if not item:
        raise NotFoundError("Readiness item does not exist.")
    section = db.get(ProjectHandoverSection, item.section_id)
    handover = db.get(ProjectSupportHandover, section.handover_id if section else 0)
    if not handover:
        raise NotFoundError("Support handover does not exist.")
    require_project_access(db, actor, handover.project_id)
    item_status = data.status.upper()
    if item_status not in {"NOT_READY", "IN_PROGRESS", "READY", "BLOCKED", "NOT_APPLICABLE"}:
        raise ConflictError("INVALID_READINESS_STATUS", "Select a supported readiness status.")
    if item_status == "READY" and item.requires_evidence:
        evidence = db.get(ProjectEvidence, data.evidence_id) if data.evidence_id else None
        if not evidence or evidence.project_id != handover.project_id:
            raise ConflictError(
                "READINESS_EVIDENCE_REQUIRED", "Ready status requires evidence from this project."
            )
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    item.status = item_status
    item.updated_by_user_id = actor.id
    _recalculate(db, handover)
    _audit(
        db,
        actor,
        handover.project_id,
        "project.handover.item_updated",
        {"item_id": item.id, "status": item_status},
    )
    db.commit()
    db.refresh(item)
    return _values(item)


@router.post("/projects/{project_id}/handover/submit")
def submit(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("handover.submit")),
) -> dict[str, Any]:
    handover = _handover(db, project_id, actor)
    missing = _recalculate(db, handover)
    if missing:
        raise ConflictError(
            "HANDOVER_NOT_READY",
            f"Complete the {len(missing)} remaining mandatory handover item(s).",
        )
    handover.status = "SUBMITTED"
    handover.submitted_by_user_id = actor.id
    handover.submitted_at = server_now()
    project = _project(db, project_id, actor)
    transition_project(
        db,
        project,
        actor,
        "SUPPORT_REVIEW",
        source="SUPPORT_HANDOVER",
    )
    receiver_ids = {row.department_id for row in _receiving_departments(db, project_id)}
    if receiver_ids:
        reviewers = db.scalars(select(User).where(
            User.department_id.in_(receiver_ids), User.is_active == true(),
            User.user_type == "EMPLOYEE", User.id != actor.id,
        ))
        for reviewer in reviewers:
            if {"handover.review", "handover.view", "project.portfolio.view"} <= set(
                effective_permissions(db, reviewer).permissions
            ):
                db.add(Notification(
                    recipient_user_id=reviewer.id,
                    notification_type="PROJECT_HANDOVER_SUBMITTED",
                    title=f"Support review needed for {project.project_number}",
                    message="A delivery handover is ready for your department to review.",
                    deep_link=f"/projects/{project_id}/handover",
                    deduplication_key=f"project-handover:{handover.id}:submitted:{project.row_version}:{reviewer.id}",
                ))
    _audit(
        db,
        actor,
        project_id,
        "project.handover.submitted",
        {"readiness_percent": handover.readiness_percent},
    )
    db.commit()
    db.refresh(handover)
    return _values(handover)


@router.post("/projects/{project_id}/handover/support-decision")
def support_decision(
    project_id: int,
    data: HandoverDecisionWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("handover.review")),
) -> dict[str, Any]:
    handover = _handover(db, project_id, actor)
    _require_receiving_scope(db, actor, project_id)
    decision = data.decision.upper()
    if decision in {"ACCEPT", "CONDITIONAL_ACCEPT"} and (
        "handover.accept" not in effective_permissions(db, actor).permissions
    ):
        raise AuthorizationError("Accepting a Support handover requires handover acceptance permission.")
    statuses = {
        "ACCEPT": "ACCEPTED",
        "CONDITIONAL_ACCEPT": "CONDITIONALLY_ACCEPTED",
        "REQUEST_CHANGES": "CHANGES_REQUESTED",
        "REJECT": "REJECTED",
    }
    if handover.status not in {"SUBMITTED", "CHANGES_REQUESTED"} or decision not in statuses:
        raise ConflictError(
            "INVALID_HANDOVER_DECISION",
            "Submitted handover can be accepted, conditionally accepted, returned, or rejected.",
        )
    handover.status = statuses[decision]
    row = ProjectHandoverDecision(
        handover_id=handover.id, decision=decision, notes=data.notes, decided_by_user_id=actor.id
    )
    db.add(row)
    project = _project(db, project_id, actor)
    if decision in {"REQUEST_CHANGES", "REJECT"}:
        transition_project(
            db,
            project,
            actor,
            "HANDOVER_PREPARATION",
            reason=data.notes or "Support requested handover changes.",
            source="SUPPORT_HANDOVER",
        )
    db.add(
        Notification(
            recipient_user_id=handover.submitted_by_user_id or project.project_manager_user_id,
            notification_type="PROJECT_HANDOVER_DECISION",
            severity="WARNING" if decision in {"REQUEST_CHANGES", "REJECT"} else "INFO",
            title=f"Support handover {handover.status.replace('_', ' ').lower()}",
            message=data.notes[:1000],
            deep_link=f"/projects/{project_id}/handover",
            deduplication_key=f"project-handover:{handover.id}:decision:{row.id}",
        )
    )
    _audit(db, actor, project_id, "project.handover.decided", {"decision": decision})
    db.commit()
    return _values(row)


@router.put("/projects/{project_id}/handover/stabilization")
def put_stabilization(
    project_id: int,
    data: StabilizationPlanWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("handover.prepare")),
) -> dict[str, Any]:
    handover = _handover(db, project_id, actor)
    if not db.get(User, data.implementation_owner_user_id) or not db.get(
        User, data.support_owner_user_id
    ):
        raise NotFoundError("A stabilization owner does not exist.")
    row = db.scalar(
        select(ProjectStabilizationPlan).where(ProjectStabilizationPlan.handover_id == handover.id)
    )
    if row:
        for key, value in data.model_dump().items():
            setattr(row, key, value)
    else:
        row = ProjectStabilizationPlan(handover_id=handover.id, **data.model_dump())
        db.add(row)
    _audit(db, actor, project_id, "project.handover.stabilization_saved", data.model_dump())
    db.commit()
    db.refresh(row)
    return _values(row)


@router.post("/projects/{project_id}/handover/residual-items", status_code=201)
def add_residual(
    project_id: int,
    data: ResidualItemWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("handover.prepare")),
) -> dict[str, Any]:
    handover = _handover(db, project_id, actor)
    if not db.get(Department, data.owner_department_id) or not db.get(User, data.owner_user_id):
        raise NotFoundError("Residual-work owner does not exist.")
    row = ProjectHandoverResidualItem(handover_id=handover.id, **data.model_dump())
    db.add(row)
    _audit(
        db,
        actor,
        project_id,
        "project.handover.residual_added",
        {"severity": data.severity, "target_date": data.target_date},
    )
    db.commit()
    db.refresh(row)
    return _values(row)


@router.post("/handover/residual-items/{item_id}/close")
def close_residual_item(
    item_id: int,
    data: ResidualCloseWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("handover.prepare")),
) -> dict[str, Any]:
    row = db.get(ProjectHandoverResidualItem, item_id)
    if not row:
        raise NotFoundError("Residual-work item does not exist.")
    handover = db.get(ProjectSupportHandover, row.handover_id)
    if not handover:
        raise NotFoundError("Support handover does not exist.")
    require_project_access(db, actor, handover.project_id)
    if row.status == "CLOSED":
        raise ConflictError("RESIDUAL_ALREADY_CLOSED", "Residual-work item is already closed.")
    row.status = "CLOSED"
    _audit(
        db,
        actor,
        handover.project_id,
        "project.handover.residual_closed",
        {"residual_item_id": row.id, "notes": data.notes},
    )
    db.commit()
    db.refresh(row)
    return _values(row)


@router.post("/projects/{project_id}/handover/activate-support")
def activate_support(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("handover.activate_support")),
) -> dict[str, Any]:
    handover = _handover(db, project_id, actor)
    _require_receiving_scope(db, actor, project_id)
    if handover.status not in {"ACCEPTED", "CONDITIONALLY_ACCEPTED"}:
        raise ConflictError(
            "HANDOVER_ACCEPTANCE_REQUIRED", "Support must accept the handover before activation."
        )
    plan = db.scalar(
        select(ProjectStabilizationPlan).where(ProjectStabilizationPlan.handover_id == handover.id)
    )
    if not plan:
        raise ConflictError(
            "STABILIZATION_PLAN_REQUIRED",
            "Define stabilization dates, owners, review frequency, and exit criteria.",
        )
    if handover.status == "CONDITIONALLY_ACCEPTED":
        unowned = (
            db.scalar(
                select(func.count())
                .select_from(ProjectHandoverResidualItem)
                .where(
                    ProjectHandoverResidualItem.handover_id == handover.id,
                    ProjectHandoverResidualItem.status == "OPEN",
                )
            )
            or 0
        )
        if not unowned:
            raise ConflictError(
                "CONDITIONAL_RESIDUAL_REQUIRED",
                "Conditional acceptance requires at least one accountable residual item.",
            )
    handover.status = "ACTIVE"
    handover.activated_by_user_id = actor.id
    handover.activated_at = server_now()
    plan.status = "ACTIVE"
    project = _project(db, project_id, actor)
    transition_project(
        db,
        project,
        actor,
        "STABILIZATION",
        source="SUPPORT_HANDOVER",
    )
    client = db.get(Client, project.client_id)
    if client and client.support_started_at is None:
        client.support_started_at = server_today()
    _audit(
        db,
        actor,
        project_id,
        "project.handover.support_activated",
        {"stabilization_end": plan.end_date},
    )
    db.commit()
    db.refresh(handover)
    return _values(handover)


@router.post("/projects/{project_id}/handover/complete-stabilization")
def complete_stabilization(
    project_id: int,
    data: StabilizationCompleteWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("handover.activate_support")),
) -> dict[str, Any]:
    handover = _handover(db, project_id, actor)
    _require_receiving_scope(db, actor, project_id)
    project = _project(db, project_id, actor)
    if project.row_version != data.expected_project_version:
        raise ConflictError(
            "PROJECT_VERSION_CONFLICT",
            "This project changed since it was opened. Refresh and try again.",
        )
    plan = db.scalar(
        select(ProjectStabilizationPlan).where(ProjectStabilizationPlan.handover_id == handover.id)
    )
    if handover.status != "ACTIVE" or not plan or plan.status != "ACTIVE":
        raise ConflictError(
            "STABILIZATION_NOT_ACTIVE",
            "Support stabilization must be active before it can be completed.",
        )
    if server_today() < plan.end_date:
        raise ConflictError(
            "STABILIZATION_PERIOD_NOT_FINISHED",
            f"Stabilization is scheduled through {plan.end_date.isoformat()}.",
        )
    open_residual = (
        db.scalar(
            select(func.count())
            .select_from(ProjectHandoverResidualItem)
            .where(
                ProjectHandoverResidualItem.handover_id == handover.id,
                ProjectHandoverResidualItem.status != "CLOSED",
            )
        )
        or 0
    )
    if open_residual:
        raise ConflictError(
            "OPEN_RESIDUAL_WORK",
            "Close all accountable residual work before completing stabilization.",
        )
    handover.status = "COMPLETED"
    plan.status = "COMPLETED"
    transition_project(
        db,
        project,
        actor,
        "COMPLETED",
        reason=data.completion_notes,
        source="STABILIZATION_EXIT",
    )
    _audit(
        db,
        actor,
        project_id,
        "project.handover.stabilization_completed",
        {"completion_notes": data.completion_notes},
    )
    db.commit()
    db.refresh(handover)
    return _values(handover)
