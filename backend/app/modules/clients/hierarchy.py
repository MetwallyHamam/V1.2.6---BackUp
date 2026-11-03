from collections import deque

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.clients.models import Client

MAX_HIERARCHY_DEPTH = 1000
SCOPE_MODES = {"SELF", "DIRECT_CHILDREN", "FULL_HIERARCHY"}


def get_ancestors(db: Session, client_id: int) -> list[Client]:
    current = db.get(Client, client_id)
    if current is None:
        raise NotFoundError("Client does not exist.")
    ancestors: list[Client] = []
    visited = {client_id}
    for _ in range(MAX_HIERARCHY_DEPTH):
        if current.parent_client_id is None:
            return list(reversed(ancestors))
        if current.parent_client_id in visited:
            raise ConflictError("CLIENT_HIERARCHY_CYCLE", "The client hierarchy contains a cycle.")
        parent = db.get(Client, current.parent_client_id)
        if parent is None:
            raise ConflictError("CLIENT_HIERARCHY_BROKEN", "A client hierarchy parent is missing.")
        visited.add(parent.id)
        ancestors.append(parent)
        current = parent
    raise ConflictError("CLIENT_HIERARCHY_TOO_DEEP", "The client hierarchy exceeds the safe depth.")


def get_descendants(
    db: Session,
    client_id: int,
    *,
    depth: int | None = None,
    include_self: bool = False,
    active_only: bool = False,
) -> list[Client]:
    root = db.get(Client, client_id)
    if root is None:
        raise NotFoundError("Client does not exist.")
    if depth is not None and depth < 0:
        raise ConflictError("INVALID_HIERARCHY_DEPTH", "Hierarchy depth cannot be negative.")
    result: list[Client] = [root] if include_self and (not active_only or root.is_active) else []
    queue: deque[tuple[int, int]] = deque([(root.id, 0)])
    visited = {root.id}
    while queue:
        parent_id, parent_depth = queue.popleft()
        if depth is not None and parent_depth >= depth:
            continue
        children = list(db.scalars(select(Client).where(Client.parent_client_id == parent_id).order_by(Client.name, Client.id)))
        for child in children:
            if child.id in visited:
                raise ConflictError("CLIENT_HIERARCHY_CYCLE", "The client hierarchy contains a cycle.")
            visited.add(child.id)
            if len(visited) > MAX_HIERARCHY_DEPTH * 100:
                raise ConflictError("CLIENT_HIERARCHY_TOO_LARGE", "The client hierarchy exceeds the safe traversal size.")
            if not active_only or child.is_active:
                result.append(child)
            queue.append((child.id, parent_depth + 1))
    return result


def get_scope_ids(db: Session, client_id: int, scope_mode: str, *, include_self: bool = True) -> list[int]:
    if scope_mode not in SCOPE_MODES:
        raise ConflictError("INVALID_SCOPE_MODE", "Unsupported hierarchy scope mode.")
    if scope_mode == "SELF":
        if db.get(Client, client_id) is None:
            raise NotFoundError("Client does not exist.")
        return [client_id] if include_self else []
    depth = 1 if scope_mode == "DIRECT_CHILDREN" else None
    return [item.id for item in get_descendants(db, client_id, depth=depth, include_self=include_self)]


def get_client_path(db: Session, client_id: int) -> list[Client]:
    client = db.get(Client, client_id)
    if client is None:
        raise NotFoundError("Client does not exist.")
    return [*get_ancestors(db, client_id), client]


def is_descendant(db: Session, ancestor_id: int, candidate_id: int) -> bool:
    if ancestor_id == candidate_id:
        return False
    return any(item.id == candidate_id for item in get_descendants(db, ancestor_id))


def validate_parent_change(db: Session, client_id: int | None, parent_client_id: int | None) -> None:
    if parent_client_id is None:
        return
    if client_id is not None and client_id == parent_client_id:
        raise ConflictError("CLIENT_SELF_PARENT", "A client cannot be its own parent.")
    if db.get(Client, parent_client_id) is None:
        raise NotFoundError("Parent client does not exist.")
    if client_id is not None and is_descendant(db, client_id, parent_client_id):
        raise ConflictError("CLIENT_HIERARCHY_CYCLE", "The parent change would create a hierarchy cycle.")
