from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureSpec:
    key: str
    name: str
    category: str
    description: str
    default_mode: str = "OFF"
    supported_scopes: tuple[str, ...] = ("SYSTEM", "CLIENT", "CONTRACT", "PRODUCT_SERVICE")


FEATURE_SPECS = (
    FeatureSpec("contract_types", "Contract types", "Contracts", "Configurable warranty, support, service, and other contract behavior."),
    FeatureSpec("product_scoped_sla", "Product-scoped SLA", "Contracts & SLA", "Resolve SLA targets using contract, product, service, and priority."),
    FeatureSpec("entitlement_approvals", "Entitlement approvals", "Approvals", "Require approval for configured client, contract, coverage, or SLA exceptions."),
    FeatureSpec("support_tiers", "Dynamic support tiers", "Support operations", "Assign configurable support levels and expertise scopes to employees."),
    FeatureSpec("sequential_escalation", "Sequential escalation", "Support operations", "Restrict escalation to the configured next support tier."),
    FeatureSpec("tier_ticket_visibility", "Tier-based ticket visibility", "Security", "Restrict ticket access using support tier and expertise policies."),
    FeatureSpec("notification_policies", "Notification policies", "Notifications", "Route event notifications by role, tier, team, and configured conditions."),
    FeatureSpec("outlook_inbound_email", "Outlook inbound email", "Email integration", "Create and update tickets from the configured Microsoft 365 mailbox."),
    FeatureSpec("email_creation_acknowledgement", "Email creation acknowledgement", "Email integration", "Acknowledge successful email ticket creation."),
    FeatureSpec("email_status_notifications", "Email status notifications", "Email integration", "Send configured ticket status updates to clients by email."),
    FeatureSpec("engineer_pre_ticket", "Engineer Pre-Tickets", "Support operations", "Allow engineers to submit pre-tickets for Call Center validation and controlled ticket creation.", supported_scopes=("SYSTEM",)),
)

FEATURES_BY_KEY = {item.key: item for item in FEATURE_SPECS}
