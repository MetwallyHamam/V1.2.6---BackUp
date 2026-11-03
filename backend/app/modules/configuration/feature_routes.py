import json
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.exceptions import AppError, ConflictError
from app.db.base import utc_now
from app.db.session import get_db
from app.modules.clients.models import Client, Product, ServiceCatalogItem
from app.modules.configuration.models import FeatureDefinition, FeaturePolicy
from app.modules.configuration.policy_service import (
    VALID_MODES,
    VALID_SCOPES,
    canonical_scope_key,
    policy_configuration,
    resolve_feature_policy,
)
from app.modules.contracts.models import Contract
from app.modules.iam.models import AuditLog, User
from app.modules.tickets.models import TicketType

router = APIRouter(prefix="/system/feature-policies", tags=["feature policy control"])


class FeaturePolicyWrite(BaseModel):
    scope_type: Literal["SYSTEM", "CLIENT", "CONTRACT", "PRODUCT_SERVICE"]
    client_id: int | None = None
    contract_id: int | None = None
    product_id: int | None = None
    service_id: int | None = None
    mode: Literal["OFF", "SHADOW", "ENFORCED"]
    configuration: dict[str, object] = Field(default_factory=dict)
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    expected_version: int | None = Field(default=None, ge=1)
    reason: str = Field(min_length=5, max_length=500)

    @model_validator(mode="after")
    def validate_scope(self) -> "FeaturePolicyWrite":
        identifiers = (self.client_id, self.contract_id, self.product_id, self.service_id)
        if self.scope_type == "SYSTEM" and any(value is not None for value in identifiers):
            raise ValueError("System policies cannot contain scoped identifiers.")
        if self.scope_type == "CLIENT" and (self.client_id is None or any(value is not None for value in identifiers[1:])):
            raise ValueError("Client policies require only client_id.")
        if self.scope_type == "CONTRACT" and (self.contract_id is None or self.client_id is not None or self.product_id is not None or self.service_id is not None):
            raise ValueError("Contract policies require only contract_id.")
        if self.scope_type == "PRODUCT_SERVICE" and self.product_id is None and self.service_id is None:
            raise ValueError("Product/service policies require product_id or service_id.")
        if self.effective_from and self.effective_until and self.effective_until <= self.effective_from:
            raise ValueError("effective_until must be later than effective_from.")
        return self


class FeatureDefinitionRead(BaseModel):
    key: str
    name: str
    category: str
    description: str
    default_mode: str
    supported_scopes: list[str]
    is_active: bool


class FeaturePolicyRead(BaseModel):
    id: int
    feature_key: str
    scope_type: str
    scope_key: str
    client_id: int | None
    contract_id: int | None
    product_id: int | None
    service_id: int | None
    mode: str
    configuration: dict[str, object]
    effective_from: datetime
    effective_until: datetime | None
    version: int
    updated_by_user_id: int
    updated_at: datetime


class EffectivePolicyRead(BaseModel):
    feature_key: str
    mode: str
    configuration: dict[str, object]
    source_scope: str
    source_scope_key: str
    policy_id: int | None
    policy_version: int
    evaluated_at: datetime


def serialize_policy(item: FeaturePolicy) -> FeaturePolicyRead:
    return FeaturePolicyRead(
        id=item.id, feature_key=item.feature_key, scope_type=item.scope_type,
        scope_key=item.scope_key, client_id=item.client_id, contract_id=item.contract_id,
        product_id=item.product_id, service_id=item.service_id, mode=item.mode,
        configuration=policy_configuration(item), effective_from=item.effective_from,
        effective_until=item.effective_until, version=item.version,
        updated_by_user_id=item.updated_by_user_id, updated_at=item.updated_at,
    )


def validate_references(db: Session, data: FeaturePolicyWrite) -> None:
    for value, model, label in (
        (data.client_id, Client, "client"), (data.contract_id, Contract, "contract"),
        (data.product_id, Product, "product"), (data.service_id, ServiceCatalogItem, "service"),
    ):
        if value is not None and not db.get(model, value):
            raise ConflictError("FEATURE_POLICY_SCOPE_NOT_FOUND", f"The selected {label} does not exist.")


def validate_pre_ticket_profile(db: Session, data: FeaturePolicyWrite) -> None:
    """Prevent enabling the workflow until every automatic conversion input is governed."""
    if data.mode != "ENFORCED":
        return
    profile = data.configuration.get("fast_create_profile", data.configuration)
    if not isinstance(profile, dict):
        raise ConflictError("PRE_TICKET_PROFILE_INCOMPLETE", "A Fast Create profile is required before enabling Pre-Tickets.")
    ticket_type_id = profile.get("ticket_type_id")
    mapping = profile.get("priority_mapping")
    ticket_type = db.get(TicketType, ticket_type_id) if isinstance(ticket_type_id, int) else None
    if not ticket_type or not ticket_type.is_active:
        raise ConflictError("PRE_TICKET_PROFILE_INVALID", "Select an active default Ticket Type.")
    values = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    if not isinstance(mapping, dict) or any(
        not isinstance(mapping.get(priority), dict)
        or mapping[priority].get("impact") not in values
        or mapping[priority].get("urgency") not in values
        for priority in ("P1", "P2", "P3", "P4")
    ):
        raise ConflictError("PRE_TICKET_PROFILE_INCOMPLETE", "Map every P1–P4 proposed priority to official Impact and Urgency before enabling Pre-Tickets.")


@router.get("", response_model=list[FeatureDefinitionRead])
def list_features(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("feature_policy.view")),
) -> list[FeatureDefinitionRead]:
    return [FeatureDefinitionRead(
        key=item.key, name=item.name, category=item.category,
        description=item.description, default_mode=item.default_mode,
        supported_scopes=item.supported_scopes.split(","), is_active=item.is_active,
    ) for item in db.scalars(select(FeatureDefinition).order_by(FeatureDefinition.category, FeatureDefinition.name))]


@router.get("/{feature_key}/policies", response_model=list[FeaturePolicyRead])
def list_feature_policies(
    feature_key: str, db: Session = Depends(get_db),
    _: User = Depends(require_permission("feature_policy.view")),
) -> list[FeaturePolicyRead]:
    if not db.get(FeatureDefinition, feature_key):
        raise AppError("FEATURE_NOT_FOUND", "The feature does not exist.", 404)
    return [serialize_policy(item) for item in db.scalars(select(FeaturePolicy).where(
        FeaturePolicy.feature_key == feature_key
    ).order_by(FeaturePolicy.scope_type, FeaturePolicy.scope_key))]


@router.get("/{feature_key}/effective", response_model=EffectivePolicyRead)
def preview_effective_policy(
    feature_key: str, client_id: int | None = None, contract_id: int | None = None,
    product_id: int | None = None, service_id: int | None = None,
    at: datetime | None = None, db: Session = Depends(get_db),
    _: User = Depends(require_permission("feature_policy.view")),
) -> EffectivePolicyRead:
    if not db.get(FeatureDefinition, feature_key):
        raise AppError("FEATURE_NOT_FOUND", "The feature does not exist.", 404)
    result = resolve_feature_policy(
        db, feature_key, client_id=client_id, contract_id=contract_id,
        product_id=product_id, service_id=service_id, at=at,
    )
    return EffectivePolicyRead(**result.__dict__)


@router.put("/{feature_key}/policies", response_model=FeaturePolicyRead)
def put_feature_policy(
    feature_key: str, data: FeaturePolicyWrite, db: Session = Depends(get_db),
    actor: User = Depends(require_permission("feature_policy.manage")),
) -> FeaturePolicyRead:
    definition = db.get(FeatureDefinition, feature_key)
    if not definition or not definition.is_active:
        raise AppError("FEATURE_NOT_FOUND", "The feature does not exist or is inactive.", 404)
    if data.scope_type not in VALID_SCOPES or data.mode not in VALID_MODES or data.scope_type not in definition.supported_scopes.split(","):
        raise ConflictError("FEATURE_POLICY_NOT_SUPPORTED", "The requested feature mode or scope is not supported.")
    validate_references(db, data)
    if feature_key == "engineer_pre_ticket":
        validate_pre_ticket_profile(db, data)
    scope_key = canonical_scope_key(
        data.scope_type, client_id=data.client_id, contract_id=data.contract_id,
        product_id=data.product_id, service_id=data.service_id,
    )
    item = db.scalar(select(FeaturePolicy).where(
        FeaturePolicy.feature_key == feature_key, FeaturePolicy.scope_key == scope_key
    ))
    old_values: dict[str, object] | None = None
    now = utc_now()
    if item:
        if data.expected_version is not None and item.version != data.expected_version:
            raise ConflictError("FEATURE_POLICY_CONCURRENT_UPDATE", "The policy changed. Refresh and try again.")
        old_values = serialize_policy(item).model_dump(mode="json")
        item.version += 1
    else:
        item = FeaturePolicy(
            feature_key=feature_key, scope_type=data.scope_type, scope_key=scope_key,
            created_by_user_id=actor.id, updated_by_user_id=actor.id,
            created_at=now, updated_at=now,
        )
        db.add(item)
    item.client_id = data.client_id
    item.contract_id = data.contract_id
    item.product_id = data.product_id
    item.service_id = data.service_id
    item.mode = data.mode
    item.configuration_json = json.dumps(data.configuration, separators=(",", ":"), sort_keys=True)
    item.effective_from = data.effective_from or now
    item.effective_until = data.effective_until
    item.updated_by_user_id = actor.id
    item.updated_at = now
    db.flush()
    new_values = serialize_policy(item).model_dump(mode="json")
    db.add(AuditLog(
        actor_user_id=actor.id, entity_type="FeaturePolicy", entity_id=str(item.id),
        action="feature_policy.created" if old_values is None else "feature_policy.updated",
        old_values_json=json.dumps(old_values),
        new_values_json=json.dumps({**new_values, "reason": data.reason}),
    ))
    db.commit()
    db.refresh(item)
    return serialize_policy(item)


@router.delete("/{feature_key}/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feature_policy(
    feature_key: str, policy_id: int, reason: str = Query(min_length=5, max_length=500),
    db: Session = Depends(get_db), actor: User = Depends(require_permission("feature_policy.manage")),
) -> Response:
    item = db.scalar(select(FeaturePolicy).where(
        FeaturePolicy.id == policy_id, FeaturePolicy.feature_key == feature_key
    ))
    if not item:
        raise AppError("FEATURE_POLICY_NOT_FOUND", "The feature policy does not exist.", 404)
    old_values = serialize_policy(item).model_dump(mode="json")
    db.delete(item)
    db.add(AuditLog(
        actor_user_id=actor.id, entity_type="FeaturePolicy", entity_id=str(policy_id),
        action="feature_policy.deleted", old_values_json=json.dumps(old_values),
        new_values_json=json.dumps({"reason": reason, "inherited_after_delete": True}),
    ))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
