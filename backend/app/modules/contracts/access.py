from sqlalchemy.orm import Session

from app.modules.contracts.models import Contract
from app.modules.iam.models import User
from app.modules.iam.service import effective_permissions


def can_access_contract(db: Session, user: User, contract: Contract) -> bool:
    """Use the same contract visibility policy for routes and notifications."""
    if not user.is_active:
        return False
    return (
        user.user_type != "CLIENT_PORTAL"
        or contract.applies_to_all_clients
        or bool(
            ({contract.client_id, *contract.linked_client_ids}).intersection(
                effective_permissions(db, user).client_scope_ids
            )
        )
    )


def can_receive_renewal(db: Session, user: User, contract: Contract) -> bool:
    permissions = effective_permissions(db, user).permissions
    return (
        user.user_type == "EMPLOYEE"
        and can_access_contract(db, user, contract)
        and bool({"contract.view", "contract.manage"}.intersection(permissions))
    )
