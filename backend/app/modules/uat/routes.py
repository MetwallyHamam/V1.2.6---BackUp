import json
import uuid
from datetime import date, datetime
from typing import Any, Literal, cast

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, true, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now, server_timezone
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import Client, Product, ProductModule
from app.modules.contracts.models import Contract
from app.modules.iam.models import AuditLog, Department, Profile, User, UserProfile
from app.modules.iam.service import effective_permissions
from app.modules.notifications.models import Notification
from app.modules.tickets.models import Ticket, TicketStatus, TicketType
from app.modules.tickets.schemas import TicketCreate
from app.modules.tickets.service import create_ticket
from app.modules.uat.models import (
    UatChecklistCategory,
    UatChecklistTemplate,
    UatChecklistTemplateClient,
    UatChecklistVersion,
    UatChecklistVersionItem,
    UatClientSignoff,
    UatCycle,
    UatCycleParticipant,
    UatCycleTest,
    UatImplementationTask,
    UatSignoff,
    UatTestAttempt,
    UatTestCase,
    UatTestCaseStep,
)
from app.modules.uat.service import notify_defect_created

router = APIRouter(prefix="/uat", tags=["uat"])


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=server_timezone())


class StepInput(BaseModel):
    action: str = Field(min_length=1, max_length=4000)
    expected_result: str = Field(min_length=1, max_length=4000)


class CaseInput(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=250)
    product_id: int | None = None
    module_id: int | None = None
    feature_name: str | None = Field(default=None, max_length=150)
    description: str | None = None
    preconditions: str | None = None
    expected_result: str = Field(min_length=1)
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    is_mandatory: bool = True
    steps: list[StepInput] = Field(min_length=1)


class TemplateInput(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=250)
    description: str | None = None
    product_id: int | None = None
    category_id: int | None = None
    scope_type: Literal["GLOBAL", "CLIENT", "CONTRACT"] = "GLOBAL"
    client_id: int | None = None
    contract_id: int | None = None
    client_ids: list[int] = Field(default_factory=list)
    test_case_ids: list[int] = Field(min_length=1)
    section_names: dict[int, str] = Field(default_factory=dict)


class ChecklistCategoryInput(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=150)


class CycleInput(BaseModel):
    code: str | None = Field(default=None, max_length=80)
    title: str | None = Field(default=None, max_length=250)
    client_id: int
    contract_id: int | None = None
    product_id: int | None = None
    release_version: str = Field(min_length=1, max_length=100)
    environment: Literal[
        "UAT", "TEST", "STAGING", "PRE_PRODUCTION", "PRODUCTION_VALIDATION", "OTHER"
    ] = "UAT"
    coordinator_user_id: int
    engineer_user_ids: list[int] = Field(default_factory=list)
    coordinator_user_ids: list[int] = Field(default_factory=list)
    client_tester_user_ids: list[int] = Field(default_factory=list)
    start_date: date | None = None
    due_date: date | None = None
    description: str | None = None
    portal_visible: bool = False
    allow_client_testing: bool = False
    allow_client_pass: bool = False
    allow_client_fail: bool = False
    allow_client_blocked: bool = False
    allow_client_comments: bool = False
    allow_client_attachments: bool = False
    allow_client_create_ticket_from_failure: bool = False
    allow_client_view_linked_ticket: bool = False
    allow_client_signoff: bool = False
    client_approver_user_id: int | None = None
    client_coordinator_user_id: int | None = None
    template_ids: list[int] = Field(default_factory=list)
    test_case_ids: list[int] = Field(default_factory=list)


class CycleUpdateInput(BaseModel):
    release_version: str = Field(min_length=1, max_length=100)
    coordinator_user_id: int
    engineer_user_ids: list[int] = Field(default_factory=list)
    coordinator_user_ids: list[int] = Field(default_factory=list)
    client_tester_user_ids: list[int] = Field(default_factory=list)
    start_date: date | None = None
    due_date: date | None = None
    description: str | None = None
    portal_visible: bool = False
    allow_client_testing: bool = False
    allow_client_pass: bool = False
    allow_client_fail: bool = False
    allow_client_blocked: bool = False
    allow_client_comments: bool = False
    allow_client_attachments: bool = False
    allow_client_create_ticket_from_failure: bool = False
    allow_client_view_linked_ticket: bool = False
    allow_client_signoff: bool = False
    client_approver_user_id: int | None = None
    client_coordinator_user_id: int | None = None


class AdHocTestInput(BaseModel):
    title: str = Field(min_length=1, max_length=250)
    preconditions: str | None = None
    expected_result: str = Field(min_length=1)
    feature_name: str | None = Field(default=None, max_length=150)
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    is_mandatory: bool = True
    steps: list[StepInput] = Field(min_length=1)


class AddTestsInput(BaseModel):
    template_ids: list[int] = Field(default_factory=list)
    test_case_ids: list[int] = Field(default_factory=list)
    ad_hoc_tests: list[AdHocTestInput] = Field(default_factory=list)


class TestOrderInput(BaseModel):
    test_ids: list[int] = Field(min_length=1)


class ExecuteInput(BaseModel):
    result: Literal["PASS", "FAIL", "BLOCKED"]
    actual_result: str = ""
    comment: str | None = None
    failure_reason: str | None = None
    blocking_reason: str | None = None
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    failure_category: (
        Literal[
            "Software Bug",
            "Configuration",
            "Integration",
            "Environment",
            "Permission",
            "Data",
            "Performance",
            "Workflow",
            "User Misunderstanding",
            "Other",
        ]
        | None
    ) = None


class WorkflowMoveInput(BaseModel):
    workflow_status: Literal["READY", "IN_PROGRESS"]


class DefectTicketInput(BaseModel):
    subject: str = Field(min_length=5, max_length=300)
    description: str = Field(min_length=10, max_length=20000)
    impact: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    urgency: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    entitlement_override_reason: str | None = None


class SignoffRequestInput(BaseModel):
    comment: str | None = Field(default=None, max_length=4000)


class SignoffDecisionInput(BaseModel):
    comment: str | None = Field(default=None, max_length=4000)
    acceptance_notes: str | None = Field(default=None, max_length=4000)


class PortalSettingsInput(BaseModel):
    portal_visible: bool = False
    allow_client_testing: bool = False
    allow_client_pass: bool = False
    allow_client_fail: bool = False
    allow_client_blocked: bool = False
    allow_client_view_linked_ticket: bool = False
    allow_client_signoff: bool = False
    allow_client_comments: bool = False
    allow_client_attachments: bool = False
    allow_client_create_ticket_from_failure: bool = False
    client_approver_user_id: int | None = None
    client_coordinator_user_id: int | None = None
    client_access_start_at: datetime | None = None
    client_access_end_at: datetime | None = None


class ClientTesterInput(BaseModel):
    user_id: int | None = None


class DuplicateUatInput(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=250)


class BulkTestsInput(BaseModel):
    test_ids: list[int] = Field(min_length=1, max_length=100)
    action: Literal["ASSIGN_OWNER", "SET_DUE_DATE", "SET_PRIORITY", "MOVE_READY"]
    owner_user_id: int | None = None
    due_date: date | None = None
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None


class ProgressInput(BaseModel):
    backend_status: str
    frontend_status: str
    database_status: str
    testing_status: str
    overall_status: str
    notes: str | None = None


class ProgressCreate(BaseModel):
    feature_area: str = Field(min_length=1, max_length=150)
    description: str | None = None


PROGRESS_STATUSES = {
    "NOT_STARTED",
    "IN_PROGRESS",
    "COMPLETED",
    "BLOCKED",
    "NEEDS_REVIEW",
    "DEFERRED",
}


def _audit(db: Session, actor: User, entity: str, entity_id: int, action: str) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor.id, entity_type=entity, entity_id=str(entity_id), action=action
        )
    )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("UAT_DUPLICATE", "A UAT code or version already exists.") from exc


def _flush(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("UAT_DUPLICATE", "A UAT code or version already exists.") from exc


def _case_snapshot(db: Session, test_case: UatTestCase) -> dict[str, object]:
    steps = list(
        db.scalars(
            select(UatTestCaseStep)
            .where(UatTestCaseStep.test_case_id == test_case.id)
            .order_by(UatTestCaseStep.step_order)
        )
    )
    return {
        "code": test_case.code,
        "title": test_case.title,
        "product_id": test_case.product_id,
        "module_id": test_case.module_id,
        "feature_name": test_case.feature_name,
        "description": test_case.description,
        "preconditions": test_case.preconditions,
        "expected_result": test_case.expected_result,
        "priority": test_case.priority,
        "is_mandatory": test_case.is_mandatory,
        "source_version": test_case.version,
        "steps": [
            {
                "order": step.step_order,
                "action": step.action,
                "expected_result": step.expected_result,
            }
            for step in steps
        ],
    }


def _case_read(db: Session, row: UatTestCase) -> dict[str, object]:
    return {
        "id": row.id,
        "is_active": row.is_active,
        "version": row.version,
        **_case_snapshot(db, row),
    }


def _validate_case_references(db: Session, data: CaseInput) -> None:
    if data.product_id and not db.get(Product, data.product_id):
        raise NotFoundError("Product does not exist.")
    if data.module_id:
        module = db.get(ProductModule, data.module_id)
        if not module or (data.product_id and module.product_id != data.product_id):
            raise ConflictError("INVALID_UAT_MODULE", "Module must belong to the selected product.")


@router.get("/metadata")
def metadata(
    db: Session = Depends(get_db), _actor: User = Depends(require_permission("uat.view"))
) -> dict[str, object]:
    return {
        "clients": [
            {"id": row.id, "name": row.name}
            for row in db.scalars(select(Client).order_by(Client.name))
        ],
        "contracts": [
            {"id": row.id, "client_id": row.client_id, "name": row.name}
            for row in db.scalars(select(Contract).order_by(Contract.name))
        ],
        "products": [
            {"id": row.id, "name": row.name}
            for row in db.scalars(select(Product).order_by(Product.name))
        ],
        "modules": [
            {"id": row.id, "product_id": row.product_id, "name": row.name}
            for row in db.scalars(select(ProductModule).order_by(ProductModule.name))
        ],
        "users": [
            {
                "id": row.id,
                "name": row.full_name,
                "user_type": row.user_type,
                "department": row.department,
                "client_ids": effective_permissions(db, row).client_scope_ids
                if row.user_type == "CLIENT_PORTAL"
                else [],
            }
            for row in db.scalars(
                select(User).where(User.is_active == true()).order_by(User.full_name)
            )
        ],
    }


@router.get("/test-cases")
def list_cases(
    db: Session = Depends(get_db), _actor: User = Depends(require_permission("uat.view"))
) -> list[dict[str, object]]:
    return [
        _case_read(db, row) for row in db.scalars(select(UatTestCase).order_by(UatTestCase.code))
    ]


@router.post("/test-cases", status_code=status.HTTP_201_CREATED)
def create_case(
    data: CaseInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.library.manage")),
) -> dict[str, object]:
    _validate_case_references(db, data)
    row = UatTestCase(**data.model_dump(exclude={"steps"}), created_by_user_id=actor.id)
    db.add(row)
    _flush(db)
    for order, step in enumerate(data.steps, 1):
        db.add(UatTestCaseStep(test_case_id=row.id, step_order=order, **step.model_dump()))
    _audit(db, actor, "UatTestCase", row.id, "uat.test_case.created")
    _commit(db)
    return _case_read(db, row)


@router.put("/test-cases/{case_id}")
def update_case(
    case_id: int,
    data: CaseInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.library.manage")),
) -> dict[str, object]:
    row = db.get(UatTestCase, case_id)
    if not row or not row.is_active:
        raise NotFoundError("UAT test case does not exist.")
    _validate_case_references(db, data)
    for key, value in data.model_dump(exclude={"steps"}).items():
        setattr(row, key, value)
    row.version += 1
    for existing_step in db.scalars(
        select(UatTestCaseStep).where(UatTestCaseStep.test_case_id == row.id)
    ):
        db.delete(existing_step)
    _flush(db)
    for order, step in enumerate(data.steps, 1):
        db.add(UatTestCaseStep(test_case_id=row.id, step_order=order, **step.model_dump()))
    _audit(db, actor, "UatTestCase", row.id, "uat.test_case.updated")
    _commit(db)
    return _case_read(db, row)


@router.post("/test-cases/{case_id}/archive")
def archive_case(
    case_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.library.manage")),
) -> dict[str, object]:
    row = db.get(UatTestCase, case_id)
    if not row:
        raise NotFoundError("UAT test case does not exist.")
    row.is_active = False
    _audit(db, actor, "UatTestCase", row.id, "uat.test_case.archived")
    _commit(db)
    return _case_read(db, row)


@router.delete("/test-cases/{case_id}")
def remove_case(
    case_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.library.manage")),
) -> dict[str, object]:
    row = db.get(UatTestCase, case_id)
    if not row:
        raise NotFoundError("UAT test case does not exist.")
    used = db.scalar(
        select(UatCycleTest.id).where(UatCycleTest.test_case_id == case_id)
    ) or db.scalar(
        select(UatChecklistVersionItem.id).where(UatChecklistVersionItem.test_case_id == case_id)
    )
    if used:
        row.is_active = False
        _audit(db, actor, "UatTestCase", row.id, "uat.test_case.archived_on_removal")
        _commit(db)
        return {
            "deleted": False,
            "archived": True,
            "message": "This test case has historical UAT records and was archived.",
        }
    for step in db.scalars(select(UatTestCaseStep).where(UatTestCaseStep.test_case_id == case_id)):
        db.delete(step)
    db.delete(row)
    _audit(db, actor, "UatTestCase", case_id, "uat.test_case.deleted")
    _commit(db)
    return {"deleted": True, "archived": False, "message": "Unused test case deleted."}


@router.post("/test-cases/{case_id}/duplicate", status_code=status.HTTP_201_CREATED)
def duplicate_case(
    case_id: int,
    data: DuplicateUatInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.library.manage")),
) -> dict[str, object]:
    source = db.get(UatTestCase, case_id)
    if not source:
        raise NotFoundError("UAT test case does not exist.")
    row = UatTestCase(
        code=data.code,
        title=data.name,
        product_id=source.product_id,
        module_id=source.module_id,
        feature_name=source.feature_name,
        description=source.description,
        preconditions=source.preconditions,
        expected_result=source.expected_result,
        priority=source.priority,
        is_mandatory=source.is_mandatory,
        created_by_user_id=actor.id,
    )
    db.add(row)
    _flush(db)
    for step in db.scalars(
        select(UatTestCaseStep)
        .where(UatTestCaseStep.test_case_id == source.id)
        .order_by(UatTestCaseStep.step_order)
    ):
        db.add(
            UatTestCaseStep(
                test_case_id=row.id,
                step_order=step.step_order,
                action=step.action,
                expected_result=step.expected_result,
            )
        )
    _audit(db, actor, "UatTestCase", row.id, "uat.test_case.duplicated")
    _commit(db)
    return _case_read(db, row)


def _template_read(db: Session, row: UatChecklistTemplate) -> dict[str, object]:
    version = db.scalar(
        select(UatChecklistVersion).where(
            UatChecklistVersion.template_id == row.id,
            UatChecklistVersion.version == row.current_version,
        )
    )
    items = (
        list(
            db.scalars(
                select(UatChecklistVersionItem)
                .where(UatChecklistVersionItem.version_id == version.id)
                .order_by(UatChecklistVersionItem.display_order)
            )
        )
        if version
        else []
    )
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "description": row.description,
        "product_id": row.product_id,
        "category_id": row.category_id,
        "scope_type": row.scope_type,
        "client_id": row.client_id,
        "contract_id": row.contract_id,
        "client_ids": list(
            db.scalars(
                select(UatChecklistTemplateClient.client_id)
                .where(UatChecklistTemplateClient.template_id == row.id)
                .order_by(UatChecklistTemplateClient.client_id)
            )
        ),
        "current_version": row.current_version,
        "is_active": row.is_active,
        "test_case_ids": [item.test_case_id for item in items],
        "section_names": {
            item.test_case_id: item.section_name for item in items if item.section_name
        },
    }


def _validate_template(
    db: Session, data: TemplateInput, current_category_id: int | None = None
) -> list[UatTestCase]:
    if len(set(data.test_case_ids)) != len(data.test_case_ids):
        raise ConflictError(
            "DUPLICATE_UAT_CASE", "A checklist cannot contain the same test case twice."
        )
    if set(data.section_names) - set(data.test_case_ids):
        raise ConflictError(
            "INVALID_UAT_SECTION", "A section may only contain a selected test case."
        )
    if any(not name.strip() or len(name.strip()) > 150 for name in data.section_names.values()):
        raise ConflictError(
            "INVALID_UAT_SECTION", "Section names must be between 1 and 150 characters."
        )
    if len(set(data.client_ids)) != len(data.client_ids):
        raise ConflictError("DUPLICATE_UAT_CLIENT", "Select each client once.")
    if data.client_ids and set(
        db.scalars(select(Client.id).where(Client.id.in_(data.client_ids)))
    ) != set(data.client_ids):
        raise NotFoundError("A selected client does not exist.")
    if data.category_id:
        category = db.get(UatChecklistCategory, data.category_id)
        if not category or (not category.is_active and data.category_id != current_category_id):
            raise NotFoundError("Active UAT checklist category does not exist.")
    if data.scope_type == "GLOBAL" and (data.client_id or data.contract_id):
        raise ConflictError(
            "INVALID_UAT_SCOPE", "Global checklists cannot have a client or contract."
        )
    if data.scope_type in {"CLIENT", "CONTRACT"} and not data.client_id:
        raise ConflictError("INVALID_UAT_SCOPE", "Client-scoped checklists require a client.")
    if data.scope_type == "CONTRACT":
        contract = db.get(Contract, data.contract_id) if data.contract_id else None
        if not contract or (
            not contract.applies_to_all_clients and data.client_id not in contract.customer_ids
        ):
            raise ConflictError("INVALID_UAT_SCOPE", "Contract must belong to the selected client.")
    elif data.contract_id:
        raise ConflictError(
            "INVALID_UAT_SCOPE", "Only contract-scoped checklists may select a contract."
        )
    cases = [db.get(UatTestCase, case_id) for case_id in data.test_case_ids]
    if any(case is None or not case.is_active for case in cases):
        raise NotFoundError("An active UAT test case was not found.")
    return [case for case in cases if case is not None]


def _new_template_version(
    db: Session,
    row: UatChecklistTemplate,
    cases: list[UatTestCase],
    actor: User,
    section_names: dict[int, str] | None = None,
) -> None:
    version = UatChecklistVersion(
        template_id=row.id, version=row.current_version, created_by_user_id=actor.id
    )
    db.add(version)
    _flush(db)
    for order, case in enumerate(cases, 1):
        db.add(
            UatChecklistVersionItem(
                version_id=version.id,
                test_case_id=case.id,
                display_order=order,
                section_name=(section_names or {}).get(case.id),
                snapshot_json=json.dumps(_case_snapshot(db, case), ensure_ascii=False),
            )
        )


def _replace_current_template_items(
    db: Session,
    row: UatChecklistTemplate,
    cases: list[UatTestCase],
    section_names: dict[int, str],
) -> None:
    version = db.scalar(
        select(UatChecklistVersion).where(
            UatChecklistVersion.template_id == row.id,
            UatChecklistVersion.version == row.current_version,
        )
    )
    if not version:
        raise NotFoundError("Current UAT checklist version does not exist.")
    db.query(UatChecklistVersionItem).filter(
        UatChecklistVersionItem.version_id == version.id
    ).delete(synchronize_session=False)
    _flush(db)
    for order, case in enumerate(cases, 1):
        db.add(
            UatChecklistVersionItem(
                version_id=version.id,
                test_case_id=case.id,
                display_order=order,
                section_name=section_names.get(case.id),
                snapshot_json=json.dumps(_case_snapshot(db, case), ensure_ascii=False),
            )
        )


def _replace_template_clients(db: Session, template_id: int, client_ids: list[int]) -> None:
    db.query(UatChecklistTemplateClient).filter(
        UatChecklistTemplateClient.template_id == template_id
    ).delete()
    db.add_all(
        UatChecklistTemplateClient(template_id=template_id, client_id=client_id)
        for client_id in client_ids
    )


@router.get("/checklist-categories")
def list_checklist_categories(
    db: Session = Depends(get_db), _actor: User = Depends(require_permission("uat.view"))
) -> list[dict[str, object]]:
    return [
        {"id": row.id, "code": row.code, "name": row.name, "is_active": row.is_active}
        for row in db.scalars(select(UatChecklistCategory).order_by(UatChecklistCategory.name))
    ]


@router.post("/checklist-categories", status_code=status.HTTP_201_CREATED)
def create_checklist_category(
    data: ChecklistCategoryInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.library.manage")),
) -> dict[str, object]:
    if not data.code.strip() or not data.name.strip():
        raise ConflictError("INVALID_UAT_CATEGORY", "Category code and name are required.")
    row = UatChecklistCategory(code=data.code.strip().upper(), name=data.name.strip())
    db.add(row)
    _flush(db)
    _audit(db, actor, "UatChecklistCategory", row.id, "uat.checklist_category.created")
    _commit(db)
    return {"id": row.id, "code": row.code, "name": row.name, "is_active": row.is_active}


@router.put("/checklist-categories/{category_id}")
def update_checklist_category(
    category_id: int,
    data: ChecklistCategoryInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.library.manage")),
) -> dict[str, object]:
    if not data.code.strip() or not data.name.strip():
        raise ConflictError("INVALID_UAT_CATEGORY", "Category code and name are required.")
    row = db.get(UatChecklistCategory, category_id)
    if not row or not row.is_active:
        raise NotFoundError("Active UAT checklist category does not exist.")
    row.code = data.code.strip().upper()
    row.name = data.name.strip()
    _audit(db, actor, "UatChecklistCategory", row.id, "uat.checklist_category.updated")
    _commit(db)
    return {"id": row.id, "code": row.code, "name": row.name, "is_active": row.is_active}


@router.post("/checklist-categories/{category_id}/archive")
def archive_checklist_category(
    category_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.library.manage")),
) -> dict[str, object]:
    row = db.get(UatChecklistCategory, category_id)
    if not row:
        raise NotFoundError("UAT checklist category does not exist.")
    row.is_active = False
    _audit(db, actor, "UatChecklistCategory", row.id, "uat.checklist_category.archived")
    _commit(db)
    return {"id": row.id, "code": row.code, "name": row.name, "is_active": row.is_active}


@router.get("/templates")
def list_templates(
    db: Session = Depends(get_db), _actor: User = Depends(require_permission("uat.view"))
) -> list[dict[str, object]]:
    return [
        _template_read(db, row)
        for row in db.scalars(select(UatChecklistTemplate).order_by(UatChecklistTemplate.name))
    ]


@router.post("/templates", status_code=status.HTTP_201_CREATED)
def create_template(
    data: TemplateInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.library.manage")),
) -> dict[str, object]:
    cases = _validate_template(db, data)
    row = UatChecklistTemplate(
        **data.model_dump(exclude={"test_case_ids", "section_names", "client_ids"}),
        created_by_user_id=actor.id,
    )
    db.add(row)
    _flush(db)
    _new_template_version(db, row, cases, actor, data.section_names)
    _replace_template_clients(db, row.id, data.client_ids)
    _audit(db, actor, "UatChecklistTemplate", row.id, "uat.checklist.created")
    _commit(db)
    return _template_read(db, row)


@router.put("/templates/{template_id}")
def update_template(
    template_id: int,
    data: TemplateInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.library.manage")),
) -> dict[str, object]:
    row = db.get(UatChecklistTemplate, template_id)
    if not row or not row.is_active:
        raise NotFoundError("UAT checklist does not exist.")
    cases = _validate_template(db, data, row.category_id)
    for key, value in data.model_dump(
        exclude={"test_case_ids", "section_names", "client_ids"}
    ).items():
        setattr(row, key, value)
    _replace_current_template_items(db, row, cases, data.section_names)
    _replace_template_clients(db, row.id, data.client_ids)
    _audit(db, actor, "UatChecklistTemplate", row.id, "uat.checklist.updated")
    _commit(db)
    return _template_read(db, row)


@router.post("/templates/{template_id}/versions", status_code=status.HTTP_201_CREATED)
def create_template_version(
    template_id: int,
    data: TemplateInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.library.manage")),
) -> dict[str, object]:
    row = db.get(UatChecklistTemplate, template_id)
    if not row or not row.is_active:
        raise NotFoundError("UAT checklist does not exist.")
    cases = _validate_template(db, data, row.category_id)
    for key, value in data.model_dump(
        exclude={"test_case_ids", "section_names", "client_ids"}
    ).items():
        setattr(row, key, value)
    row.current_version += 1
    _new_template_version(db, row, cases, actor, data.section_names)
    _replace_template_clients(db, row.id, data.client_ids)
    _audit(db, actor, "UatChecklistTemplate", row.id, "uat.checklist.versioned")
    _commit(db)
    return _template_read(db, row)


@router.post("/templates/{template_id}/duplicate", status_code=status.HTTP_201_CREATED)
def duplicate_template(
    template_id: int,
    data: DuplicateUatInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.library.manage")),
) -> dict[str, object]:
    source = db.get(UatChecklistTemplate, template_id)
    if not source:
        raise NotFoundError("UAT checklist does not exist.")
    current = db.scalar(
        select(UatChecklistVersion).where(
            UatChecklistVersion.template_id == source.id,
            UatChecklistVersion.version == source.current_version,
        )
    )
    if not current:
        raise NotFoundError("UAT checklist version does not exist.")
    case_ids = list(
        db.scalars(
            select(UatChecklistVersionItem.test_case_id)
            .where(UatChecklistVersionItem.version_id == current.id)
            .order_by(UatChecklistVersionItem.display_order)
        )
    )
    cases = [db.get(UatTestCase, case_id) for case_id in case_ids]
    if any(case is None or not case.is_active for case in cases):
        raise ConflictError(
            "UAT_CHECKLIST_INACTIVE_CASE",
            "Activate or replace archived test cases before duplicating this checklist.",
        )
    row = UatChecklistTemplate(
        code=data.code,
        name=data.name,
        description=source.description,
        product_id=source.product_id,
        category_id=source.category_id,
        scope_type=source.scope_type,
        client_id=source.client_id,
        contract_id=source.contract_id,
        created_by_user_id=actor.id,
    )
    db.add(row)
    _flush(db)
    section_names = {
        item.test_case_id: item.section_name
        for item in db.scalars(
            select(UatChecklistVersionItem).where(UatChecklistVersionItem.version_id == current.id)
        )
        if item.section_name
    }
    _new_template_version(
        db, row, [case for case in cases if case is not None], actor, section_names
    )
    source_client_ids = list(
        db.scalars(
            select(UatChecklistTemplateClient.client_id).where(
                UatChecklistTemplateClient.template_id == source.id
            )
        )
    )
    _replace_template_clients(db, row.id, source_client_ids)
    _audit(db, actor, "UatChecklistTemplate", row.id, "uat.checklist.duplicated")
    _commit(db)
    return _template_read(db, row)


@router.post("/templates/{template_id}/archive")
def archive_template(
    template_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.library.manage")),
) -> dict[str, object]:
    row = db.get(UatChecklistTemplate, template_id)
    if not row:
        raise NotFoundError("UAT checklist does not exist.")
    row.is_active = False
    _audit(db, actor, "UatChecklistTemplate", row.id, "uat.checklist.archived")
    _commit(db)
    return _template_read(db, row)


def _cycle_read(db: Session, row: UatCycle) -> dict[str, object]:
    tests = list(
        db.scalars(
            select(UatCycleTest)
            .where(UatCycleTest.cycle_id == row.id)
            .order_by(UatCycleTest.display_order, UatCycleTest.id)
        )
    )
    participants = list(
        db.scalars(select(UatCycleParticipant).where(UatCycleParticipant.cycle_id == row.id))
    )
    ticket_numbers = {
        ticket.id: ticket.ticket_number
        for ticket in db.scalars(
            select(Ticket).where(
                Ticket.id.in_([item.linked_ticket_id for item in tests if item.linked_ticket_id])
            )
        )
    }
    return {
        "id": row.id,
        "code": row.code,
        "title": row.title,
        "client_id": row.client_id,
        "contract_id": row.contract_id,
        "product_id": row.product_id,
        "release_version": row.release_version,
        "environment": row.environment,
        "start_date": row.start_date,
        "due_date": row.due_date,
        "coordinator_user_id": row.coordinator_user_id,
        "description": row.description,
        "engineer_user_ids": [item.user_id for item in participants if item.role == "ENGINEER"],
        "coordinator_user_ids": [
            item.user_id for item in participants if item.role == "COORDINATOR"
        ],
        "client_tester_user_ids": sorted(
            {item.client_tester_user_id for item in tests if item.client_tester_user_id is not None}
        ),
        "status": row.status,
        "total_tests": len(tests),
        "portal_settings": {
            "portal_visible": row.portal_visible,
            "allow_client_testing": row.allow_client_testing,
            "allow_client_pass": row.allow_client_pass,
            "allow_client_fail": row.allow_client_fail,
            "allow_client_blocked": row.allow_client_blocked,
            "allow_client_view_linked_ticket": row.allow_client_view_linked_ticket,
            "allow_client_signoff": row.allow_client_signoff,
            "allow_client_comments": row.allow_client_comments,
            "allow_client_attachments": row.allow_client_attachments,
            "allow_client_create_ticket_from_failure": row.allow_client_create_ticket_from_failure,
            "client_approver_user_id": row.client_approver_user_id,
            "client_coordinator_user_id": row.client_coordinator_user_id,
            "client_access_start_at": row.client_access_start_at,
            "client_access_end_at": row.client_access_end_at,
        },
        "passed": sum(item.test_result == "PASS" for item in tests),
        "failed": sum(item.test_result == "FAIL" for item in tests),
        "tests": [
            {
                "id": item.id,
                "test_case_id": item.test_case_id,
                "display_order": item.display_order,
                "snapshot": json.loads(item.snapshot_json),
                "owner_user_id": item.owner_user_id,
                "client_tester_user_id": item.client_tester_user_id,
                "client_test_result": item.client_test_result,
                "client_workflow_status": item.client_workflow_status,
                "client_attempt_count": item.client_attempt_count,
                "due_date": item.due_date,
                "priority": item.priority_override or json.loads(item.snapshot_json)["priority"],
                "workflow_status": item.workflow_status,
                "test_result": item.test_result,
                "attempt_count": item.attempt_count,
                "retest_count": item.retest_count,
                "linked_ticket_id": item.linked_ticket_id,
                "linked_ticket_number": ticket_numbers.get(item.linked_ticket_id)
                if item.linked_ticket_id
                else None,
                "tested_at": item.tested_at,
            }
            for item in tests
        ],
    }


@router.get("/cycles")
def list_cycles(
    db: Session = Depends(get_db), _actor: User = Depends(require_permission("uat.view"))
) -> list[dict[str, object]]:
    return [
        _cycle_read(db, row)
        for row in db.scalars(select(UatCycle).order_by(UatCycle.created_at.desc()))
    ]


@router.get("/cycles/{cycle_id}")
def get_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    _actor: User = Depends(require_permission("uat.view")),
) -> dict[str, object]:
    row = db.get(UatCycle, cycle_id)
    if not row:
        raise NotFoundError("UAT cycle does not exist.")
    return _cycle_read(db, row)


@router.get("/cycles/{cycle_id}/dashboard")
def cycle_dashboard(
    cycle_id: int,
    db: Session = Depends(get_db),
    _actor: User = Depends(require_permission("uat.view")),
) -> dict[str, object]:
    cycle = db.get(UatCycle, cycle_id)
    if not cycle:
        raise NotFoundError("UAT cycle does not exist.")
    tests = list(db.scalars(select(UatCycleTest).where(UatCycleTest.cycle_id == cycle.id)))
    test_ids = [item.id for item in tests]
    attempts = (
        list(
            db.scalars(
                select(UatTestAttempt)
                .where(UatTestAttempt.cycle_test_id.in_(test_ids))
                .order_by(UatTestAttempt.attempt_number)
            )
        )
        if test_ids
        else []
    )
    latest = {attempt.cycle_test_id: attempt for attempt in attempts}
    linked_ids = [item.linked_ticket_id for item in tests if item.linked_ticket_id]
    tickets = (
        list(db.scalars(select(Ticket).where(Ticket.id.in_(linked_ids)))) if linked_ids else []
    )
    ticket_status_ids = {ticket.status_id for ticket in tickets}
    status_codes = (
        {
            row.id: row.code
            for row in db.scalars(
                select(TicketStatus).where(TicketStatus.id.in_(ticket_status_ids))
            )
        }
        if ticket_status_ids
        else {}
    )
    owner_ids = {item.owner_user_id for item in tests if item.owner_user_id}
    owner_names = (
        {user.id: user.full_name for user in db.scalars(select(User).where(User.id.in_(owner_ids)))}
        if owner_ids
        else {}
    )
    total = len(tests)
    passed = sum(item.test_result == "PASS" for item in tests)
    failed = sum(item.test_result == "FAIL" for item in tests)
    blocked = sum(item.test_result == "BLOCKED" for item in tests)
    status_counts: dict[str, int] = {}
    module_counts: dict[str, dict[str, int]] = {}
    owner_counts: dict[str, dict[str, int]] = {}
    severity_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for item in tests:
        status_counts[item.workflow_status] = status_counts.get(item.workflow_status, 0) + 1
        snapshot = json.loads(item.snapshot_json)
        module = (
            db.get(ProductModule, snapshot.get("module_id")) if snapshot.get("module_id") else None
        )
        module_name = module.name if module else "General"
        owner_name = (
            owner_names.get(item.owner_user_id, "Unassigned")
            if item.owner_user_id
            else "Unassigned"
        )
        for bucket, name in ((module_counts, module_name), (owner_counts, owner_name)):
            values = bucket.setdefault(name, {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "NOT_TESTED": 0})
            values[item.test_result] = values.get(item.test_result, 0) + 1
        current = latest.get(item.id)
        if item.test_result == "FAIL" and current:
            severity = current.severity or "UNKNOWN"
            category = current.failure_category or "Uncategorized"
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
    progress_by_date: dict[str, dict[str, int]] = {}
    for attempt in attempts:
        day = attempt.tested_at.date().isoformat()
        values = progress_by_date.setdefault(day, {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "RETEST": 0})
        values[attempt.result] = values.get(attempt.result, 0) + 1
        if attempt.attempt_number > 1:
            values["RETEST"] += 1
    open_defects = sum(
        status_codes.get(ticket.status_id) not in {"RESOLVED", "CLOSED", "CANCELLED"}
        for ticket in tickets
    )
    today = server_now().date()
    metrics = {
        "total": total,
        "completed": passed + failed,
        "completion_percent": round((passed + failed) * 100 / total, 1) if total else 0,
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "not_tested": sum(item.test_result == "NOT_TESTED" for item in tests),
        "overdue": sum(item.test_result != "PASS" for item in tests)
        if cycle.due_date and cycle.due_date < today and cycle.status == "ACTIVE"
        else 0,
        "pass_rate": round(passed * 100 / (passed + failed), 1) if passed + failed else 0,
        "critical_failures": sum(
            item.test_result == "FAIL"
            and latest.get(item.id) is not None
            and latest[item.id].severity == "CRITICAL"
            for item in tests
        ),
        "waiting_retest": status_counts.get("READY_FOR_RETEST", 0),
        "open_defects": open_defects,
    }
    return {
        "cycle_id": cycle.id,
        "metrics": metrics,
        "by_status": status_counts,
        "by_module": module_counts,
        "by_owner": owner_counts,
        "failures_by_severity": severity_counts,
        "failures_by_category": category_counts,
        "progress_by_date": progress_by_date,
    }


def _pending_signoff(db: Session, cycle_id: int) -> UatSignoff | None:
    return db.scalar(
        select(UatSignoff).where(UatSignoff.cycle_id == cycle_id, UatSignoff.status == "PENDING")
    )


def _signoff_summary(db: Session, cycle: UatCycle, actor: User) -> dict[str, object]:
    metrics = cycle_dashboard(cycle.id, db, actor)["metrics"]
    assert isinstance(metrics, dict)
    tests = list(db.scalars(select(UatCycleTest).where(UatCycleTest.cycle_id == cycle.id)))
    mandatory_incomplete = sum(
        json.loads(item.snapshot_json).get("is_mandatory", True) and item.test_result != "PASS"
        for item in tests
    )
    return {**metrics, "mandatory_incomplete": mandatory_incomplete}


def _signoff_read(row: UatSignoff) -> dict[str, object]:
    return {
        "id": row.id,
        "request_number": row.request_number,
        "status": row.status,
        "requested_by_user_id": row.requested_by_user_id,
        "requested_at": row.requested_at,
        "request_comment": row.request_comment,
        "summary_snapshot": json.loads(row.summary_snapshot_json),
        "decided_by_user_id": row.decided_by_user_id,
        "decided_at": row.decided_at,
        "decision_comment": row.decision_comment,
        "acceptance_notes": row.acceptance_notes,
    }


@router.get("/cycles/{cycle_id}/signoff")
def get_signoff(
    cycle_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.view")),
) -> dict[str, object]:
    cycle = db.get(UatCycle, cycle_id)
    if not cycle:
        raise NotFoundError("UAT cycle does not exist.")
    history = list(
        db.scalars(
            select(UatSignoff)
            .where(UatSignoff.cycle_id == cycle.id)
            .order_by(UatSignoff.request_number.desc())
        )
    )
    return {
        "status": history[0].status if history else "NOT_REQUESTED",
        "current_summary": _signoff_summary(db, cycle, actor),
        "history": [_signoff_read(row) for row in history],
    }


@router.post("/cycles/{cycle_id}/signoff/request", status_code=status.HTTP_201_CREATED)
def request_signoff(
    cycle_id: int,
    data: SignoffRequestInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.signoff.request")),
) -> dict[str, object]:
    cycle = db.get(UatCycle, cycle_id)
    if not cycle:
        raise NotFoundError("UAT cycle does not exist.")
    if cycle.status != "ACTIVE":
        raise ConflictError("INVALID_UAT_STATE", "Only active cycles can request sign-off.")
    if _pending_signoff(db, cycle.id):
        raise ConflictError(
            "UAT_SIGNOFF_PENDING", "This cycle already has a pending sign-off request."
        )
    summary = _signoff_summary(db, cycle, actor)
    if cycle.allow_client_signoff:
        client_decision = db.scalar(
            select(UatClientSignoff)
            .where(UatClientSignoff.cycle_id == cycle.id)
            .order_by(UatClientSignoff.decision_number.desc())
        )
        if not client_decision or client_decision.decision != "APPROVED":
            raise ConflictError(
                "UAT_CLIENT_SIGNOFF_REQUIRED",
                "The assigned client approver must approve before internal sign-off.",
            )
        approved_states = json.loads(client_decision.summary_snapshot_json).get("test_states", {})
        current_states = {
            str(test.id): test.client_test_result
            for test in db.scalars(
                select(UatCycleTest).where(
                    UatCycleTest.cycle_id == cycle.id,
                    UatCycleTest.client_tester_user_id.is_not(None),
                )
            )
        }
        if current_states != approved_states:
            raise ConflictError(
                "UAT_CLIENT_SIGNOFF_CHANGED",
                "Client tests changed after approval. Request a new client decision.",
            )
    if (
        not summary["total"]
        or summary["mandatory_incomplete"]
        or summary["failed"]
        or summary["blocked"]
        or summary["open_defects"]
    ):
        raise ConflictError(
            "UAT_SIGNOFF_NOT_READY",
            "Resolve failed and blocked tests, open defects, and incomplete mandatory tests before requesting sign-off.",
        )
    number = (
        db.scalar(
            select(func.max(UatSignoff.request_number)).where(UatSignoff.cycle_id == cycle.id)
        )
        or 0
    ) + 1
    row = UatSignoff(
        cycle_id=cycle.id,
        request_number=number,
        status="PENDING",
        requested_by_user_id=actor.id,
        requested_at=server_now(),
        request_comment=data.comment,
        summary_snapshot_json=json.dumps(summary),
    )
    db.add(row)
    _flush(db)
    approver_ids = set(
        db.scalars(
            select(User.id)
            .join(UserProfile, UserProfile.user_id == User.id)
            .join(Profile, Profile.id == UserProfile.profile_id)
            .where(
                Profile.code.in_(["TOP_MANAGEMENT", "ADMINISTRATOR"]),
                User.is_active == true(),
                User.id != actor.id,
            )
        )
    )
    for user_id in approver_ids:
        db.add(
            Notification(
                recipient_user_id=user_id,
                notification_type="UAT_SIGNOFF_REQUESTED",
                severity="INFO",
                title=f"UAT sign-off requested: {cycle.code}",
                message=f"{actor.full_name} requested sign-off for {cycle.title}.",
                deep_link="/uat",
                deduplication_key=f"uat-signoff-request:{row.id}:user:{user_id}",
            )
        )
    _audit(db, actor, "UatSignoff", row.id, "uat.signoff.requested")
    _commit(db)
    return _signoff_read(row)


def _decide_signoff(
    cycle_id: int, data: SignoffDecisionInput, decision: str, db: Session, actor: User
) -> dict[str, object]:
    cycle = db.get(UatCycle, cycle_id)
    if not cycle:
        raise NotFoundError("UAT cycle does not exist.")
    row = _pending_signoff(db, cycle.id)
    if not row:
        raise ConflictError("UAT_SIGNOFF_NOT_PENDING", "There is no pending sign-off request.")
    if row.requested_by_user_id == actor.id:
        raise AuthorizationError("The requester cannot decide their own sign-off request.")
    if decision == "REJECTED" and (not data.comment or not data.comment.strip()):
        raise ConflictError("UAT_REJECTION_COMMENT_REQUIRED", "A rejection comment is required.")
    if decision == "APPROVED":
        summary = _signoff_summary(db, cycle, actor)
        original = json.loads(row.summary_snapshot_json)
        tracked = (
            "total",
            "passed",
            "failed",
            "blocked",
            "not_tested",
            "open_defects",
            "mandatory_incomplete",
        )
        if any(summary[key] != original[key] for key in tracked):
            raise ConflictError(
                "UAT_SIGNOFF_CHANGED",
                "The cycle changed after sign-off was requested. Reject this request and submit a new one.",
            )
    changed = cast(
        CursorResult[Any],
        db.execute(
            update(UatSignoff)
            .where(UatSignoff.id == row.id, UatSignoff.status == "PENDING")
            .values(
                status=decision,
                decided_by_user_id=actor.id,
                decided_at=server_now(),
                decision_comment=data.comment.strip() if data.comment else None,
                acceptance_notes=data.acceptance_notes,
            )
        ),
    )
    if changed.rowcount != 1:
        raise ConflictError("UAT_SIGNOFF_NOT_PENDING", "This sign-off request was already decided.")
    if decision == "APPROVED":
        cycle.status = "COMPLETED"
    db.add(
        Notification(
            recipient_user_id=row.requested_by_user_id,
            notification_type="UAT_SIGNOFF_DECIDED",
            severity="INFO" if decision == "APPROVED" else "WARNING",
            title=f"UAT sign-off {decision.lower()}: {cycle.code}",
            message=(
                data.comment or f"{actor.full_name} {decision.lower()} the UAT sign-off request."
            )[:1000],
            deep_link="/uat",
            deduplication_key=f"uat-signoff-decision:{row.id}:user:{row.requested_by_user_id}",
        )
    )
    _audit(db, actor, "UatSignoff", row.id, f"uat.signoff.{decision.lower()}")
    _commit(db)
    db.refresh(row)
    return _signoff_read(row)


@router.post("/cycles/{cycle_id}/signoff/approve")
def approve_signoff(
    cycle_id: int,
    data: SignoffDecisionInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.signoff.approve")),
) -> dict[str, object]:
    return _decide_signoff(cycle_id, data, "APPROVED", db, actor)


@router.post("/cycles/{cycle_id}/signoff/reject")
def reject_signoff(
    cycle_id: int,
    data: SignoffDecisionInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.signoff.reject")),
) -> dict[str, object]:
    return _decide_signoff(cycle_id, data, "REJECTED", db, actor)


def _source_snapshots(
    db: Session,
    *,
    client_id: int,
    contract_id: int | None,
    product_id: int | None,
    template_ids: list[int],
    test_case_ids: list[int],
    seen: set[int],
) -> list[tuple[int, int | None, dict[str, object]]]:
    if len(set(template_ids)) != len(template_ids) or len(set(test_case_ids)) != len(test_case_ids):
        raise ConflictError("DUPLICATE_UAT_SOURCE", "Select each checklist or test case once.")
    snapshots: list[tuple[int, int | None, dict[str, object]]] = []
    for template_id in template_ids:
        template = db.get(UatChecklistTemplate, template_id)
        if not template or not template.is_active:
            raise NotFoundError("UAT checklist does not exist.")
        assigned_clients = set(
            db.scalars(
                select(UatChecklistTemplateClient.client_id).where(
                    UatChecklistTemplateClient.template_id == template.id
                )
            )
        )
        if (
            template.scope_type != "GLOBAL"
            and template.client_id != client_id
            and client_id not in assigned_clients
        ):
            raise AuthorizationError("This checklist belongs to another client.")
        if (
            template.scope_type == "GLOBAL"
            and assigned_clients
            and client_id not in assigned_clients
        ):
            raise AuthorizationError("This checklist is not assigned to this client.")
        if template.scope_type == "CONTRACT" and template.contract_id != contract_id:
            raise AuthorizationError("This checklist belongs to another contract.")
        if template.product_id and product_id and template.product_id != product_id:
            raise ConflictError(
                "INVALID_UAT_PRODUCT", "Checklist product differs from the cycle product."
            )
        version = db.scalar(
            select(UatChecklistVersion).where(
                UatChecklistVersion.template_id == template.id,
                UatChecklistVersion.version == template.current_version,
            )
        )
        if version:
            for item in db.scalars(
                select(UatChecklistVersionItem)
                .where(UatChecklistVersionItem.version_id == version.id)
                .order_by(UatChecklistVersionItem.display_order)
            ):
                if item.test_case_id not in seen:
                    snapshot = json.loads(item.snapshot_json)
                    if item.section_name:
                        snapshot["checklist_section"] = item.section_name
                    snapshots.append((item.test_case_id, version.id, snapshot))
                    seen.add(item.test_case_id)
    for case_id in test_case_ids:
        case = db.get(UatTestCase, case_id)
        if not case or not case.is_active:
            raise NotFoundError("UAT test case does not exist.")
        if product_id and case.product_id and case.product_id != product_id:
            raise ConflictError(
                "INVALID_UAT_PRODUCT", "Test case product differs from the cycle product."
            )
        if case_id not in seen:
            snapshots.append((case.id, None, _case_snapshot(db, case)))
            seen.add(case.id)
    return snapshots


@router.post("/cycles", status_code=status.HTTP_201_CREATED)
def create_cycle(
    data: CycleInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, object]:
    client = db.get(Client, data.client_id)
    if not client:
        raise NotFoundError("Client does not exist.")
    contract = db.get(Contract, data.contract_id) if data.contract_id else None
    if data.contract_id and (
        not contract
        or (not contract.applies_to_all_clients and data.client_id not in contract.customer_ids)
    ):
        raise ConflictError("INVALID_UAT_CONTRACT", "Contract must belong to the selected client.")
    if data.product_id and not db.get(Product, data.product_id):
        raise NotFoundError("Product does not exist.")
    coordinator = db.get(User, data.coordinator_user_id)
    if not coordinator or not coordinator.is_active or coordinator.user_type == "CLIENT_PORTAL":
        raise ConflictError(
            "INVALID_UAT_COORDINATOR", "Coordinator must be an active internal user."
        )
    if (
        len(set(data.engineer_user_ids)) != len(data.engineer_user_ids)
        or len(set(data.coordinator_user_ids)) != len(data.coordinator_user_ids)
        or len(set(data.client_tester_user_ids)) != len(data.client_tester_user_ids)
    ):
        raise ConflictError(
            "DUPLICATE_UAT_PARTICIPANT", "Select each UAT engineer or coordinator once."
        )
    engineer_ids = data.engineer_user_ids or [data.coordinator_user_id]
    engineers = [db.get(User, user_id) for user_id in engineer_ids]
    if any(
        user is None or not user.is_active or user.user_type != "EMPLOYEE" for user in engineers
    ):
        raise ConflictError("INVALID_UAT_ENGINEER", "UAT engineers must be active internal users.")
    support_coordinators = [db.get(User, user_id) for user_id in data.coordinator_user_ids]
    for user in support_coordinators:
        department = db.get(Department, user.department_id) if user and user.department_id else None
        department_text = " ".join(
            filter(
                None,
                [
                    user.department if user else None,
                    department.code if department else None,
                    department.name if department else None,
                ],
            )
        ).casefold()
        if (
            not user
            or not user.is_active
            or user.user_type != "EMPLOYEE"
            or "support" not in department_text
        ):
            raise ConflictError(
                "INVALID_UAT_SUPPORT_COORDINATOR",
                "UAT coordinators must be active users in the Support department.",
            )
    if data.start_date and data.due_date and data.due_date < data.start_date:
        raise ConflictError("INVALID_UAT_DATES", "Due date must follow start date.")
    for user_id, label in (
        (data.client_approver_user_id, "approver"),
        (data.client_coordinator_user_id, "coordinator"),
    ):
        if user_id:
            portal_user = db.get(User, user_id)
            if (
                not portal_user
                or not portal_user.is_active
                or portal_user.user_type != "CLIENT_PORTAL"
                or data.client_id not in effective_permissions(db, portal_user).client_scope_ids
            ):
                raise ConflictError(
                    "INVALID_UAT_CLIENT_USER",
                    f"Client {label} must be an active portal user for this client.",
                )
    client_testers = [db.get(User, user_id) for user_id in data.client_tester_user_ids]
    for portal_user in client_testers:
        if (
            not portal_user
            or not portal_user.is_active
            or portal_user.user_type != "CLIENT_PORTAL"
            or data.client_id not in effective_permissions(db, portal_user).client_scope_ids
        ):
            raise ConflictError(
                "INVALID_UAT_CLIENT_TESTER",
                "Client engineers must be active portal contacts for the selected client.",
            )
    if data.allow_client_signoff and not data.client_approver_user_id:
        raise ConflictError(
            "INVALID_UAT_CLIENT_APPROVER", "Choose a client approver when sign-off is enabled."
        )
    if not data.template_ids and not data.test_case_ids:
        raise ConflictError("EMPTY_UAT_CYCLE", "Select a checklist or test case.")
    selected_templates = [
        db.get(UatChecklistTemplate, template_id) for template_id in data.template_ids
    ]
    template_names = [template.name for template in selected_templates if template]
    inferred_products = {
        template.product_id for template in selected_templates if template and template.product_id
    }
    generated_code = (
        data.code.strip()
        if data.code and data.code.strip()
        else f"UAT-{data.client_id}-{uuid.uuid4().hex[:8].upper()}"
    )
    generated_title = (
        data.title.strip()
        if data.title and data.title.strip()
        else f"{client.name} - {' + '.join(template_names)}"[:250]
    )
    product_id = data.product_id or (
        next(iter(inferred_products)) if len(inferred_products) == 1 else None
    )
    snapshots = _source_snapshots(
        db,
        client_id=data.client_id,
        contract_id=data.contract_id,
        product_id=product_id,
        template_ids=data.template_ids,
        test_case_ids=data.test_case_ids,
        seen=set(),
    )
    row = UatCycle(
        **data.model_dump(
            exclude={
                "template_ids",
                "test_case_ids",
                "engineer_user_ids",
                "coordinator_user_ids",
                "client_tester_user_ids",
                "code",
                "title",
                "product_id",
            }
        ),
        code=generated_code,
        title=generated_title,
        product_id=product_id,
        created_by_user_id=actor.id,
    )
    db.add(row)
    _flush(db)
    for user_id in engineer_ids:
        db.add(UatCycleParticipant(cycle_id=row.id, user_id=user_id, role="ENGINEER"))
    for user_id in data.coordinator_user_ids:
        db.add(UatCycleParticipant(cycle_id=row.id, user_id=user_id, role="COORDINATOR"))
    for index, (case_id, version_id, snapshot) in enumerate(snapshots):
        db.add(
            UatCycleTest(
                cycle_id=row.id,
                test_case_id=case_id,
                checklist_version_id=version_id,
                snapshot_json=json.dumps(snapshot, ensure_ascii=False),
                display_order=index + 1,
                owner_user_id=engineer_ids[index % len(engineer_ids)],
                client_tester_user_id=data.client_tester_user_ids[
                    index % len(data.client_tester_user_ids)
                ]
                if data.client_tester_user_ids
                else None,
            )
        )
    _audit(db, actor, "UatCycle", row.id, "uat.cycle.created")
    _commit(db)
    return _cycle_read(db, row)


@router.post("/cycles/{cycle_id}/activate")
def activate_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, object]:
    row = db.get(UatCycle, cycle_id)
    if not row:
        raise NotFoundError("UAT cycle does not exist.")
    if row.status != "DRAFT":
        raise ConflictError("INVALID_UAT_STATE", "Only draft cycles can be activated.")
    row.status = "ACTIVE"
    _audit(db, actor, "UatCycle", row.id, "uat.cycle.activated")
    _commit(db)
    return _cycle_read(db, row)


@router.put("/cycles/{cycle_id}")
def update_cycle(
    cycle_id: int,
    data: CycleUpdateInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, object]:
    cycle = db.get(UatCycle, cycle_id)
    if not cycle:
        raise NotFoundError("UAT cycle does not exist.")
    if cycle.status == "COMPLETED":
        raise ConflictError("UAT_CYCLE_COMPLETED", "A completed UAT cannot be edited.")
    if data.start_date and data.due_date and data.due_date < data.start_date:
        raise ConflictError("INVALID_UAT_DATES", "Due date must follow start date.")
    owner = db.get(User, data.coordinator_user_id)
    if not owner or not owner.is_active or owner.user_type != "EMPLOYEE":
        raise ConflictError("INVALID_UAT_COORDINATOR", "UAT owner must be an active internal user.")
    if (
        len(set(data.engineer_user_ids)) != len(data.engineer_user_ids)
        or len(set(data.coordinator_user_ids)) != len(data.coordinator_user_ids)
        or len(set(data.client_tester_user_ids)) != len(data.client_tester_user_ids)
    ):
        raise ConflictError("DUPLICATE_UAT_PARTICIPANT", "Select each UAT participant once.")
    engineer_ids = data.engineer_user_ids or [data.coordinator_user_id]
    engineers = [db.get(User, user_id) for user_id in engineer_ids]
    if any(
        user is None or not user.is_active or user.user_type != "EMPLOYEE" for user in engineers
    ):
        raise ConflictError("INVALID_UAT_ENGINEER", "UAT engineers must be active internal users.")
    for user_id in data.coordinator_user_ids:
        user = db.get(User, user_id)
        department = db.get(Department, user.department_id) if user and user.department_id else None
        department_text = " ".join(
            filter(
                None,
                [
                    user.department if user else None,
                    department.code if department else None,
                    department.name if department else None,
                ],
            )
        ).casefold()
        if (
            not user
            or not user.is_active
            or user.user_type != "EMPLOYEE"
            or "support" not in department_text
        ):
            raise ConflictError(
                "INVALID_UAT_SUPPORT_COORDINATOR",
                "UAT coordinators must be active users in the Support department.",
            )
    for user_id in data.client_tester_user_ids:
        user = db.get(User, user_id)
        if (
            not user
            or not user.is_active
            or user.user_type != "CLIENT_PORTAL"
            or cycle.client_id not in effective_permissions(db, user).client_scope_ids
        ):
            raise ConflictError(
                "INVALID_UAT_CLIENT_TESTER",
                "Client engineers must be active portal contacts for this client.",
            )
    for optional_user_id, label in (
        (data.client_approver_user_id, "approver"),
        (data.client_coordinator_user_id, "coordinator"),
    ):
        if optional_user_id:
            user = db.get(User, optional_user_id)
            if (
                not user
                or not user.is_active
                or user.user_type != "CLIENT_PORTAL"
                or cycle.client_id not in effective_permissions(db, user).client_scope_ids
            ):
                raise ConflictError(
                    "INVALID_UAT_CLIENT_USER",
                    f"Client {label} must be an active portal user for this client.",
                )
    if data.allow_client_signoff and not data.client_approver_user_id:
        raise ConflictError(
            "INVALID_UAT_CLIENT_APPROVER", "Choose a client approver when sign-off is enabled."
        )
    if (
        db.scalar(select(UatClientSignoff.id).where(UatClientSignoff.cycle_id == cycle.id))
        and data.client_approver_user_id != cycle.client_approver_user_id
    ):
        raise ConflictError(
            "UAT_CLIENT_SIGNOFF_RECORDED", "The client approver cannot be changed after a decision."
        )
    for field, value in data.model_dump(
        exclude={"engineer_user_ids", "coordinator_user_ids", "client_tester_user_ids"}
    ).items():
        setattr(cycle, field, value)
    db.query(UatCycleParticipant).filter(UatCycleParticipant.cycle_id == cycle.id).delete()
    for user_id in engineer_ids:
        db.add(UatCycleParticipant(cycle_id=cycle.id, user_id=user_id, role="ENGINEER"))
    for user_id in data.coordinator_user_ids:
        db.add(UatCycleParticipant(cycle_id=cycle.id, user_id=user_id, role="COORDINATOR"))
    tests = list(
        db.scalars(
            select(UatCycleTest)
            .where(UatCycleTest.cycle_id == cycle.id)
            .order_by(UatCycleTest.display_order, UatCycleTest.id)
        )
    )
    for index, test in enumerate(tests):
        test.owner_user_id = engineer_ids[index % len(engineer_ids)]
        test.client_tester_user_id = (
            data.client_tester_user_ids[index % len(data.client_tester_user_ids)]
            if data.client_tester_user_ids
            else None
        )
    _audit(db, actor, "UatCycle", cycle.id, "uat.cycle.updated")
    _commit(db)
    return _cycle_read(db, cycle)


@router.put("/cycles/{cycle_id}/portal-settings")
def update_portal_settings(
    cycle_id: int,
    data: PortalSettingsInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, object]:
    cycle = db.get(UatCycle, cycle_id)
    if not cycle:
        raise NotFoundError("UAT cycle does not exist.")
    if data.portal_visible and cycle.status not in {"ACTIVE", "COMPLETED"}:
        raise ConflictError(
            "INVALID_UAT_STATE", "Activate the cycle before publishing it to the client portal."
        )
    if (
        data.client_access_start_at
        and data.client_access_end_at
        and _aware(data.client_access_end_at) < _aware(data.client_access_start_at)
    ):
        raise ConflictError("INVALID_UAT_ACCESS_WINDOW", "Client access end must follow its start.")
    if not data.allow_client_testing and any(
        (data.allow_client_pass, data.allow_client_fail, data.allow_client_blocked)
    ):
        raise ConflictError(
            "INVALID_UAT_PORTAL_SETTINGS", "Enable client testing before allowing client results."
        )
    if data.allow_client_signoff:
        approver = (
            db.get(User, data.client_approver_user_id) if data.client_approver_user_id else None
        )
        if (
            not data.portal_visible
            or not approver
            or not approver.is_active
            or approver.user_type != "CLIENT_PORTAL"
            or cycle.client_id not in effective_permissions(db, approver).client_scope_ids
        ):
            raise ConflictError(
                "INVALID_UAT_CLIENT_APPROVER",
                "Choose an active portal approver scoped to this client before enabling client sign-off.",
            )
    if data.client_coordinator_user_id:
        coordinator = db.get(User, data.client_coordinator_user_id)
        if (
            not coordinator
            or not coordinator.is_active
            or coordinator.user_type != "CLIENT_PORTAL"
            or cycle.client_id not in effective_permissions(db, coordinator).client_scope_ids
        ):
            raise ConflictError(
                "INVALID_UAT_CLIENT_COORDINATOR",
                "Choose an active portal coordinator scoped to this client.",
            )
    if db.scalar(select(UatClientSignoff.id).where(UatClientSignoff.cycle_id == cycle.id)) and (
        data.client_approver_user_id != cycle.client_approver_user_id
        or not data.allow_client_signoff
    ):
        raise ConflictError(
            "UAT_CLIENT_SIGNOFF_RECORDED",
            "Client sign-off settings cannot be disabled or reassigned after a decision.",
        )
    if _pending_signoff(db, cycle.id):
        raise ConflictError(
            "UAT_SIGNOFF_PENDING",
            "Decide the pending sign-off request before changing portal access.",
        )
    was_visible = cycle.portal_visible
    previous_coordinator_id = cycle.client_coordinator_user_id
    for key, value in data.model_dump().items():
        setattr(cycle, key, value)
    if data.portal_visible and not was_visible:
        recipients = {
            user_id
            for user_id in db.scalars(
                select(UatCycleTest.client_tester_user_id).where(
                    UatCycleTest.cycle_id == cycle.id,
                    UatCycleTest.client_tester_user_id.is_not(None),
                )
            )
            if user_id is not None
        }
        if data.client_approver_user_id:
            recipients.add(data.client_approver_user_id)
        if data.client_coordinator_user_id:
            recipients.add(data.client_coordinator_user_id)
        for user_id in recipients:
            db.add(
                Notification(
                    recipient_user_id=user_id,
                    notification_type="UAT_CLIENT_PUBLISHED",
                    severity="INFO",
                    title=f"UAT available: {cycle.code}",
                    message=f"{cycle.title} is available in the client portal.",
                    deep_link="/portal/uat",
                    deduplication_key=f"uat-client-published:{cycle.id}:user:{user_id}",
                )
            )
    if (
        data.portal_visible
        and data.client_coordinator_user_id
        and data.client_coordinator_user_id != previous_coordinator_id
        and was_visible
    ):
        key = f"uat-client-coordinator:{cycle.id}:user:{data.client_coordinator_user_id}"
        if not db.scalar(select(Notification.id).where(Notification.deduplication_key == key)):
            db.add(
                Notification(
                    recipient_user_id=data.client_coordinator_user_id,
                    notification_type="UAT_CLIENT_COORDINATOR_ASSIGNED",
                    severity="INFO",
                    title=f"Coordinate client UAT: {cycle.code}",
                    message=f"You can review client testing and request more testing for {cycle.title}.",
                    deep_link="/portal/uat",
                    deduplication_key=key,
                )
            )
    _audit(db, actor, "UatCycle", cycle.id, "uat.portal.settings_updated")
    _commit(db)
    return _cycle_read(db, cycle)


@router.put("/cycle-tests/{test_id}/client-tester")
def assign_client_tester(
    test_id: int,
    data: ClientTesterInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, object]:
    test = db.get(UatCycleTest, test_id)
    if not test:
        raise NotFoundError("UAT cycle test does not exist.")
    cycle = db.get(UatCycle, test.cycle_id)
    if not cycle or cycle.status not in {"DRAFT", "ACTIVE"}:
        raise ConflictError(
            "INVALID_UAT_STATE", "Client testers can only be assigned to draft or active cycles."
        )
    if _pending_signoff(db, cycle.id):
        raise ConflictError(
            "UAT_SIGNOFF_PENDING",
            "Decide the pending sign-off request before changing assignments.",
        )
    user = db.get(User, data.user_id) if data.user_id else None
    if data.user_id and (
        not user
        or not user.is_active
        or user.user_type != "CLIENT_PORTAL"
        or cycle.client_id not in effective_permissions(db, user).client_scope_ids
    ):
        raise ConflictError(
            "INVALID_UAT_CLIENT_TESTER", "Tester must be an active portal user for this client."
        )
    previous_user_id = test.client_tester_user_id
    test.client_tester_user_id = data.user_id
    if data.user_id and data.user_id != previous_user_id and cycle.portal_visible:
        db.add(
            Notification(
                recipient_user_id=data.user_id,
                notification_type="UAT_CLIENT_ASSIGNED",
                severity="INFO",
                title=f"UAT test assigned: {cycle.code}",
                message=f"You have been assigned a test in {cycle.title}.",
                deep_link="/portal/uat",
                deduplication_key=f"uat-client-assigned:{test.id}:user:{data.user_id}",
            )
        )
    _audit(db, actor, "UatCycleTest", test.id, "uat.client_tester.assigned")
    _commit(db)
    return {"id": test.id, "client_tester_user_id": test.client_tester_user_id}


@router.post("/cycle-tests/{test_id}/client-unblock")
def unblock_client_test(
    test_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, object]:
    test = db.get(UatCycleTest, test_id)
    if not test:
        raise NotFoundError("UAT cycle test does not exist.")
    cycle = db.get(UatCycle, test.cycle_id)
    if not cycle or cycle.status != "ACTIVE" or test.client_workflow_status != "BLOCKED":
        raise ConflictError(
            "UAT_CLIENT_NOT_BLOCKED", "Only blocked client tests in active cycles can be unblocked."
        )
    if _pending_signoff(db, cycle.id):
        raise ConflictError(
            "UAT_SIGNOFF_PENDING", "Decide the pending sign-off request before changing tests."
        )
    test.client_workflow_status = "READY"
    _audit(db, actor, "UatCycleTest", test.id, "uat.client_test.unblocked")
    _commit(db)
    return {"id": test.id, "client_workflow_status": test.client_workflow_status}


@router.post("/cycles/{cycle_id}/bulk-tests")
def bulk_update_tests(
    cycle_id: int,
    data: BulkTestsInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, object]:
    cycle = db.get(UatCycle, cycle_id)
    if not cycle:
        raise NotFoundError("UAT cycle does not exist.")
    if cycle.status not in {"DRAFT", "ACTIVE"} or _pending_signoff(db, cycle.id):
        raise ConflictError(
            "INVALID_UAT_STATE",
            "Bulk changes require a draft or active cycle with no pending sign-off.",
        )
    if len(set(data.test_ids)) != len(data.test_ids):
        raise ConflictError("DUPLICATE_UAT_TEST", "Select each test only once.")
    tests = list(
        db.scalars(
            select(UatCycleTest).where(
                UatCycleTest.id.in_(data.test_ids), UatCycleTest.cycle_id == cycle.id
            )
        )
    )
    if len(tests) != len(data.test_ids):
        raise NotFoundError("A selected UAT test does not belong to this cycle.")
    if data.action == "ASSIGN_OWNER":
        owner = db.get(User, data.owner_user_id) if data.owner_user_id else None
        if not owner or not owner.is_active or owner.user_type != "EMPLOYEE":
            raise ConflictError("INVALID_UAT_OWNER", "Choose an active employee as the owner.")
        for test in tests:
            test.owner_user_id = owner.id
    elif data.action == "SET_DUE_DATE":
        if data.due_date is None:
            raise ConflictError("UAT_DUE_DATE_REQUIRED", "Choose a due date.")
        for test in tests:
            test.due_date = data.due_date
    elif data.action == "SET_PRIORITY":
        if data.priority is None:
            raise ConflictError("UAT_PRIORITY_REQUIRED", "Choose a priority.")
        for test in tests:
            test.priority_override = data.priority
    else:
        if any(
            test.workflow_status not in {"BLOCKED", "IN_PROGRESS"} or test.linked_ticket_id
            for test in tests
        ):
            raise ConflictError(
                "UAT_BULK_READY_INVALID",
                "Only blocked or in-progress tests without linked tickets can move to Ready.",
            )
        for test in tests:
            test.workflow_status = "READY"
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="UatCycle",
            entity_id=str(cycle.id),
            action="uat.tests.bulk_updated",
            new_values_json=json.dumps({"action": data.action, "test_ids": data.test_ids}),
        )
    )
    _commit(db)
    return {"updated": len(tests), "action": data.action}


@router.post("/cycles/{cycle_id}/tests", status_code=status.HTTP_201_CREATED)
def add_cycle_tests(
    cycle_id: int,
    data: AddTestsInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, object]:
    cycle = db.get(UatCycle, cycle_id)
    if not cycle:
        raise NotFoundError("UAT cycle does not exist.")
    if cycle.status not in {"DRAFT", "ACTIVE"}:
        raise ConflictError(
            "INVALID_UAT_STATE", "Tests can only be added to draft or active cycles."
        )
    if _pending_signoff(db, cycle.id):
        raise ConflictError(
            "UAT_SIGNOFF_PENDING", "Decide the pending sign-off request before adding tests."
        )
    if not data.template_ids and not data.test_case_ids and not data.ad_hoc_tests:
        raise ConflictError(
            "EMPTY_UAT_SELECTION", "Select a checklist, library test, or ad-hoc test."
        )
    existing = list(
        db.scalars(
            select(UatCycleTest)
            .where(UatCycleTest.cycle_id == cycle.id)
            .order_by(UatCycleTest.display_order, UatCycleTest.id)
        )
    )
    seen = {item.test_case_id for item in existing if item.test_case_id is not None}
    next_order = max((item.display_order for item in existing), default=0) + 1
    snapshots = _source_snapshots(
        db,
        client_id=cycle.client_id,
        contract_id=cycle.contract_id,
        product_id=cycle.product_id,
        template_ids=data.template_ids,
        test_case_ids=data.test_case_ids,
        seen=seen,
    )
    for offset, (case_id, version_id, snapshot) in enumerate(snapshots):
        db.add(
            UatCycleTest(
                cycle_id=cycle.id,
                test_case_id=case_id,
                checklist_version_id=version_id,
                snapshot_json=json.dumps(snapshot, ensure_ascii=False),
                display_order=next_order + offset,
                owner_user_id=cycle.coordinator_user_id,
            )
        )
    ad_hoc_start = next_order + len(snapshots)
    for offset, item in enumerate(data.ad_hoc_tests):
        index = len(existing) + offset + 1
        ad_hoc_snapshot: dict[str, object] = {
            "code": f"ADHOC-{cycle.id}-{index}",
            "title": item.title,
            "product_id": cycle.product_id,
            "module_id": None,
            "feature_name": item.feature_name,
            "description": None,
            "preconditions": item.preconditions,
            "expected_result": item.expected_result,
            "priority": item.priority,
            "is_mandatory": item.is_mandatory,
            "source_version": 1,
            "ad_hoc": True,
            "steps": [
                {"order": order, **step.model_dump()} for order, step in enumerate(item.steps, 1)
            ],
        }
        db.add(
            UatCycleTest(
                cycle_id=cycle.id,
                test_case_id=None,
                snapshot_json=json.dumps(ad_hoc_snapshot, ensure_ascii=False),
                display_order=ad_hoc_start + offset,
                owner_user_id=cycle.coordinator_user_id,
            )
        )
    added_count = len(snapshots) + len(data.ad_hoc_tests)
    if added_count == 0:
        raise ConflictError(
            "UAT_TESTS_ALREADY_PRESENT", "The selected tests are already in this cycle."
        )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="UatCycle",
            entity_id=str(cycle.id),
            action="uat.cycle.tests_added",
            new_values_json=json.dumps({"added_count": added_count}),
        )
    )
    _commit(db)
    return _cycle_read(db, cycle)


@router.put("/cycles/{cycle_id}/test-order")
def update_cycle_test_order(
    cycle_id: int,
    data: TestOrderInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, object]:
    cycle = db.get(UatCycle, cycle_id)
    if not cycle:
        raise NotFoundError("UAT cycle does not exist.")
    tests = list(db.scalars(select(UatCycleTest).where(UatCycleTest.cycle_id == cycle.id)))
    current_ids = {test.id for test in tests}
    if len(data.test_ids) != len(current_ids) or set(data.test_ids) != current_ids:
        raise ConflictError(
            "INVALID_UAT_TEST_ORDER", "The order must contain every test in this UAT exactly once."
        )
    rows = {test.id: test for test in tests}
    for position, test_id in enumerate(data.test_ids, 1):
        rows[test_id].display_order = position
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="UatCycle",
            entity_id=str(cycle.id),
            action="uat.cycle.tests_reordered",
            new_values_json=json.dumps({"test_ids": data.test_ids}),
        )
    )
    _commit(db)
    return _cycle_read(db, cycle)


@router.get("/cycle-tests/{test_id}/attempts")
def list_attempts(
    test_id: int,
    db: Session = Depends(get_db),
    _actor: User = Depends(require_permission("uat.view")),
) -> list[dict[str, object]]:
    if not db.get(UatCycleTest, test_id):
        raise NotFoundError("UAT cycle test does not exist.")
    return [
        {
            "id": row.id,
            "attempt_number": row.attempt_number,
            "execution_source": row.execution_source,
            "result": row.result,
            "actual_result": row.actual_result,
            "failure_reason": row.failure_reason,
            "blocking_reason": row.blocking_reason,
            "severity": row.severity,
            "failure_category": row.failure_category,
            "linked_ticket_id": row.linked_ticket_id,
            "comment": row.comment,
            "tested_by_user_id": row.tested_by_user_id,
            "tested_at": row.tested_at,
        }
        for row in db.scalars(
            select(UatTestAttempt)
            .where(UatTestAttempt.cycle_test_id == test_id)
            .order_by(UatTestAttempt.attempt_number)
        )
    ]


@router.post("/cycle-tests/{test_id}/attempts", status_code=status.HTTP_201_CREATED)
def execute_test(
    test_id: int,
    data: ExecuteInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.test.execute")),
) -> dict[str, object]:
    row = db.get(UatCycleTest, test_id)
    if not row:
        raise NotFoundError("UAT cycle test does not exist.")
    cycle = db.get(UatCycle, row.cycle_id)
    if not cycle or cycle.status != "ACTIVE":
        raise ConflictError("INVALID_UAT_STATE", "The UAT cycle must be active before testing.")
    if _pending_signoff(db, cycle.id):
        raise ConflictError(
            "UAT_SIGNOFF_PENDING", "Decide the pending sign-off request before testing."
        )
    if (
        row.owner_user_id != actor.id
        and "uat.cycle.manage" not in effective_permissions(db, actor).permissions
    ):
        raise AuthorizationError("Only the assigned tester or UAT manager can execute this test.")
    if row.test_result == "PASS":
        raise ConflictError(
            "UAT_ALREADY_PASSED", "A passed test cannot be executed again in this milestone."
        )
    if data.result in {"PASS", "FAIL"} and not data.actual_result.strip():
        raise ConflictError("UAT_ACTUAL_RESULT_REQUIRED", "Actual result is required.")
    if data.result == "FAIL" and (
        not data.failure_reason or not data.failure_reason.strip() or not data.severity
    ):
        raise ConflictError(
            "UAT_FAILURE_DETAILS_REQUIRED", "Failure description and severity are required."
        )
    if data.result == "BLOCKED" and (
        not data.blocking_reason
        or not data.blocking_reason.strip()
        or not data.comment
        or not data.comment.strip()
    ):
        raise ConflictError(
            "UAT_BLOCKING_DETAILS_REQUIRED", "Blocking reason and comment are required."
        )
    if row.workflow_status == "BLOCKED":
        raise ConflictError(
            "UAT_BLOCKED", "A UAT manager must unblock this test before another attempt."
        )
    if row.workflow_status == "NEEDS_INVESTIGATION":
        raise ConflictError(
            "UAT_NEEDS_INVESTIGATION",
            "The coordinator must investigate the failure, create a ticket, or return the test to Ready.",
        )
    if row.linked_ticket_id and row.workflow_status == "WAITING_FIX":
        raise ConflictError(
            "UAT_WAITING_FIX", "The linked ticket must be resolved before retesting."
        )
    when = server_now()
    row.attempt_count += 1
    if row.attempt_count > 1:
        row.retest_count += 1
    row.test_result = data.result
    row.workflow_status = {
        "PASS": "COMPLETED",
        "FAIL": "NEEDS_INVESTIGATION",
        "BLOCKED": "BLOCKED",
    }[data.result]
    row.tested_at = when
    attempt_number = (
        db.scalar(
            select(func.max(UatTestAttempt.attempt_number)).where(
                UatTestAttempt.cycle_test_id == row.id
            )
        )
        or 0
    ) + 1
    attempt = UatTestAttempt(
        cycle_test_id=row.id,
        attempt_number=attempt_number,
        execution_source="INTERNAL",
        tested_by_user_id=actor.id,
        tested_at=when,
        result=data.result,
        actual_result=data.actual_result
        or (data.blocking_reason.strip() if data.blocking_reason else ""),
        comment=data.comment,
        failure_reason=data.failure_reason.strip()
        if data.result == "FAIL" and data.failure_reason
        else None,
        blocking_reason=data.blocking_reason.strip()
        if data.result == "BLOCKED" and data.blocking_reason
        else None,
        severity=data.severity if data.result == "FAIL" else None,
        failure_category=data.failure_category if data.result == "FAIL" else None,
    )
    db.add(attempt)
    if data.result == "FAIL" and row.retest_count == 0 and cycle.coordinator_user_id != actor.id:
        db.add(
            Notification(
                recipient_user_id=cycle.coordinator_user_id,
                notification_type="UAT_TEST_FAILED",
                severity="WARNING" if data.severity != "CRITICAL" else "CRITICAL",
                title=f"UAT test failed: {cycle.code}",
                message=f"Test #{row.id} failed. Severity: {data.severity}.",
                deep_link="/uat",
                deduplication_key=f"uat-test-failed:{row.id}:attempt:{row.attempt_count}",
            )
        )
    if row.retest_count and data.result in {"PASS", "FAIL"}:
        db.add(
            Notification(
                recipient_user_id=cycle.coordinator_user_id,
                notification_type=f"UAT_RETEST_{data.result}",
                severity="WARNING" if data.result == "FAIL" else "INFO",
                title=f"UAT retest {data.result.lower()}: {cycle.code}",
                message=f"Test #{row.id} retest #{row.retest_count} {data.result.lower()}.",
                deep_link="/uat",
                deduplication_key=f"uat-retest-result:{row.id}:attempt:{row.attempt_count}",
            )
        )
    _audit(db, actor, "UatCycleTest", row.id, "uat.test.executed")
    _commit(db)
    return {
        "id": row.id,
        "result": row.test_result,
        "workflow_status": row.workflow_status,
        "attempt_count": row.attempt_count,
        "retest_count": row.retest_count,
        "tested_at": row.tested_at,
    }


@router.post("/cycle-tests/{test_id}/unblock")
def unblock_test(
    test_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, object]:
    row = db.get(UatCycleTest, test_id)
    if not row:
        raise NotFoundError("UAT cycle test does not exist.")
    if _pending_signoff(db, row.cycle_id):
        raise ConflictError(
            "UAT_SIGNOFF_PENDING", "Decide the pending sign-off request before changing tests."
        )
    if row.workflow_status != "BLOCKED":
        raise ConflictError("UAT_NOT_BLOCKED", "Only blocked tests can be unblocked.")
    row.workflow_status = "READY"
    _audit(db, actor, "UatCycleTest", row.id, "uat.test.unblocked")
    _commit(db)
    return {"id": row.id, "workflow_status": row.workflow_status, "test_result": row.test_result}


@router.put("/cycle-tests/{test_id}/workflow")
def move_test_workflow(
    test_id: int,
    data: WorkflowMoveInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.test.execute")),
) -> dict[str, object]:
    row = db.get(UatCycleTest, test_id)
    if not row:
        raise NotFoundError("UAT cycle test does not exist.")
    cycle = db.get(UatCycle, row.cycle_id)
    if not cycle or cycle.status != "ACTIVE" or _pending_signoff(db, cycle.id):
        raise ConflictError(
            "INVALID_UAT_STATE",
            "Workflow movement requires an active cycle with no pending sign-off.",
        )
    permissions = set(effective_permissions(db, actor).permissions)
    if row.owner_user_id != actor.id and "uat.cycle.manage" not in permissions:
        raise AuthorizationError("Only the assigned tester or UAT manager can move this test.")
    allowed = {
        ("READY", "IN_PROGRESS"),
        ("IN_PROGRESS", "READY"),
        ("READY_FOR_RETEST", "IN_PROGRESS"),
        ("BLOCKED", "READY"),
        ("NEEDS_INVESTIGATION", "READY"),
    }
    if (row.workflow_status, data.workflow_status) not in allowed:
        raise ConflictError(
            "UAT_WORKFLOW_MOVE_INVALID",
            "Use the test action form to record Pass, Fail, or Blocked results. Waiting-for-fix tests move after their ticket is resolved.",
        )
    if row.workflow_status == "BLOCKED" and "uat.cycle.manage" not in permissions:
        raise AuthorizationError("A UAT manager must unblock this test.")
    if row.workflow_status == "NEEDS_INVESTIGATION" and "uat.cycle.manage" not in permissions:
        raise AuthorizationError("A UAT manager must complete the failure investigation.")
    row.workflow_status = data.workflow_status
    _audit(db, actor, "UatCycleTest", row.id, "uat.test.workflow_moved")
    _commit(db)
    return {"id": row.id, "workflow_status": row.workflow_status, "test_result": row.test_result}


def _defect_draft(db: Session, row: UatCycleTest) -> dict[str, object]:
    cycle = db.get(UatCycle, row.cycle_id)
    assert cycle is not None
    snapshot = json.loads(row.snapshot_json)
    latest = db.scalar(
        select(UatTestAttempt)
        .where(UatTestAttempt.cycle_test_id == row.id, UatTestAttempt.result == "FAIL")
        .order_by(UatTestAttempt.attempt_number.desc())
    )
    if not latest:
        raise ConflictError(
            "UAT_NOT_FAILED", "Record a failed attempt before creating a defect ticket."
        )
    product = (
        db.get(Product, cycle.product_id or snapshot.get("product_id"))
        if cycle.product_id or snapshot.get("product_id")
        else None
    )
    module = db.get(ProductModule, snapshot.get("module_id")) if snapshot.get("module_id") else None
    client = db.get(Client, cycle.client_id)
    contract = db.get(Contract, cycle.contract_id) if cycle.contract_id else None
    subject = f"UAT Failed - {product.name if product else 'Product'} - {module.name if module else 'General'} - {snapshot['title']}"[
        :300
    ]
    lines = [
        f"UAT cycle: {cycle.code} - {cycle.title}",
        f"UAT test ID: {row.id}",
        f"Client: {client.name if client else cycle.client_id}",
        f"Contract: {contract.name if contract else 'None'}",
        f"Product: {product.name if product else 'None'}",
        f"Module: {module.name if module else 'None'}",
        f"Feature: {snapshot.get('feature_name') or 'None'}",
        f"Release: {cycle.release_version}",
        f"Environment: {cycle.environment}",
        f"Preconditions: {snapshot.get('preconditions') or 'None'}",
        "Steps:",
        *[
            f"{step['order']}. {step['action']} => {step['expected_result']}"
            for step in snapshot["steps"]
        ],
        f"Expected: {snapshot['expected_result']}",
        f"Actual: {latest.actual_result}",
        f"Failure: {latest.failure_reason or latest.actual_result}",
        f"Severity: {latest.severity or 'MEDIUM'}",
        f"Tester ID: {latest.tested_by_user_id}",
    ]
    return {
        "subject": subject,
        "description": "\n".join(lines)[:20000],
        "impact": latest.severity or "MEDIUM",
        "urgency": latest.severity or "MEDIUM",
    }


@router.get("/cycle-tests/{test_id}/defect-ticket-draft")
def defect_ticket_draft(
    test_id: int,
    db: Session = Depends(get_db),
    _actor: User = Depends(require_permission("uat.view")),
) -> dict[str, object]:
    row = db.get(UatCycleTest, test_id)
    if not row:
        raise NotFoundError("UAT cycle test does not exist.")
    return _defect_draft(db, row)


@router.post("/cycle-tests/{test_id}/defect-ticket", status_code=status.HTTP_201_CREATED)
def create_defect_ticket(
    test_id: int,
    data: DefectTicketInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.test.execute")),
) -> dict[str, object]:
    permissions = set(effective_permissions(db, actor).permissions)
    if "ticket.create" not in permissions:
        raise AuthorizationError("Ticket creation permission is required.")
    row = db.get(UatCycleTest, test_id)
    if not row:
        raise NotFoundError("UAT cycle test does not exist.")
    if row.owner_user_id != actor.id and "uat.cycle.manage" not in permissions:
        raise AuthorizationError(
            "Only the assigned tester or UAT manager can create this defect ticket."
        )
    if row.linked_ticket_id:
        ticket = db.get(Ticket, row.linked_ticket_id)
        raise ConflictError(
            "UAT_TICKET_EXISTS",
            f"This UAT test is already linked to {ticket.ticket_number if ticket else row.linked_ticket_id}.",
        )
    if row.test_result != "FAIL":
        raise ConflictError(
            "UAT_NOT_FAILED", "Record a failed attempt before creating a defect ticket."
        )
    cycle = db.get(UatCycle, row.cycle_id)
    assert cycle is not None
    snapshot = json.loads(row.snapshot_json)
    ticket_type = db.scalar(select(TicketType).where(TicketType.code == "INCIDENT"))
    if not ticket_type:
        raise NotFoundError("Incident ticket type is not configured.")
    previous = db.scalar(
        select(Ticket).where(
            Ticket.source_channel == "UAT",
            Ticket.creation_idempotency_key == f"uat-defect-{row.id}",
        )
    )
    ticket = previous or create_ticket(
        db,
        TicketCreate(
            ticket_type_id=ticket_type.id,
            client_id=cycle.client_id,
            contract_id=cycle.contract_id,
            product_id=cycle.product_id or snapshot.get("product_id"),
            product_module_id=snapshot.get("module_id"),
            source_channel="UAT",
            creation_idempotency_key=f"uat-defect-{row.id}",
            **data.model_dump(),
        ),
        actor,
    )
    row.linked_ticket_id = ticket.id
    latest = db.scalar(
        select(UatTestAttempt)
        .where(UatTestAttempt.cycle_test_id == row.id, UatTestAttempt.result == "FAIL")
        .order_by(UatTestAttempt.attempt_number.desc())
    )
    if latest:
        latest.linked_ticket_id = ticket.id
    row.workflow_status = "WAITING_FIX"
    notify_defect_created(db, cycle, row, ticket)
    _audit(db, actor, "UatCycleTest", row.id, "uat.defect_ticket.linked")
    _commit(db)
    return {
        "ticket_id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "workflow_status": row.workflow_status,
    }


@router.get("/implementation-progress")
def list_progress(
    db: Session = Depends(get_db), _actor: User = Depends(require_permission("uat.progress.view"))
) -> list[dict[str, object]]:
    return [
        _progress_read(row)
        for row in db.scalars(select(UatImplementationTask).order_by(UatImplementationTask.id))
    ]


@router.post("/implementation-progress", status_code=status.HTTP_201_CREATED)
def create_progress(
    data: ProgressCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.progress.manage")),
) -> dict[str, object]:
    row = UatImplementationTask(**data.model_dump(), updated_by_user_id=actor.id)
    db.add(row)
    _flush(db)
    _audit(db, actor, "UatImplementationTask", row.id, "uat.progress.created")
    _commit(db)
    return _progress_read(row)


def _progress_read(row: UatImplementationTask) -> dict[str, object]:
    return {
        "id": row.id,
        "feature_area": row.feature_area,
        "description": row.description,
        "backend_status": row.backend_status,
        "frontend_status": row.frontend_status,
        "database_status": row.database_status,
        "testing_status": row.testing_status,
        "overall_status": row.overall_status,
        "notes": row.notes,
        "updated_by_user_id": row.updated_by_user_id,
        "updated_at": row.updated_at,
    }


@router.put("/implementation-progress/{task_id}")
def update_progress(
    task_id: int,
    data: ProgressInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.progress.manage")),
) -> dict[str, object]:
    row = db.get(UatImplementationTask, task_id)
    if not row:
        raise NotFoundError("UAT implementation task does not exist.")
    for key, value in data.model_dump().items():
        if key.endswith("_status") and value not in PROGRESS_STATUSES:
            raise ConflictError("INVALID_UAT_PROGRESS", "Unknown implementation status.")
        setattr(row, key, value)
    row.updated_by_user_id = actor.id
    row.updated_at = server_now()
    _audit(db, actor, "UatImplementationTask", row.id, "uat.progress.updated")
    _commit(db)
    return _progress_read(row)
