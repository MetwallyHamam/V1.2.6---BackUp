from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.exceptions import AuthorizationError
from app.modules.clients.models import (
    Branch,
    Client,
    ClientLocation,
    SupportTeamMember,
)
from app.modules.iam.models import User
from app.modules.tickets.models import Ticket
from app.modules.tickets.service import visible_ticket_query

# Interactive endpoint budgets. Production-scale acceptance still requires the
# separate SQL Server fixtures; these limits prevent ordinary endpoint changes
# from silently regressing query shape or returning export-sized payloads.
DASHBOARD_SUMMARY_MAX_QUERIES = 55
DASHBOARD_ASSIGNMENT_IMPACT_MAX_QUERIES = 8
DASHBOARD_INTERACTIVE_MAX_SECONDS = 5.0
DASHBOARD_SUMMARY_MAX_RESPONSE_BYTES = 2_000_000
DASHBOARD_ASSIGNMENT_IMPACT_MAX_RESPONSE_BYTES = 1_000_000
DASHBOARD_SUMMARY_MAX_PEAK_BYTES = 64 * 1024 * 1024
DASHBOARD_SUMMARY_MAX_DETAIL_ROWS = 2_000
DASHBOARD_ASSIGNMENT_IMPACT_MAX_ROWS = 10_000


@dataclass(frozen=True)
class DashboardTicketFilters:
    country_id: int | None = None
    zone: str | None = None
    client_id: int | None = None
    location_id: int | None = None
    product_id: int | None = None
    engineer_id: int | None = None
    team_id: int | None = None


@dataclass(frozen=True)
class AuthenticatedDashboardScope:
    """Ticket scope derived only from the authenticated user.

    Dashboard layouts and request filters may narrow this query, but they must
    never replace or expand it. Department descendants and client sharing are
    intentionally left to the central ticket policy until those contracts are
    approved.
    """

    db: Session
    user: User

    def ticket_query(self) -> Select[tuple[Ticket]]:
        return visible_ticket_query(self.db, self.user)

    def ensure_filters_allowed(self, filters: DashboardTicketFilters) -> None:
        scope = self.ticket_query()
        for selected, column, label in (
            (filters.client_id, Ticket.client_id, "client"),
            (filters.product_id, Ticket.product_id, "product"),
            (filters.engineer_id, Ticket.assigned_user_id, "engineer"),
        ):
            if selected is not None and not self.db.scalar(
                select(scope.where(column == selected).exists())
            ):
                raise AuthorizationError(
                    f"The selected {label} is outside your dashboard scope."
                )

        if filters.team_id is not None:
            team_members = select(SupportTeamMember.user_id).where(
                SupportTeamMember.team_id == filters.team_id
            )
            if not self.db.scalar(
                select(
                    scope.where(
                        or_(
                            Ticket.routed_team_id == filters.team_id,
                            Ticket.assigned_user_id.in_(team_members),
                        )
                    ).exists()
                )
            ):
                raise AuthorizationError("The selected team is outside your dashboard scope.")

        if filters.country_id is not None or filters.zone or filters.location_id is not None:
            branch_location = aliased(ClientLocation)
            client_location = aliased(ClientLocation)
            geographic_scope = (
                scope.join(Client, Client.id == Ticket.client_id)
                .outerjoin(Branch, Branch.id == Ticket.branch_id)
                .outerjoin(branch_location, branch_location.id == Branch.location_id)
                .outerjoin(client_location, client_location.id == Client.primary_location_id)
            )
            dimensions: tuple[tuple[Any, Any, str], ...] = (
                (
                    filters.country_id,
                    func.coalesce(
                        branch_location.country_id,
                        client_location.country_id,
                        Client.country_id,
                    ),
                    "country",
                ),
                (
                    filters.zone,
                    func.coalesce(branch_location.zone, client_location.zone, Client.zone),
                    "zone",
                ),
                (
                    filters.location_id,
                    func.coalesce(branch_location.id, client_location.id),
                    "location",
                ),
            )
            for selected, column, label in dimensions:
                if selected is not None and not self.db.scalar(
                    select(geographic_scope.where(column == selected).exists())
                ):
                    raise AuthorizationError(
                        f"The selected {label} is outside your dashboard scope."
                    )
