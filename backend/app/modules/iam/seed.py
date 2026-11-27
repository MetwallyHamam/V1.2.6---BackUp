import secrets
from datetime import time

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.clients.models import ClientStatus, DeploymentIssueType, Environment, SupportTeam
from app.modules.configuration.features import FEATURE_SPECS
from app.modules.configuration.models import FeatureDefinition, TicketFormFieldSetting
from app.modules.configuration.ticket_form import (
    PRE_TICKET_FIELD_DEFINITIONS,
    TICKET_FIELD_DEFINITIONS,
)
from app.modules.contracts.models import (
    BusinessCalendar,
    BusinessCalendarDay,
    ContractTemplateType,
    ContractType,
    SlaPolicy,
    SlaPolicyVersion,
    SlaTarget,
    SlaTargetVersion,
)
from app.modules.escalations.models import EscalationRule
from app.modules.iam.models import Permission, Profile, ProfilePermission, User, UserProfile
from app.modules.iam.security import hash_password
from app.modules.iam.service import normalize
from app.modules.outlook_email.models import OutlookEmailTemplate
from app.modules.shifts.models import ShiftType
from app.modules.tickets.models import TicketStatus, TicketType
from app.modules.uat.models import UatImplementationTask
from app.modules.visits.models import VisitType

PERMISSIONS = [
    "analytics.dictionary.view",
    "analytics.project.view",
    "analytics.implementation.view",
    "analytics.support_readiness.view",
    "analytics.executive.view",
    "uat.view",
    "uat.library.manage",
    "uat.cycle.manage",
    "uat.test.execute",
    "uat.progress.view",
    "uat.progress.manage",
    "uat.signoff.request",
    "uat.signoff.approve",
    "uat.signoff.reject",
    "uat.portal.view",
    "uat.portal.execute",
    "uat.portal.signoff",
    "uat.portal.comment",
    "uat.portal.evidence",
    "uat.portal.create_ticket",
    "portal.training.view",
    "portal.caller.manage",
    "portal.client_profile.view",
    "problem.view",
    "problem.create",
    "problem.edit",
    "problem.assign",
    "problem.link_ticket",
    "problem.identify_root_cause",
    "problem.publish_known_error",
    "problem.close",
    "problem.reopen",
    "major_incident.view",
    "major_incident.declare",
    "major_incident.command",
    "major_incident.link_ticket",
    "major_incident.publish_update",
    "major_incident.restore_service",
    "major_incident.close",
    "change_request.view",
    "change_request.create",
    "change_request.assess",
    "change_request.approve",
    "change_request.plan",
    "change_request.implement",
    "change_request.validate",
    "change_request.complete",
    "change_request.rollback",
    "permission.grant.in_context",
    "customer_success.view",
    "customer_success.export",
    "complaint.create",
    "complaint.view.all",
    "complaint.manage",
    "complaint.update",
    "complaint.assign",
    "complaint.status.change",
    "complaint.tracking.send",
    "complaint.ticket.reopen",
    "ticket.create",
    "ticket.copy",
    "ticket.template.create",
    "ticket.template.manage",
    "ticket.view.own",
    "ticket.view.team",
    "ticket.view.department",
    "ticket.view.all",
    "ticket.help.request",
    "ticket.help.return",
    "ticket.assign.self",
    "ticket.assign.team",
    "ticket.reassign",
    "ticket.comment.public",
    "ticket.live_update.send",
    "ticket.satisfaction.send",
    "ticket.comment.internal",
    "ticket.mention",
    "ticket.change.status",
    "ticket.start.progress",
    "ticket.start_progress_any",
    "ticket.change.priority",
    "ticket.edit.own",
    "ticket.edit.assigned",
    "ticket.edit.team",
    "ticket.edit.all",
    "ticket.edit.subject",
    "ticket.edit.description",
    "ticket.edit.classification",
    "ticket.change.client",
    "ticket.change.contract",
    "ticket.edit.due_date",
    "ticket.resolve",
    "ticket.resolve.any",
    "ticket.resolve.override_readiness",
    "ticket.close",
    "ticket.auto_close_on_resolve",
    "ticket.reopen",
    "ticket.cancel",
    "ticket.escalate",
    "ticket.relate",
    "ticket.bulk.status",
    "ticket.bulk.delete",
    "ticket.delete.request",
    "ticket.delete.approve",
    "ticket.trash.view",
    "ticket.trash.restore",
    "ticket.pre_ticket.create",
    "integration.pre_ticket.create",
    "integration.form.create",
    "ticket.pre_ticket.view.own",
    "ticket.pre_ticket.queue.view",
    "ticket.pre_ticket.queue.process",
    "ticket.pre_ticket.convert_assign",
    "ticket.pre_ticket.report",
    "ticket.pre_ticket.fast_convert.self",
    "ticket.flag.view",
    "ticket.flag.apply",
    "ticket.flag.remove",
    "ticket.flag.manage",
    "ticket.flag.sla.apply",
    "ticket.flag.sla.remove",
    "support_assistant.queue.view",
    "support_assistant.mine.view",
    "support_assistant.backlog.view",
    "support_assistant.sla_risk.view",
    "support_assistant.follow_up.view",
    "support_assistant.pre_ticket.view",
    "support_assistant.ops.view",
    "onboarding.view.own",
    "onboarding.item.update.own",
    "onboarding.hierarchy.view",
    "onboarding.material.view",
    "onboarding.progress.view.team",
    "onboarding.progress.view.department",
    "onboarding.assign",
    "onboarding.item.override",
    "onboarding.template.manage",
    "onboarding.material.manage",
    "onboarding.category.manage",
    "service_checklist.view_own",
    "service_checklist.view_team",
    "service_checklist.view_all",
    "service_checklist.perform",
    "service_checklist.reassign",
    "service_checklist.waive_item",
    "service_checklist.template.view",
    "service_checklist.template.manage",
    "service_checklist.schedule.manage",
    "service_checklist.report.view",
    "service_checklist.export",
    "client.view",
    "client.profile.view",
    "client.manage",
    "customer_structure.policy.view",
    "customer_structure.policy.manage",
    "project.portfolio.view",
    "project.create",
    "project.manage",
    "project.manage.assigned",
    "workspace.project_management.access",
    "workspace.implementation.access",
    "workspace.support.access",
    "project.assignment.request",
    "project.assignment.respond",
    "implementation.task.view",
    "implementation.task.manage",
    "implementation.task.execute",
    "implementation.task.blocker.manage",
    "implementation.task.evidence.create",
    "implementation.task.assign",
    "implementation.task.worklog",
    "implementation.task.review",
    "implementation.unplanned.create",
    "implementation.unplanned.approve",
    "implementation.private_history.view",
    "cross_department.request.create",
    "cross_department.request.respond",
    "cross_department.request.manage",
    "cross_department.event.publish",
    "cross_department.ticket_link.manage",
    "cross_department.history.view",
    "handover.view",
    "handover.prepare",
    "handover.submit",
    "handover.review",
    "handover.accept",
    "handover.activate_support",
    "client.delete",
    "client_access.view",
    "client_access.manage",
    "client_access.reveal",
    "contact.manage",
    "contact.link_existing",
    "installation.read",
    "installation.manage",
    "contract.view",
    "contract.template.view",
    "contract.template.manage",
    "contract.template.apply",
    "contract.manage",
    "contract.notification_rules.manage",
    "contract.delete",
    "contract.override_entitlement",
    "knowledge.view",
    "knowledge.create",
    "knowledge.approve",
    "news.view",
    "news.create",
    "news.publish",
    "news.manage",
    "news.analytics",
    "shift.view",
    "shift.manage",
    "shift.presence.view",
    "shift.view.own",
    "shift.view.team",
    "shift.view.department",
    "shift.view.all",
    "shift.create",
    "shift.edit.own",
    "shift.edit.team",
    "shift.edit.all",
    "shift.edit.published",
    "shift.delete",
    "shift.publish",
    "shift.approve",
    "shift.assign_employee",
    "shift.export",
    "dashboard.agent",
    "dashboard.online_engineers.view",
    "dashboard.manager",
    "dashboard.executive",
    "dashboard.customize.own",
    "dashboard.customize.profile",
    "dashboard.customize.user",
    "dashboard.manage_widgets",
    "report.view",
    "report.export",
    "user.manage",
    "profile.manage",
    "configuration.manage",
    "maintenance.view",
    "maintenance.manage",
    "maintenance.run",
    "feature_policy.view",
    "feature_policy.manage",
    "entitlement_approval.request",
    "entitlement_approval.view",
    "entitlement_approval.decide",
    "entitlement_approval.manage",
    "finance.view",
    "finance.manage",
    "finance.dashboard.view",
    "finance.invoice.create",
    "finance.invoice.edit",
    "finance.invoice.confirm",
    "finance.invoice.cancel",
    "finance.payment.collect",
    "visit.entitlement.view",
    "visit.entitlement.manage",
    "visit.occurrence.generate",
    "visit.occurrence.complete",
    "visit.schedule",
    "visit.field.create.self",
    "visit.assign",
    "visit.override_conflict",
    "visit.document.upload",
    "visit.document.download",
    "data_migration.manage",
    "audit.view",
    "internal_operation.view",
    "internal_operation.manage",
    "internal_operation.workspace.view",
    "internal_operation.calendar.view",
    "internal_operation.create",
    "internal_operation.schedule",
    "internal_operation.assign",
    "internal_operation.transition",
    "internal_operation.comment",
    "internal_operation.document.upload",
    "internal_operation.document.download",
    "internal_operation.template.manage",
    "internal_operation.type.manage",
    "internal_operation.override_conflict",
    "hr.view",
    "project_handover.view",
    "project_handover.manage",
    "project_handover.edit_pending",
    "project_handover.client.lookup",
    "project_handover.client.create",
    "project_handover.contact.create",
    "project_handover.client_access.create",
    "project_handover.engineer.lookup",
    "project_handover.contract_template.apply",
    "kpi.view.team",
    "kpi.view.department",
    "kpi.view.all",
    "kpi.review.team",
    "kpi.approve",
    "kpi.finalize",
    "kpi.export.team",
    "kpi.export.department",
    "kpi.export.all",
    "kpi.manage.templates",
    "kpi.submit.team",
    "kpi.edit_submitted",
    "kpi.hr.view_submitted",
    "kpi.hr.acknowledge",
    "kpi.cutoff.manage",
    "kpi.cutoff.override",
    "kpi.batch.submit",
    "kpi.batch.view",
]

PROFILE_MAP = {
    "CALL_CENTER": {
        "ticket.pre_ticket.queue.view",
        "ticket.pre_ticket.queue.process",
        "ticket.pre_ticket.convert_assign",
        "contact.link_existing",
        "complaint.create",
        "complaint.update",
        "complaint.assign",
        "complaint.status.change",
        "complaint.tracking.send",
        "project_handover.view",
        "internal_operation.view",
        "ticket.create",
        "ticket.view.department",
        "ticket.view.own",
        "ticket.help.return",
        "ticket.comment.public",
        "ticket.live_update.send",
        "ticket.satisfaction.send",
        "ticket.change.status",
        "ticket.edit.own",
        "ticket.edit.subject",
        "ticket.edit.description",
        "ticket.resolve",
        "ticket.close",
        "ticket.cancel",
        "ticket.auto_close_on_resolve",
        "client.view",
        "contact.manage",
        "contract.view",
        "dashboard.agent",
    },
    "L1_SUPPORT": {
        "service_checklist.view_own",
        "service_checklist.perform",
        "service_checklist.template.view",
        "ticket.pre_ticket.create",
        "ticket.pre_ticket.view.own",
        "ticket.pre_ticket.fast_convert.self",
        "contact.link_existing",
        "client_access.view",
        "project_handover.view",
        "internal_operation.view",
        "ticket.create",
        "ticket.view.all",
        "ticket.assign.self",
        "ticket.comment.public",
        "ticket.live_update.send",
        "ticket.satisfaction.send",
        "ticket.comment.internal",
        "ticket.change.status",
        "ticket.start.progress",
        "ticket.edit.assigned",
        "ticket.edit.subject",
        "ticket.edit.description",
        "ticket.edit.classification",
        "ticket.resolve",
        "ticket.close",
        "ticket.cancel",
        "ticket.auto_close_on_resolve",
        "ticket.relate",
        "client.view",
        "contract.view",
        "knowledge.view",
        "shift.view",
        "dashboard.agent",
    },
    "L2_SUPPORT": {
        "service_checklist.view_own",
        "service_checklist.view_team",
        "service_checklist.perform",
        "service_checklist.template.view",
        "contact.link_existing",
        "client_access.view",
        "client_access.reveal",
        "project_handover.view",
        "internal_operation.view",
        "ticket.create",
        "ticket.view.all",
        "ticket.assign.self",
        "ticket.assign.team",
        "ticket.comment.public",
        "ticket.live_update.send",
        "ticket.satisfaction.send",
        "ticket.comment.internal",
        "ticket.change.status",
        "ticket.start.progress",
        "ticket.change.priority",
        "ticket.edit.assigned",
        "ticket.edit.subject",
        "ticket.edit.description",
        "ticket.edit.classification",
        "ticket.resolve",
        "ticket.close",
        "ticket.cancel",
        "ticket.auto_close_on_resolve",
        "ticket.relate",
        "client.view",
        "client.profile.view",
        "installation.read",
        "contract.view",
        "knowledge.view",
        "knowledge.create",
        "shift.view",
        "dashboard.agent",
        "report.view",
    },
    "L3_SUPPORT": {
        "service_checklist.view_own",
        "service_checklist.view_team",
        "service_checklist.perform",
        "service_checklist.reassign",
        "service_checklist.template.view",
        "ticket.delete.request",
        "contact.link_existing",
        "client_access.view",
        "client_access.reveal",
        "project_handover.view",
        "internal_operation.view",
        "ticket.create",
        "ticket.view.all",
        "ticket.assign.team",
        "ticket.assign.self",
        "ticket.reassign",
        "ticket.comment.public",
        "ticket.live_update.send",
        "ticket.satisfaction.send",
        "ticket.comment.internal",
        "ticket.change.status",
        "ticket.start.progress",
        "ticket.change.priority",
        "ticket.edit.assigned",
        "ticket.edit.team",
        "ticket.edit.subject",
        "ticket.edit.description",
        "ticket.edit.classification",
        "ticket.resolve",
        "ticket.close",
        "ticket.auto_close_on_resolve",
        "ticket.reopen",
        "ticket.cancel",
        "ticket.escalate",
        "ticket.help.request",
        "ticket.relate",
        "client.view",
        "client.profile.view",
        "installation.read",
        "contract.view",
        "knowledge.view",
        "knowledge.create",
        "knowledge.approve",
        "shift.view",
        "dashboard.agent",
        "report.view",
    },
    "SUPPORT_MANAGER": {
        "service_checklist.view_own",
        "service_checklist.view_team",
        "service_checklist.view_all",
        "service_checklist.perform",
        "service_checklist.reassign",
        "service_checklist.waive_item",
        "service_checklist.template.view",
        "service_checklist.template.manage",
        "service_checklist.schedule.manage",
        "service_checklist.report.view",
        "service_checklist.export",
        "ticket.delete.request",
        "ticket.delete.approve",
        "ticket.trash.view",
        "ticket.trash.restore",
        "contact.link_existing",
        "customer_success.view",
        "customer_success.export",
        "complaint.manage",
        "complaint.view.all",
        "complaint.update",
        "complaint.assign",
        "complaint.status.change",
        "complaint.tracking.send",
        "complaint.ticket.reopen",
        "client_access.view",
        "client_access.manage",
        "client_access.reveal",
        "project_handover.view",
        "project_handover.manage",
        "internal_operation.view",
        "internal_operation.manage",
        "ticket.create",
        "ticket.view.all",
        "ticket.assign.team",
        "ticket.assign.self",
        "ticket.reassign",
        "ticket.comment.public",
        "ticket.live_update.send",
        "ticket.satisfaction.send",
        "ticket.comment.internal",
        "ticket.change.status",
        "ticket.start.progress",
        "ticket.start_progress_any",
        "ticket.change.priority",
        "ticket.edit.all",
        "ticket.edit.subject",
        "ticket.edit.description",
        "ticket.edit.classification",
        "ticket.change.client",
        "ticket.change.contract",
        "ticket.edit.due_date",
        "ticket.resolve",
        "ticket.resolve.any",
        "ticket.close",
        "ticket.auto_close_on_resolve",
        "ticket.reopen",
        "ticket.cancel",
        "ticket.escalate",
        "ticket.help.request",
        "ticket.relate",
        "client.view",
        "client.profile.view",
        "contract.view",
        "contract.override_entitlement",
        "entitlement_approval.request",
        "entitlement_approval.view",
        "entitlement_approval.decide",
        "finance.view",
        "finance.manage",
        "finance.dashboard.view",
        "finance.invoice.create",
        "finance.invoice.edit",
        "finance.invoice.confirm",
        "finance.invoice.cancel",
        "finance.payment.collect",
        "visit.entitlement.view",
        "visit.entitlement.manage",
        "visit.occurrence.generate",
        "visit.occurrence.complete",
        "visit.schedule",
        "visit.assign",
        "visit.override_conflict",
        "visit.document.upload",
        "visit.document.download",
        "knowledge.view",
        "knowledge.approve",
        "shift.view",
        "shift.manage",
        "dashboard.manager",
        "dashboard.online_engineers.view",
        "dashboard.customize.profile",
        "dashboard.customize.user",
        "dashboard.manage_widgets",
        "report.view",
        "report.export",
        "audit.view",
    },
    "HR": {
        "hr.view",
        "dashboard.manager",
        "report.view",
        "report.export",
        "shift.view",
        "shift.view.all",
        "shift.create",
        "shift.edit.all",
        "shift.edit.published",
        "shift.publish",
        "shift.assign_employee",
        "shift.export",
        "internal_operation.view",
    },
    "TOP_MANAGEMENT": {
        "dashboard.executive",
        "finance.dashboard.view",
        "report.view",
        "report.export",
        "ticket.view.all",
        "client.view",
        "client.profile.view",
        "contract.view",
        "shift.view",
        "shift.view.all",
        "internal_operation.view",
    },
    "FINANCIAL_MANAGEMENT": {
        "finance.view",
        "finance.dashboard.view",
        "client.view",
        "client.profile.view",
        "contract.view",
        "dashboard.agent",
        "report.view",
        "report.export",
    },
    "PROJECT_HANDOVER": {
        "project_handover.view",
        "project_handover.manage",
        "project_handover.edit_pending",
        "project_handover.client.lookup",
        "project_handover.client.create",
        "project_handover.contact.create",
        "project_handover.client_access.create",
        "project_handover.engineer.lookup",
        "project_handover.contract_template.apply",
    },
    "PROJECT_MANAGER": {
        "workspace.project_management.access",
        "analytics.project.view",
        "client.view",
        "client.profile.view",
        "implementation.task.view",
        "project.portfolio.view",
        "project.create",
        "project.manage.assigned",
        "project.assignment.request",
        "cross_department.request.create",
        "cross_department.event.publish",
        "cross_department.ticket_link.manage",
        "cross_department.history.view",
        "handover.view",
        "handover.prepare",
        "handover.submit",
    },
    "IMPLEMENTATION_MANAGER": {
        "workspace.implementation.access",
        "analytics.implementation.view",
        "project.portfolio.view",
        "project.assignment.respond",
        "implementation.task.view",
        "implementation.task.assign",
        "implementation.task.review",
        "implementation.unplanned.approve",
        "implementation.private_history.view",
        "cross_department.request.create",
        "cross_department.request.respond",
        "cross_department.event.publish",
        "cross_department.history.view",
        "handover.view",
    },
    "IMPLEMENTATION_TEAM_LEADER": {
        "workspace.implementation.access",
        "analytics.implementation.view",
        "project.portfolio.view",
        "implementation.task.view",
        "implementation.task.assign",
        "implementation.task.review",
        "implementation.private_history.view",
        "cross_department.request.respond",
        "cross_department.event.publish",
        "cross_department.history.view",
        "handover.view",
    },
    "IMPLEMENTATION_ENGINEER": {
        "workspace.implementation.access",
        "analytics.implementation.view",
        "project.portfolio.view",
        "implementation.task.view",
        "implementation.task.execute",
        "implementation.task.blocker.manage",
        "implementation.task.evidence.create",
        "implementation.task.worklog",
        "implementation.unplanned.create",
        "cross_department.history.view",
        "handover.view",
    },
    "SUPPORT_HANDOVER_REVIEWER": {
        "project.portfolio.view",
        "cross_department.history.view",
        "handover.view",
        "handover.review",
        "handover.accept",
    },
    "ADMINISTRATOR": set(PERMISSIONS),
    "CLIENT_PORTAL": {
        "uat.portal.view",
        "uat.portal.execute",
        "uat.portal.signoff",
        "uat.portal.comment",
        "uat.portal.evidence",
        "uat.portal.create_ticket",
        "portal.training.view",
        "portal.caller.manage",
        "portal.client_profile.view",
        "ticket.create",
        "ticket.view.own",
        "ticket.comment.public",
        "ticket.live_update.send",
        "ticket.satisfaction.send",
        "ticket.reopen",
        "knowledge.view",
    },
}

for _profile_code in ("L1_SUPPORT", "L2_SUPPORT", "L3_SUPPORT"):
    PROFILE_MAP[_profile_code].add("shift.view.own")
for _profile_code in ("L1_SUPPORT", "L2_SUPPORT", "L3_SUPPORT"):
    PROFILE_MAP[_profile_code].update(
        {
            "problem.view", "problem.create", "problem.edit", "problem.link_ticket",
            "major_incident.view", "major_incident.link_ticket", "major_incident.publish_update",
            "change_request.view", "change_request.create", "change_request.assess",
            "change_request.plan", "change_request.implement", "change_request.validate",
        }
    )
PROFILE_MAP["SUPPORT_MANAGER"].update(
    {
        "problem.view", "problem.create", "problem.edit", "problem.assign",
        "problem.link_ticket", "problem.identify_root_cause", "problem.publish_known_error",
        "problem.close", "problem.reopen", "major_incident.view", "major_incident.declare",
        "major_incident.command", "major_incident.link_ticket", "major_incident.publish_update",
        "major_incident.restore_service", "major_incident.close", "change_request.view",
        "change_request.create", "change_request.assess", "change_request.approve",
        "change_request.plan", "change_request.implement", "change_request.validate",
        "change_request.complete", "change_request.rollback",
    }
)
for _profile_code in ("L1_SUPPORT", "L2_SUPPORT", "L3_SUPPORT", "SUPPORT_MANAGER", "TOP_MANAGEMENT", "PROJECT_HANDOVER"):
    PROFILE_MAP[_profile_code].update({"uat.view", "uat.test.execute"})
for _profile_code in ("SUPPORT_MANAGER", "PROJECT_HANDOVER"):
    PROFILE_MAP[_profile_code].update({"uat.library.manage", "uat.cycle.manage", "uat.progress.view", "uat.signoff.request"})
PROFILE_MAP["TOP_MANAGEMENT"].update({"uat.progress.view", "uat.signoff.approve", "uat.signoff.reject"})
for _profile_code in PROFILE_MAP.keys() - {"CLIENT_PORTAL"}:
    PROFILE_MAP[_profile_code].update(
        {
            "onboarding.view.own",
            "onboarding.item.update.own",
            "onboarding.hierarchy.view",
            "onboarding.material.view",
        }
    )
for _profile_code in ("SUPPORT_MANAGER", "HR", "ADMINISTRATOR"):
    PROFILE_MAP[_profile_code].update(
        {
            "onboarding.progress.view.department",
            "onboarding.assign",
            "onboarding.item.override",
            "onboarding.template.manage",
            "onboarding.material.manage",
            "onboarding.category.manage",
        }
    )
PROFILE_MAP["SUPPORT_MANAGER"].update(
    {"shift.view.all", "shift.create", "shift.edit.all", "shift.edit.published", "shift.publish", "shift.assign_employee", "shift.export", "shift.presence.view", "kpi.view.department", "kpi.approve", "kpi.export.department", "kpi.submit.team", "kpi.edit_submitted", "kpi.cutoff.override", "kpi.batch.submit", "kpi.batch.view"}
)
PROFILE_MAP["HR"].update(
    {"kpi.view.all", "kpi.approve", "kpi.finalize", "kpi.export.all", "kpi.manage.templates", "kpi.hr.view_submitted", "kpi.hr.acknowledge", "kpi.cutoff.manage", "kpi.batch.view"}
)
for _profile_code in ("CALL_CENTER", "L1_SUPPORT", "L2_SUPPORT", "L3_SUPPORT", "SUPPORT_MANAGER", "ADMINISTRATOR"):
    PROFILE_MAP[_profile_code].update(
        {"support_assistant.queue.view", "support_assistant.mine.view", "support_assistant.sla_risk.view", "support_assistant.follow_up.view"}
    )
for _profile_code, _profile_permissions in PROFILE_MAP.items():
    if _profile_code in {"CALL_CENTER", "L1_SUPPORT", "L2_SUPPORT", "L3_SUPPORT", "SUPPORT_MANAGER"}:
        _profile_permissions.add("workspace.support.access")
    if "ticket.create" in _profile_permissions:
        _profile_permissions.add("ticket.copy")
    _profile_permissions.add("news.view")
PROFILE_MAP["ADMINISTRATOR"].update(
    {"news.create", "news.publish", "news.manage", "news.analytics", "maintenance.view", "maintenance.manage", "maintenance.run", "customer_structure.policy.view", "customer_structure.policy.manage", "project.portfolio.view", "project.create", "project.manage", "project.assignment.request", "project.assignment.respond", "implementation.task.view", "implementation.task.manage", "implementation.task.assign", "implementation.task.worklog", "implementation.task.review", "implementation.unplanned.create", "implementation.unplanned.approve"}
)
PROFILE_MAP["ADMINISTRATOR"].update({"analytics.dictionary.view", "analytics.project.view", "analytics.implementation.view", "analytics.support_readiness.view", "analytics.executive.view"})
PROFILE_MAP["PROJECT_HANDOVER"].update({"analytics.dictionary.view", "analytics.project.view", "analytics.implementation.view", "analytics.support_readiness.view"})
PROFILE_MAP["SUPPORT_MANAGER"].update({"analytics.dictionary.view", "analytics.support_readiness.view"})
PROFILE_MAP["TOP_MANAGEMENT"].update({"analytics.dictionary.view", "analytics.project.view", "analytics.support_readiness.view", "analytics.executive.view"})
for _profile_code in ("SUPPORT_MANAGER", "TOP_MANAGEMENT", "PROJECT_HANDOVER"):
    PROFILE_MAP[_profile_code].update({"customer_structure.policy.view", "project.portfolio.view"})
PROFILE_MAP["PROJECT_HANDOVER"].update({"project.create", "project.manage", "project.assignment.request", "project.assignment.respond"})
PROFILE_MAP["PROJECT_HANDOVER"].update({"implementation.task.view", "implementation.task.manage", "implementation.task.assign", "implementation.task.worklog", "implementation.task.review", "implementation.unplanned.create", "implementation.unplanned.approve"})
PROFILE_MAP["PROJECT_HANDOVER"].update({"implementation.task.execute", "implementation.task.blocker.manage", "implementation.task.evidence.create"})
PROFILE_MAP["PROJECT_HANDOVER"].add("implementation.private_history.view")
PROFILE_MAP["PROJECT_HANDOVER"].update({"cross_department.request.create", "cross_department.request.respond", "cross_department.request.manage", "cross_department.event.publish", "cross_department.ticket_link.manage", "cross_department.history.view"})
PROFILE_MAP["PROJECT_HANDOVER"].update({"handover.view", "handover.prepare", "handover.submit"})
PROFILE_MAP["ADMINISTRATOR"].update({"cross_department.request.create", "cross_department.request.respond", "cross_department.request.manage", "cross_department.event.publish", "cross_department.ticket_link.manage", "cross_department.history.view"})
PROFILE_MAP["ADMINISTRATOR"].add("implementation.private_history.view")
PROFILE_MAP["ADMINISTRATOR"].update({"handover.view", "handover.prepare", "handover.submit", "handover.review", "handover.accept", "handover.activate_support"})
for _profile_code in ("L1_SUPPORT", "L2_SUPPORT", "L3_SUPPORT", "SUPPORT_MANAGER"):
    PROFILE_MAP[_profile_code].add("cross_department.history.view")
for _profile_code in ("SUPPORT_MANAGER",):
    PROFILE_MAP[_profile_code].update({"cross_department.request.create", "cross_department.request.respond", "cross_department.ticket_link.manage", "cross_department.event.publish"})
    PROFILE_MAP[_profile_code].update({"handover.view", "handover.review", "handover.accept", "handover.activate_support"})
for _profile_code in ("CALL_CENTER", "L1_SUPPORT", "L2_SUPPORT", "L3_SUPPORT", "SUPPORT_MANAGER", "ADMINISTRATOR"):
    PROFILE_MAP[_profile_code].add("support_assistant.backlog.view")
    PROFILE_MAP[_profile_code].update({"ticket.flag.view", "ticket.flag.apply", "ticket.flag.remove"})
for _profile_code in ("SUPPORT_MANAGER", "ADMINISTRATOR"):
    PROFILE_MAP[_profile_code].update({"ticket.flag.manage", "ticket.flag.sla.apply", "ticket.flag.sla.remove"})
for _profile_code in ("L1_SUPPORT", "L2_SUPPORT", "L3_SUPPORT", "SUPPORT_MANAGER", "ADMINISTRATOR"):
    if "internal_operation.view" in PROFILE_MAP[_profile_code]:
        PROFILE_MAP[_profile_code].add("support_assistant.ops.view")
for _profile_code in ("CALL_CENTER", "L1_SUPPORT", "ADMINISTRATOR"):
    PROFILE_MAP[_profile_code].add("support_assistant.pre_ticket.view")

for _profile_code in ("L2_SUPPORT", "L3_SUPPORT"):
    PROFILE_MAP[_profile_code].update(
        {"kpi.view.team", "kpi.review.team", "kpi.export.team", "kpi.submit.team", "kpi.edit_submitted"}
    )

# Client credentials are available to every internal employee group. The external
# CLIENT_PORTAL profile is intentionally excluded from infrastructure secrets.
for _profile_code in (
    "CALL_CENTER",
    "L1_SUPPORT",
    "L2_SUPPORT",
    "L3_SUPPORT",
    "SUPPORT_MANAGER",
    "ADMINISTRATOR",
):
    PROFILE_MAP[_profile_code].update(
        {"client_access.view", "client_access.manage", "client_access.reveal"}
    )

PROFILE_MAP["IMPLEMENTATION"] = PROFILE_MAP["IMPLEMENTATION_MANAGER"] | PROFILE_MAP["IMPLEMENTATION_ENGINEER"]

NAMES = {
    "CALL_CENTER": "Call Center",
    "L1_SUPPORT": "L1 Support",
    "L2_SUPPORT": "L2 Support",
    "L3_SUPPORT": "L3 Support",
    "SUPPORT_MANAGER": "Support Manager",
    "HR": "Human Resources",
    "TOP_MANAGEMENT": "Top Management",
    "FINANCIAL_MANAGEMENT": "Financial Management",
    "PROJECT_HANDOVER": "Project Handover",
    "PROJECT_MANAGER": "Project Manager",
    "IMPLEMENTATION_MANAGER": "Implementation Manager",
    "IMPLEMENTATION_TEAM_LEADER": "Implementation Team Leader",
    "IMPLEMENTATION_ENGINEER": "Implementation Engineer",
    "IMPLEMENTATION": "Impelemntation",
    "SUPPORT_HANDOVER_REVIEWER": "Support Handover Reviewer",
    "ADMINISTRATOR": "System Administrator",
    "CLIENT_PORTAL": "Client Portal",
}


def seed(db: Session) -> None:
    if inspect(db.get_bind()).has_table("visit_types"):
        for code, name in (
            ("PREVENTIVE", "Preventive Visit"),
            ("HEALTH_CHECK", "Health Check"),
            ("SERVICE_REVIEW", "Service Review"),
        ):
            if not db.scalar(select(VisitType.id).where(VisitType.code == code)):
                db.add(VisitType(code=code, name=name, is_active=True))
        db.flush()
    for spec in FEATURE_SPECS:
        definition = db.get(FeatureDefinition, spec.key)
        if not definition:
            db.add(FeatureDefinition(
                key=spec.key, name=spec.name, category=spec.category,
                description=spec.description, default_mode=spec.default_mode,
                supported_scopes=",".join(spec.supported_scopes), is_active=True,
            ))
        else:
            definition.name = spec.name
            definition.category = spec.category
            definition.description = spec.description
            definition.supported_scopes = ",".join(spec.supported_scopes)
    for values in (
        {"code":"LEGACY","name":"Legacy / General","description":"Existing contracts and generic agreements.","precedence":900,"default_has_sla":True,"default_duration_days":None,"expiry_behavior":"EXPIRE","approval_behavior":"INHERIT"},
        {"code":"WARRANTY","name":"Warranty","description":"Product warranty coverage for a defined duration.","precedence":200,"default_has_sla":True,"default_duration_days":365,"expiry_behavior":"EXPIRE","approval_behavior":"INHERIT"},
        {"code":"SUPPORT","name":"Support Contract","description":"Ongoing product support agreement.","precedence":100,"default_has_sla":True,"default_duration_days":365,"expiry_behavior":"RENEW","approval_behavior":"INHERIT"},
        {"code":"SERVICE","name":"Service Contract","description":"Agreement for defined professional or managed services.","precedence":150,"default_has_sla":True,"default_duration_days":365,"expiry_behavior":"RENEW","approval_behavior":"INHERIT"},
    ):
        item = db.scalar(select(ContractType).where(ContractType.code == values["code"]))
        if not item:
            db.add(ContractType(**values, is_system=True, is_active=True))
    permissions: dict[str, Permission] = {}
    for code in PERMISSIONS:
        permission = db.scalar(select(Permission).where(Permission.code == code))
        if not permission:
            permission = Permission(
                code=code,
                module=code.split(".")[0],
                description=code.replace(".", " ").title(),
                is_high_risk=code in {"user.manage", "profile.manage", "configuration.manage", "data_migration.manage", "permission.grant.in_context"},
            )
            db.add(permission)
            db.flush()
        permissions[code] = permission
    for code, codes in PROFILE_MAP.items():
        profile = db.scalar(select(Profile).where(Profile.code == code))
        if not profile:
            profile = Profile(
                code=code,
                name=NAMES[code],
                description=f"System profile: {NAMES[code]}",
                profile_type="CLIENT_PORTAL"
                if code == "CLIENT_PORTAL"
                else ("ADMINISTRATOR" if code == "ADMINISTRATOR" else "EMPLOYEE"),
                is_system=True,
                risk_level="CRITICAL" if code == "ADMINISTRATOR" else "STANDARD",
                default_dashboard_code="portal" if code == "CLIENT_PORTAL" else "dashboard",
            )
            db.add(profile)
            db.flush()
        elif profile.default_dashboard_code == "agent":
            profile.default_dashboard_code = "dashboard"
        existing = set(
            db.scalars(
                select(ProfilePermission.permission_id).where(
                    ProfilePermission.profile_id == profile.id
                )
            )
        )
        db.add_all(
            ProfilePermission(profile_id=profile.id, permission_id=permissions[x].id)
            for x in codes
            if permissions[x].id not in existing
        )
    api_profile = db.scalar(select(Profile).where(Profile.code == "VENDOR_PRE_TICKET_API"))
    if not api_profile:
        api_profile = Profile(
            code="VENDOR_PRE_TICKET_API",
            name="Vendor Pre-Ticket Integration",
            description="API-only profile for hosted forms and automated Pre-Ticket creation.",
            profile_type="API_INTEGRATION",
            is_system=True,
            risk_level="STANDARD",
            default_dashboard_code=None,
        )
        db.add(api_profile)
        db.flush()
    api_permission_ids = {
        permissions["integration.pre_ticket.create"].id,
        permissions["integration.form.create"].id,
    }
    existing_api_permissions = set(db.scalars(select(ProfilePermission.permission_id).where(
        ProfilePermission.profile_id == api_profile.id
    )))
    db.add_all(ProfilePermission(profile_id=api_profile.id, permission_id=permission_id)
               for permission_id in api_permission_ids - existing_api_permissions)
    for code, name, portal_allowed, ticket_allowed in (
        ("PROSPECT", "Prospect", False, False),
        ("IMPLEMENTATION", "Implementation", True, True),
        ("ACTIVE", "Active", True, True),
        ("ON_HOLD", "On Hold", True, False),
        ("SUSPENDED", "Suspended", False, False),
        ("EXPIRED_CONTRACT", "Expired Contract", True, False),
        ("TERMINATED", "Terminated", False, False),
    ):
        if not db.scalar(select(ClientStatus.id).where(ClientStatus.code == code)):
            db.add(
                ClientStatus(
                    code=code,
                    name=name,
                    portal_allowed=portal_allowed,
                    ticket_creation_allowed=ticket_allowed,
                )
            )
    for code, name, is_production in (
        ("PRODUCTION", "Production", True),
        ("UAT", "User Acceptance Testing", False),
        ("DR", "Disaster Recovery", False),
        ("TRAINING", "Training", False),
        ("TEST", "Test", False),
    ):
        if not db.scalar(select(Environment.id).where(Environment.code == code)):
            db.add(Environment(code=code, name=name, is_production=is_production))
    if not db.scalar(select(SupportTeam.id).where(SupportTeam.code == "SUPPORT")):
        db.add(
            SupportTeam(
                code="SUPPORT",
                name="Support",
                description="General support assignment queue",
                is_active=True,
            )
        )
    for code, name, prefix in (
        ("INCIDENT", "Incident", "INC"),
        ("SERVICE_REQUEST", "Service Request", "SR"),
        ("SCHEDULED_SERVICE", "Scheduled Service", "SSV"),
        ("PROBLEM", "Problem", "PRB"),
        ("CHANGE_REQUEST", "Change Request", "CHG"),
        ("ACCESS_REQUEST", "Access Request", "ACC"),
        ("MONITORING_ALERT", "Monitoring Alert", "ALT"),
    ):
        if not db.scalar(select(TicketType.id).where(TicketType.code == code)):
            db.add(
                TicketType(
                    code=code,
                    name=name,
                    number_prefix=prefix,
                    available_for_deployment_issue=code in {"INCIDENT", "SERVICE_REQUEST"},
                )
            )
    for code, name, is_default in (
        ("ISSUE", "Issue", True),
        ("ERROR", "Error", False),
        ("BUG", "BUG", False),
        ("ENHANCEMENT", "Enhancement", False),
    ):
        if not db.scalar(select(DeploymentIssueType.id).where(DeploymentIssueType.code == code)):
            db.add(
                DeploymentIssueType(
                    code=code,
                    name=name,
                    is_default=is_default,
                    is_active=True,
                )
            )
    statuses = (
        ("NEW", "New", False, False),
        ("TRIAGED", "Triaged", False, False),
        ("ASSIGNED", "Assigned", False, False),
        ("IN_PROGRESS", "In Progress", False, False),
        ("PENDING_CLIENT", "Pending Client", False, True),
        ("PENDING_INTERNAL", "Pending Internal", False, False),
        ("PENDING_VENDOR", "Pending Vendor", False, True),
        ("RESOLVED", "Resolved", False, False),
        ("CLIENT_CONFIRMATION", "Client Confirmation", False, False),
        ("CLOSED", "Closed", True, False),
        ("CANCELLED", "Cancelled", True, False),
        ("REOPENED", "Reopened", False, False),
    )
    for order, (code, name, closed, paused) in enumerate(statuses, start=1):
        if not db.scalar(select(TicketStatus.id).where(TicketStatus.code == code)):
            db.add(
                TicketStatus(
                    code=code,
                    name=name,
                    is_closed_state=closed,
                    is_sla_pause_state=paused,
                    sort_order=order,
                )
            )
    for code, name, description in (
        ("GLOBAL", "Global", "General-purpose contract template."),
        ("HIS", "HIS", "Hospital Information System template."),
        ("RIS_PACS", "RIS / PACS", "Radiology and PACS template."),
        ("WORKSTATION", "Workstation", "Workstation contract template."),
        ("VISION_TOOLS", "Vision Tools", "Vision tools contract template."),
    ):
        if not db.scalar(select(ContractTemplateType.id).where(ContractTemplateType.code == code)):
            db.add(ContractTemplateType(code=code, name=name, description=description))
    calendar = db.scalar(select(BusinessCalendar).where(BusinessCalendar.code == "CAIRO_8X5"))
    if not calendar:
        calendar = BusinessCalendar(
            code="CAIRO_8X5", name="Cairo Sunday-Thursday 08:00-17:00", timezone="Africa/Cairo"
        )
        db.add(calendar)
        db.flush()
    existing_days = set(
        db.scalars(
            select(BusinessCalendarDay.weekday).where(
                BusinessCalendarDay.calendar_id == calendar.id
            )
        )
    )
    for weekday in range(7):
        if weekday not in existing_days:
            db.add(
                BusinessCalendarDay(
                    calendar_id=calendar.id,
                    weekday=weekday,
                    start_time=time(8),
                    end_time=time(17),
                    is_working_day=weekday in {6, 0, 1, 2, 3},
                )
            )
    policy = db.scalar(select(SlaPolicy).where(SlaPolicy.code == "DEFAULT_SUPPORT"))
    if not policy:
        policy = SlaPolicy(
            code="DEFAULT_SUPPORT", name="Default Support SLA", calendar_id=calendar.id
        )
        db.add(policy)
        db.flush()
    targets = {"P1": (15, 240), "P2": (30, 480), "P3": (120, 1440), "P4": (240, 2880)}
    existing_targets = set(
        db.scalars(select(SlaTarget.priority).where(SlaTarget.policy_id == policy.id))
    )
    for priority, (response, resolution) in targets.items():
        if priority not in existing_targets:
            db.add(
                SlaTarget(
                    policy_id=policy.id,
                    priority=priority,
                    first_response_minutes=response,
                    resolution_minutes=resolution,
                    is_fallback=True,
                )
            )
    db.flush()
    current_snapshot = db.scalar(select(SlaPolicyVersion).where(
        SlaPolicyVersion.policy_id == policy.id,
        SlaPolicyVersion.version == policy.version,
        SlaPolicyVersion.status == "PUBLISHED",
    ))
    if current_snapshot is not None and db.scalar(select(SlaTargetVersion.id).where(
        SlaTargetVersion.policy_version_id == current_snapshot.id
    )) is None:
        current_snapshot.status = "RETIRED"
        current_snapshot.effective_until = server_now()
        policy.version += 1
        current_snapshot = None
    if current_snapshot is None:
        for prior in db.scalars(select(SlaPolicyVersion).where(
            SlaPolicyVersion.policy_id == policy.id,
            SlaPolicyVersion.status == "PUBLISHED",
        )):
            prior.status = "RETIRED"
            prior.effective_until = server_now()
        current_snapshot = SlaPolicyVersion(
            policy_id=policy.id,
            version=policy.version,
            name_snapshot=policy.name,
            calendar_id=policy.calendar_id,
            calculation_version=policy.calculation_version,
            include_escalation_time=policy.include_escalation_time,
            effective_from=server_now(),
            status="PUBLISHED",
            published_at=server_now(),
        )
        db.add(current_snapshot)
        db.flush()
        for target in db.scalars(select(SlaTarget).where(SlaTarget.policy_id == policy.id)):
            db.add(SlaTargetVersion(
                policy_version_id=current_snapshot.id,
                source_target_id=target.id,
                product_id=target.product_id,
                product_module_id=target.product_module_id,
                service_id=target.service_id,
                priority=target.priority,
                context_key=target.context_key,
                is_fallback=target.is_fallback,
                effective_from=target.effective_from,
                effective_until=target.effective_until,
                first_response_minutes=target.first_response_minutes,
                resolution_minutes=target.resolution_minutes,
                warning_percent=target.warning_percent,
            ))
    for code, name, clock_type, threshold, severity, managers in (
        ("SLA_RESPONSE_50", "First response 50% warning", "FIRST_RESPONSE", 50, "INFO", False),
        ("SLA_RESPONSE_75", "First response 75% warning", "FIRST_RESPONSE", 75, "WARNING", True),
        ("SLA_RESPONSE_100", "First response breach", "FIRST_RESPONSE", 100, "CRITICAL", True),
        ("SLA_RESOLUTION_75", "Resolution 75% warning", "RESOLUTION", 75, "WARNING", True),
        ("SLA_RESOLUTION_100", "Resolution breach", "RESOLUTION", 100, "CRITICAL", True),
    ):
        if not db.scalar(select(EscalationRule.id).where(EscalationRule.code == code)):
            db.add(
                EscalationRule(
                    code=code,
                    name=name,
                    clock_type=clock_type,
                    threshold_percent=threshold,
                    severity=severity,
                    notify_assignee=True,
                    notify_managers=managers,
                )
            )
    for code, name, color, on_call, default_start, default_end in (
        ("DAY", "Day Shift", "#145da0", False, time(9), time(17)),
        ("NIGHT", "Night Shift", "#4b3f72", False, time(16), time(0)),
        ("ON_CALL", "On Call", "#d97706", True, time(0), time(0)),
        ("LEAVE", "Leave", "#64748b", False, time(9), time(17)),
    ):
        if not db.scalar(select(ShiftType.id).where(ShiftType.code == code)):
            db.add(ShiftType(code=code, name=name, color=color, is_on_call=on_call, default_start_time=default_start, default_end_time=default_end))
    existing_ticket_fields = set(db.scalars(select(TicketFormFieldSetting.field_key)))
    db.add_all(
        TicketFormFieldSetting(
            field_key=definition.key,
            is_required=definition.key.startswith("pre_ticket."),
            default_value="SERVICE_REQUEST" if definition.key == "ticket_type_id" else None,
        )
        for definition in (*TICKET_FIELD_DEFINITIONS, *PRE_TICKET_FIELD_DEFINITIONS)
        if definition.key not in existing_ticket_fields
    )
    settings = get_settings()
    support_user = db.scalar(select(User).where(User.email_normalized == "support@millensys.com"))
    if not support_user:
        support_user = User(
            full_name="Support",
            username="Support",
            username_normalized=normalize("Support"),
            email="Support@millensys.com",
            email_normalized=normalize("Support@millensys.com"),
            employee_code=None,
            department="Support",
            job_title="Support Engineer",
            password_hash=hash_password(secrets.token_urlsafe(32)),
            user_type="EMPLOYEE",
            is_active=True,
            require_password_change=True,
        )
        db.add(support_user)
        db.flush()
        support_profile = db.scalar(select(Profile).where(Profile.code == "L1_SUPPORT"))
        if support_profile:
            db.add(UserProfile(user_id=support_user.id, profile_id=support_profile.id, is_primary=True, assigned_by_user_id=support_user.id, assignment_reason="Default ticket assignment account"))
    if settings.dev_admin_username and settings.dev_admin_email and settings.dev_admin_password:
        admin = db.scalar(
            select(User).where(User.username_normalized == normalize(settings.dev_admin_username))
        )
        if not admin:
            admin = User(
                full_name="Development Administrator",
                username=settings.dev_admin_username,
                username_normalized=normalize(settings.dev_admin_username),
                email=settings.dev_admin_email,
                email_normalized=normalize(settings.dev_admin_email),
                password_hash=hash_password(settings.dev_admin_password),
                user_type="EMPLOYEE",
                is_active=True,
                require_password_change=True,
            )
            db.add(admin)
            db.flush()
            profile = db.scalar(select(Profile).where(Profile.code == "ADMINISTRATOR"))
            if profile is None:
                raise RuntimeError("Administrator profile seed failed.")
            db.add(
                UserProfile(
                    user_id=admin.id,
                    profile_id=profile.id,
                    is_primary=True,
                    assigned_by_user_id=admin.id,
                    assignment_reason="Development bootstrap",
                )
            )
    template_defaults = {
        "CREATED": ("Ticket {{ticket_number}} received", "We received your request {{ticket_number}}: {{subject}}. Our support team will update you shortly."),
        "IN_PROGRESS": ("Ticket {{ticket_number}} is in progress", "Your ticket {{ticket_number}} is now in progress."),
        "PENDING": ("Ticket {{ticket_number}} is pending", "Your ticket {{ticket_number}} is pending further information or action."),
        "RESOLVED": ("Ticket {{ticket_number}} resolved", "Your ticket {{ticket_number}} has been resolved."),
        "CLOSED": ("Ticket {{ticket_number}} closed", "Your ticket {{ticket_number}} has been closed."),
        "REOPENED": ("Ticket {{ticket_number}} reopened", "Your ticket {{ticket_number}} has been reopened."),
    }
    template_actor = support_user
    for event_key, (subject, body) in template_defaults.items():
        if not db.scalar(select(OutlookEmailTemplate.id).where(OutlookEmailTemplate.event_key == event_key)):
            db.add(OutlookEmailTemplate(
                event_key=event_key, subject_template=subject, body_template=body,
                is_enabled=False, updated_by_user_id=template_actor.id,
            ))
    for feature_area in (
        "Database Schema", "UAT Permissions", "UAT Navigation", "UAT Dashboard", "UAT Cycle Management",
        "Test Library", "Checklist Templates", "Checklist Builder", "UAT Test Execution", "PASS Workflow",
        "FAIL Workflow", "BLOCKED Workflow", "Ticket Creation From Failure", "Ticket-to-Retest Integration",
        "Board View", "List View", "Test Attempt History", "Comments", "Attachments", "Notifications",
        "Activity Timeline", "Sign-Off", "Client Portal UAT", "Client Portal Security", "Client Testing",
        "Client Sign-Off", "Internal vs Client Results", "Live Tracking", "Secure Share Link",
        "Executive Presentation Mode", "UAT Portfolio Dashboard", "Reports", "Excel Export", "PDF Export",
        "Search", "Bulk Actions", "Test Checklist Versioning", "Ad-hoc Test Cases", "Test Case Import",
        "Automated Tests", "Performance / Index Review", "Security Review", "Final Integration Testing",
        "Production Readiness Review",
    ):
        if not db.scalar(select(UatImplementationTask.id).where(UatImplementationTask.feature_area == feature_area)):
            db.add(UatImplementationTask(
                feature_area=feature_area,
                overall_status="COMPLETED",
            ))
    db.commit()


if __name__ == "__main__":
    with SessionLocal() as session:
        seed(session)
