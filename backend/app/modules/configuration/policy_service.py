import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.modules.configuration.features import FEATURES_BY_KEY
from app.modules.configuration.models import FeatureDefinition, FeaturePolicy

VALID_MODES = {"OFF", "SHADOW", "ENFORCED"}
VALID_SCOPES = {"SYSTEM", "CLIENT", "CONTRACT", "PRODUCT_SERVICE"}


@dataclass(frozen=True)
class EffectiveFeaturePolicy:
    feature_key: str
    mode: str
    configuration: dict[str, Any]
    source_scope: str
    source_scope_key: str
    policy_id: int | None
    policy_version: int
    evaluated_at: datetime


def canonical_scope_key(
    scope_type: str, *, client_id: int | None = None, contract_id: int | None = None,
    product_id: int | None = None, service_id: int | None = None,
) -> str:
    if scope_type == "SYSTEM":
        return "SYSTEM"
    if scope_type == "CLIENT":
        return f"CLIENT:{client_id}"
    if scope_type == "CONTRACT":
        return f"CONTRACT:{contract_id}"
    return f"PRODUCT_SERVICE:C{client_id or 0}:K{contract_id or 0}:P{product_id or 0}:S{service_id or 0}"


def policy_configuration(policy: FeaturePolicy | None) -> dict[str, Any]:
    if not policy or not policy.configuration_json:
        return {}
    value = json.loads(policy.configuration_json)
    return value if isinstance(value, dict) else {}


def resolve_feature_policy(
    db: Session, feature_key: str, *, client_id: int | None = None,
    contract_id: int | None = None, product_id: int | None = None,
    service_id: int | None = None, at: datetime | None = None,
) -> EffectiveFeaturePolicy:
    evaluated_at = at or server_now()
    definition = db.get(FeatureDefinition, feature_key)
    spec = FEATURES_BY_KEY.get(feature_key)
    default_mode = definition.default_mode if definition else spec.default_mode if spec else "OFF"
    candidates = list(db.scalars(select(FeaturePolicy).where(
        FeaturePolicy.feature_key == feature_key,
        FeaturePolicy.effective_from <= evaluated_at,
        or_(FeaturePolicy.effective_until.is_(None), FeaturePolicy.effective_until > evaluated_at),
    )))
    ordered_scope_keys: list[str] = []
    if product_id is not None or service_id is not None:
        for context_client, context_contract in (
            (client_id, contract_id), (None, contract_id), (client_id, None), (None, None),
        ):
            key = canonical_scope_key(
                "PRODUCT_SERVICE", client_id=context_client, contract_id=context_contract,
                product_id=product_id, service_id=service_id,
            )
            if key not in ordered_scope_keys:
                ordered_scope_keys.append(key)
    if contract_id is not None:
        ordered_scope_keys.append(canonical_scope_key("CONTRACT", contract_id=contract_id))
    if client_id is not None:
        ordered_scope_keys.append(canonical_scope_key("CLIENT", client_id=client_id))
    ordered_scope_keys.append("SYSTEM")
    by_scope = {item.scope_key: item for item in candidates}
    selected = next((by_scope[key] for key in ordered_scope_keys if key in by_scope), None)
    return EffectiveFeaturePolicy(
        feature_key=feature_key,
        mode=selected.mode if selected else default_mode,
        configuration=policy_configuration(selected),
        source_scope=selected.scope_type if selected else "DEFAULT",
        source_scope_key=selected.scope_key if selected else "DEFAULT",
        policy_id=selected.id if selected else None,
        policy_version=selected.version if selected else 0,
        evaluated_at=evaluated_at,
    )
