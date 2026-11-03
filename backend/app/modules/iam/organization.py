from datetime import date, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.clock import server_today
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.iam.models import (
    Department,
    DepartmentHierarchyAssignment,
    DepartmentMembership,
    User,
    UserReportingLine,
)

MAX_ORGANIZATION_DEPTH = 100
MAX_ORGANIZATION_NODES = 10_000


def active_on(
    model: type[DepartmentHierarchyAssignment]
    | type[DepartmentMembership]
    | type[UserReportingLine],
    as_of: date,
) -> ColumnElement[bool]:
    return and_(model.effective_from <= as_of, or_(model.effective_until.is_(None), model.effective_until >= as_of))


def periods_overlap(start_a: date, end_a: date | None, start_b: date, end_b: date | None) -> bool:
    return start_a <= (end_b or date.max) and start_b <= (end_a or date.max)


def department_assignment(db: Session, department_id: int, as_of: date) -> DepartmentHierarchyAssignment | None:
    return db.scalar(
        select(DepartmentHierarchyAssignment)
        .where(DepartmentHierarchyAssignment.department_id == department_id, active_on(DepartmentHierarchyAssignment, as_of))
        .order_by(DepartmentHierarchyAssignment.effective_from.desc(), DepartmentHierarchyAssignment.id.desc())
    )


def department_path(db: Session, department_id: int, as_of: date) -> list[Department]:
    current = db.get(Department, department_id)
    if not current:
        raise NotFoundError("Department does not exist.")
    path: list[Department] = []
    seen: set[int] = set()
    for _ in range(MAX_ORGANIZATION_DEPTH):
        if current.id in seen:
            raise ConflictError("DEPARTMENT_HIERARCHY_CYCLE", "The department hierarchy contains a cycle.")
        seen.add(current.id)
        path.append(current)
        assignment = department_assignment(db, current.id, as_of)
        if not assignment or assignment.parent_department_id is None:
            return list(reversed(path))
        parent = db.get(Department, assignment.parent_department_id)
        if not parent:
            raise ConflictError("DEPARTMENT_HIERARCHY_BROKEN", "A department hierarchy parent is missing.")
        current = parent
    raise ConflictError("DEPARTMENT_HIERARCHY_TOO_DEEP", "The department hierarchy exceeds the safe depth.")


def department_descendant_ids(db: Session, department_id: int, as_of: date, include_self: bool = False) -> list[int]:
    if not db.get(Department, department_id):
        raise NotFoundError("Department does not exist.")
    assignments = list(db.scalars(select(DepartmentHierarchyAssignment).where(active_on(DepartmentHierarchyAssignment, as_of))))
    children: dict[int, list[int]] = {}
    for assignment in assignments:
        if assignment.parent_department_id is not None:
            children.setdefault(assignment.parent_department_id, []).append(assignment.department_id)
    result = [department_id] if include_self else []
    queue = list(children.get(department_id, []))
    seen = {department_id}
    while queue:
        candidate = queue.pop(0)
        if candidate in seen:
            raise ConflictError("DEPARTMENT_HIERARCHY_CYCLE", "The department hierarchy contains a cycle.")
        seen.add(candidate)
        result.append(candidate)
        if len(seen) > MAX_ORGANIZATION_NODES:
            raise ConflictError("DEPARTMENT_HIERARCHY_TOO_LARGE", "The department hierarchy exceeds the safe traversal size.")
        queue.extend(children.get(candidate, []))
    return result


def validate_department_assignment(db: Session, department_id: int, parent_department_id: int | None, head_user_id: int | None, effective_from: date, effective_until: date | None, ignore_assignment_id: int | None = None) -> None:
    department = db.get(Department, department_id)
    if not department:
        raise NotFoundError("Department does not exist.")
    if effective_until is not None and effective_until < effective_from:
        raise ConflictError("INVALID_EFFECTIVE_DATES", "Effective until must not precede effective from.")
    if parent_department_id == department_id:
        raise ConflictError("DEPARTMENT_HIERARCHY_CYCLE", "A department cannot be its own parent.")
    if parent_department_id is not None and not db.get(Department, parent_department_id):
        raise ConflictError("DEPARTMENT_PARENT_NOT_FOUND", "Parent department does not exist.")
    if head_user_id is not None:
        head = db.get(User, head_user_id)
        if not head or head.user_type != "EMPLOYEE" or not head.is_active:
            raise ConflictError("INVALID_DEPARTMENT_HEAD", "Department head must be an active employee.")
    existing = list(db.scalars(select(DepartmentHierarchyAssignment).where(DepartmentHierarchyAssignment.department_id == department_id, DepartmentHierarchyAssignment.id != ignore_assignment_id if ignore_assignment_id is not None else DepartmentHierarchyAssignment.id > 0)))
    if any(periods_overlap(effective_from, effective_until, row.effective_from, row.effective_until) for row in existing):
        raise ConflictError("DEPARTMENT_HIERARCHY_OVERLAP", "Department hierarchy periods cannot overlap.")
    if parent_department_id is not None:
        descendants = department_descendant_ids(db, department_id, effective_from)
        if parent_department_id in descendants:
            raise ConflictError("DEPARTMENT_HIERARCHY_CYCLE", "The parent change would create a hierarchy cycle.")


def add_department_assignment(db: Session, department_id: int, parent_department_id: int | None, head_user_id: int | None, effective_from: date, effective_until: date | None, actor_id: int) -> DepartmentHierarchyAssignment:
    validate_department_assignment(db, department_id, parent_department_id, head_user_id, effective_from, effective_until)
    row = DepartmentHierarchyAssignment(department_id=department_id, parent_department_id=parent_department_id, head_user_id=head_user_id, effective_from=effective_from, effective_until=effective_until, created_by_user_id=actor_id)
    db.add(row)
    if effective_from <= server_today() and (effective_until is None or effective_until >= server_today()):
        department = db.get(Department, department_id)
        assert department is not None
        department.parent_department_id = parent_department_id
        department.head_user_id = head_user_id
        department.effective_from = effective_from
        department.effective_until = effective_until
    return row


def _close_current_period(rows: list[DepartmentMembership] | list[UserReportingLine], effective_from: date) -> None:
    for row in rows:
        if row.effective_until is None or row.effective_until >= effective_from:
            if row.effective_from >= effective_from:
                raise ConflictError("ORGANIZATION_PERIOD_OVERLAP", "A future or same-day organization assignment already exists.")
            row.effective_until = effective_from - timedelta(days=1)


def assign_user_department(db: Session, user_id: int, department_id: int, effective_from: date, actor_id: int) -> DepartmentMembership:
    user = db.get(User, user_id)
    department = db.get(Department, department_id)
    if not user or user.user_type != "EMPLOYEE":
        raise NotFoundError("Employee does not exist.")
    if not department or not department.is_active:
        raise ConflictError("INVALID_DEPARTMENT", "Department must be active.")
    existing = list(db.scalars(select(DepartmentMembership).where(DepartmentMembership.user_id == user_id, DepartmentMembership.is_primary.in_([True]))))
    same_day = next((row for row in existing if row.effective_from == effective_from and row.effective_until is None), None)
    if same_day:
        same_day.department_id = department_id
        if effective_from <= server_today():
            user.department_id = department_id
            user.department = department.name
        return same_day
    _close_current_period(existing, effective_from)
    row = DepartmentMembership(user_id=user_id, department_id=department_id, effective_from=effective_from, is_primary=True, created_by_user_id=actor_id)
    db.add(row)
    if effective_from <= server_today():
        user.department_id = department_id
        user.department = department.name
    return row


def reporting_path(db: Session, user_id: int, as_of: date) -> list[int]:
    result = [user_id]
    seen = {user_id}
    current = user_id
    for _ in range(MAX_ORGANIZATION_DEPTH):
        row = db.scalar(select(UserReportingLine).where(UserReportingLine.user_id == current, active_on(UserReportingLine, as_of)).order_by(UserReportingLine.effective_from.desc(), UserReportingLine.id.desc()))
        if not row:
            return result
        if row.manager_user_id in seen:
            raise ConflictError("REPORTING_LINE_CYCLE", "The reporting hierarchy contains a cycle.")
        seen.add(row.manager_user_id)
        result.append(row.manager_user_id)
        current = row.manager_user_id
    raise ConflictError("REPORTING_HIERARCHY_TOO_DEEP", "The reporting hierarchy exceeds the safe depth.")


def assign_user_manager(db: Session, user_id: int, manager_user_id: int, effective_from: date, actor_id: int) -> UserReportingLine:
    user = db.get(User, user_id)
    manager = db.get(User, manager_user_id)
    if not user or user.user_type != "EMPLOYEE" or not manager or manager.user_type != "EMPLOYEE" or not manager.is_active:
        raise ConflictError("INVALID_REPORTING_LINE", "Employee and manager must be active employee records.")
    if user_id == manager_user_id or user_id in reporting_path(db, manager_user_id, effective_from):
        raise ConflictError("REPORTING_LINE_CYCLE", "The manager change would create a reporting cycle.")
    existing = list(db.scalars(select(UserReportingLine).where(UserReportingLine.user_id == user_id)))
    same_day = next((row for row in existing if row.effective_from == effective_from and row.effective_until is None), None)
    if same_day:
        same_day.manager_user_id = manager_user_id
        if effective_from <= server_today():
            user.reports_to_user_id = manager_user_id
        return same_day
    _close_current_period(existing, effective_from)
    row = UserReportingLine(user_id=user_id, manager_user_id=manager_user_id, effective_from=effective_from, created_by_user_id=actor_id)
    db.add(row)
    if effective_from <= server_today():
        user.reports_to_user_id = manager_user_id
    return row
