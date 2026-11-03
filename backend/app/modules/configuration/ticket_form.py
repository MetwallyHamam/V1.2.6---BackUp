from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.modules.configuration.models import TicketFormFieldSetting


@dataclass(frozen=True)
class TicketFieldDefinition:
    key: str
    label: str
    section: str
    order: int
    can_hide: bool = True
    can_require: bool = True
    permission: str | None = None
    can_default: bool = False


TICKET_FIELD_DEFINITIONS = (
    TicketFieldDefinition(
        "ticket_type_id", "Ticket type", "PRIMARY", 10, False, False, can_default=True
    ),
    TicketFieldDefinition("client_id", "Client", "PRIMARY", 20, False, False),
    TicketFieldDefinition("subject", "Subject", "PRIMARY", 30, False, False),
    TicketFieldDefinition("description", "Description", "PRIMARY", 40, False, False),
    TicketFieldDefinition("product_id", "Product", "PRIMARY", 50),
    TicketFieldDefinition("product_module_id", "Module", "PRIMARY", 60),
    TicketFieldDefinition("category_id", "Category", "PRIMARY", 70),
    TicketFieldDefinition("subcategory_id", "Subcategory", "PRIMARY", 80),
    TicketFieldDefinition("service_id", "Service", "PRIMARY", 90),
    TicketFieldDefinition("environment_id", "Environment", "PRIMARY", 100),
    TicketFieldDefinition("impact", "Impact", "PRIMARY", 110, False, False),
    TicketFieldDefinition("urgency", "Urgency", "PRIMARY", 120, False, False),
    TicketFieldDefinition(
        "priority", "Priority", "PRIMARY", 130, True, False, "ticket.change.priority"
    ),
    TicketFieldDefinition("affected_users", "Affected users / branches", "PRIMARY", 140),
    TicketFieldDefinition("first_occurred_at", "First occurred", "PRIMARY", 150),
    TicketFieldDefinition("patient_safety_flag", "Patient safety", "PRIMARY", 160, True, False),
    TicketFieldDefinition("security_incident_flag", "Security incident", "PRIMARY", 170, True, False),
    TicketFieldDefinition("requester_contact_id", "Caller", "ADDITIONAL", 210),
    TicketFieldDefinition("branch_id", "Branch / site", "ADDITIONAL", 220),
    TicketFieldDefinition(
        "assigned_team", "Assigned team", "ADDITIONAL", 230, True, False, "ticket.assign.team"
    ),
    TicketFieldDefinition(
        "assigned_user_id", "Assigned engineer", "ADDITIONAL", 240, True, False, "ticket.assign.team"
    ),
    TicketFieldDefinition(
        "follower_user_ids", "Followers", "ADDITIONAL", 250, True, False, "ticket.assign.team"
    ),
)
DEFINITIONS_BY_KEY = {item.key: item for item in TICKET_FIELD_DEFINITIONS}

PRE_TICKET_FIELD_DEFINITIONS = tuple(
    TicketFieldDefinition(f"pre_ticket.{key}", label, "PRE_TICKET", order, False, True)
    for key, label, order in (
        ("client_id", "Client", 10),
        ("requester_contact_id", "Contact", 20),
        ("product_id", "Product", 30),
        ("product_module_id", "Module", 40),
        ("service_id", "Service", 50),
    )
)
PRE_TICKET_DEFINITIONS_BY_KEY = {item.key: item for item in PRE_TICKET_FIELD_DEFINITIONS}


def pre_ticket_field_settings(db: Session) -> list[TicketFormFieldSetting]:
    rows = {row.field_key: row for row in db.scalars(select(TicketFormFieldSetting).where(TicketFormFieldSetting.field_key.like("pre_ticket.%")))}
    return [rows[item.key] for item in PRE_TICKET_FIELD_DEFINITIONS if item.key in rows]


def validate_required_pre_ticket_fields(db: Session, data: object) -> None:
    missing = [definition.label for setting in pre_ticket_field_settings(db) if setting.is_required and (definition := PRE_TICKET_DEFINITIONS_BY_KEY[setting.field_key]) and getattr(data, setting.field_key.removeprefix("pre_ticket."), None) is None]
    if missing:
        raise AppError("PRE_TICKET_REQUIRED_FIELDS_MISSING", f"Complete the required Pre-Ticket fields: {', '.join(missing)}.", 422)


def ticket_field_settings(db: Session) -> list[TicketFormFieldSetting]:
    rows = {row.field_key: row for row in db.scalars(select(TicketFormFieldSetting))}
    return [rows[item.key] for item in TICKET_FIELD_DEFINITIONS if item.key in rows]


def validate_required_ticket_fields(db: Session, data: object) -> None:
    missing: list[str] = []
    for setting in ticket_field_settings(db):
        definition = DEFINITIONS_BY_KEY[setting.field_key]
        if not setting.is_visible or not setting.is_required or not definition.can_require:
            continue
        value = getattr(data, setting.field_key, None)
        if value is None or value == "" or value == []:
            missing.append(definition.label)
    if missing:
        raise AppError(
            "TICKET_REQUIRED_FIELDS_MISSING",
            f"Complete the required ticket fields: {', '.join(missing)}.",
            422,
        )
