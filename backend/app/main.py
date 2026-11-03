import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm.exc import StaleDataError
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.db.compatibility import DatabaseCompatibility, check_database_compatibility
from app.db.session import SessionLocal, engine, refresh_server_clock
from app.modules.audit.routes import router as audit_router
from app.modules.client_portal.routes import router as client_portal_router
from app.modules.clients.routes import catalog_router
from app.modules.clients.routes import router as clients_router
from app.modules.complaints.routes import public_router as complaint_public_router
from app.modules.complaints.routes import router as complaints_router
from app.modules.configuration.feature_routes import router as feature_policy_router
from app.modules.configuration.routes import router as configuration_router
from app.modules.contracts.routes import router as contracts_router
from app.modules.customer_success.routes import router as customer_success_router
from app.modules.dashboards.management import router as management_dashboards_router
from app.modules.dashboards.routes import router as dashboards_router
from app.modules.entitlements.routes import router as entitlement_approvals_router
from app.modules.escalations.scheduler import run_scheduler
from app.modules.finance.routes import router as manager_finance_router
from app.modules.home.routes import router as home_router
from app.modules.iam.access_requests import router as access_requests_router
from app.modules.iam.routes import (
    auth_router,
    departments_router,
    permissions_router,
    profiles_router,
    users_router,
)
from app.modules.imports.routes import router as imports_router
from app.modules.integrations.routes import router as integrations_router
from app.modules.integrations.vendor_routes import router as vendor_integrations_router
from app.modules.internal_operations.routes import router as internal_operations_router
from app.modules.knowledge_base.routes import router as knowledge_router
from app.modules.kpis.routes import router as kpis_router
from app.modules.local_ai.routes import router as local_ai_router
from app.modules.news.routes import router as news_router
from app.modules.notifications.routes import router as notifications_router
from app.modules.onboarding.routes import router as onboarding_router
from app.modules.outlook_email.routes import router as outlook_email_router
from app.modules.pre_tickets.routes import router as pre_tickets_router
from app.modules.project_handovers.routes import router as project_handovers_router
from app.modules.reports.client_profile import router as client_profile_reports_router
from app.modules.reports.dynamic_routes import router as dynamic_reports_router
from app.modules.reports.operational import router as operational_reports_router
from app.modules.reports.routes import router as reports_router
from app.modules.service_checklists.routes import public_router as service_checklists_public_router
from app.modules.service_checklists.routes import router as service_checklists_router
from app.modules.service_management.routes import router as service_management_router
from app.modules.shifts.routes import router as shifts_router
from app.modules.ticket_flags.routes import router as ticket_flags_router
from app.modules.ticket_reports.routes import public_router as ticket_reports_public_router
from app.modules.ticket_reports.routes import router as ticket_reports_router
from app.modules.tickets.live_update import (
    management_router as ticket_live_update_management_router,
)
from app.modules.tickets.live_update import public_router as ticket_live_update_public_router
from app.modules.tickets.routes import catalog_router as ticket_catalog_router
from app.modules.tickets.routes import router as tickets_router
from app.modules.tickets.satisfaction import management_router as satisfaction_management_router
from app.modules.tickets.satisfaction import router as satisfaction_router
from app.modules.uat.collaboration_routes import internal_router as uat_collaboration_router
from app.modules.uat.collaboration_routes import portal_router as uat_portal_collaboration_router
from app.modules.uat.collaboration_routes import ticket_router as uat_ticket_evidence_router
from app.modules.uat.deployment_routes import portal_router as portal_deployment_router
from app.modules.uat.deployment_routes import public_router as public_deployment_router
from app.modules.uat.deployment_routes import router as deployment_router
from app.modules.uat.import_routes import router as uat_import_router
from app.modules.uat.portal_routes import router as uat_portal_router
from app.modules.uat.reporting_routes import router as uat_reporting_router
from app.modules.uat.routes import router as uat_router
from app.modules.uat.saved_view_routes import router as uat_saved_view_router
from app.modules.uat.share_routes import internal_router as uat_share_router
from app.modules.uat.share_routes import public_router as uat_public_share_router
from app.modules.visits.routes import router as visits_router

logger = logging.getLogger(__name__)


class PathBaseMiddleware:
    def __init__(self, application: ASGIApp, path_base: str) -> None:
        self.application = application
        self.path_base = "/" + path_base.strip("/") if path_base.strip("/") else ""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = str(scope.get("path", ""))
        if self.path_base and (path == self.path_base or path.startswith(self.path_base + "/")):
            scope = dict(scope)
            scope["root_path"] = str(scope.get("root_path", "")) + self.path_base
            scope["path"] = path[len(self.path_base) :] or "/"
        await self.application(scope, receive, send)


def create_app(settings_override: Settings | None = None) -> FastAPI:
    settings = settings_override or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings)
        with SessionLocal() as clock_db:
            refresh_server_clock(clock_db)
        compatibility = DatabaseCompatibility(True, "NOT_REQUIRED")
        if (
            settings.app_env in {"staging", "production"}
            and settings.database_compatibility_check_enabled
        ):
            compatibility = check_database_compatibility(engine)
            if not compatibility.compatible:
                logger.error(
                    "Database compatibility failed status=%s revision=%s missing_table=%s missing_columns=%s",
                    compatibility.status,
                    compatibility.current_revision,
                    compatibility.missing_table,
                    compatibility.missing_columns,
                )
        application.state.database_compatibility = compatibility
        stop_event = asyncio.Event()
        scheduler_task = (
            asyncio.create_task(run_scheduler(settings, stop_event))
            if settings.escalation_scheduler_enabled
            else None
        )
        try:
            yield
        finally:
            if scheduler_task:
                stop_event.set()
                await scheduler_task

    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[host.strip() for host in settings.trusted_hosts.split(",") if host.strip()],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip() for origin in settings.frontend_origin.split(",") if origin.strip()
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-ID", "Idempotency-Key"],
    )
    if settings.application_path_base:
        app.add_middleware(PathBaseMiddleware, path_base=settings.application_path_base)

    @app.middleware("http")
    async def correlation_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        supplied = request.headers.get("X-Correlation-ID")
        try:
            correlation = str(uuid.UUID(supplied)) if supplied else str(uuid.uuid4())
        except (ValueError, AttributeError):
            correlation = str(uuid.uuid4())
        request.state.correlation_id = correlation
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation
        return response

    @app.middleware("http")
    async def database_compatibility_gate(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        compatibility = getattr(
            request.app.state,
            "database_compatibility",
            DatabaseCompatibility(True, "NOT_CHECKED"),
        )
        if not compatibility.compatible and not request.url.path.endswith(
            ("/health", "/health/database")
        ):
            correlation = getattr(request.state, "correlation_id", str(uuid.uuid4()))
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "code": "DATABASE_MIGRATION_REQUIRED",
                        "message": "The SupportHub database is not compatible with this application release. Run the database migration before using the system.",
                        "details": {
                            "status": compatibility.status,
                            "revision": compatibility.current_revision,
                            "missing_table": compatibility.missing_table,
                            "missing_columns": list(compatibility.missing_columns),
                        },
                        "correlation_id": correlation,
                    }
                },
                headers={"X-Correlation-ID": correlation},
            )
        return await call_next(request)

    @app.middleware("http")
    async def request_size_and_security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if settings.app_env == "production" and request.url.scheme != "https":
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "HTTPS_REQUIRED",
                        "message": "HTTPS is required.",
                        "details": {},
                        "correlation_id": getattr(
                            request.state, "correlation_id", str(uuid.uuid4())
                        ),
                    }
                },
            )
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                too_large = int(content_length) > settings.max_request_bytes
            except ValueError:
                too_large = True
            if too_large:
                correlation = getattr(request.state, "correlation_id", str(uuid.uuid4()))
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": "The request exceeds the configured size limit.",
                            "details": {},
                            "correlation_id": correlation,
                        }
                    },
                    headers={"X-Correlation-ID": correlation},
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Cache-Control"] = "no-store"
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "correlation_id": request.state.correlation_id,
                }
            },
        )

    @app.exception_handler(StaleDataError)
    async def stale_data_error_handler(request: Request, _: StaleDataError) -> JSONResponse:
        correlation = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "CONCURRENT_UPDATE",
                    "message": "The record was updated by another request. Refresh and try again.",
                    "details": {},
                    "correlation_id": correlation,
                }
            },
            headers={"X-Correlation-ID": correlation},
        )

    @app.exception_handler(SQLAlchemyTimeoutError)
    async def database_pool_timeout_handler(
        request: Request, _: SQLAlchemyTimeoutError
    ) -> JSONResponse:
        correlation = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        logger.warning("Database connection pool exhausted; correlation_id=%s", correlation)
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "DATABASE_BUSY",
                    "message": "The service is temporarily busy. Please retry shortly.",
                    "details": {},
                    "correlation_id": correlation,
                }
            },
            headers={"X-Correlation-ID": correlation, "Retry-After": "5"},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields: list[dict[str, object]] = []
        for raw_error in exc.errors():
            error = dict(raw_error)
            if context := error.get("ctx"):
                error["ctx"] = {
                    key: str(value) if isinstance(value, Exception) else value
                    for key, value in dict(context).items()
                }
            fields.append(error)
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "The request contains invalid data.",
                    "details": {"fields": fields},
                    "correlation_id": request.state.correlation_id,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        logger.exception(
            "Unhandled request error correlation_id=%s method=%s path=%s",
            correlation,
            request.method,
            request.url.path,
            exc_info=exc,
            extra={"correlation_id": correlation},
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                    "details": {},
                    "correlation_id": correlation,
                }
            },
        )

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(home_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(departments_router, prefix="/api/v1")
    app.include_router(profiles_router, prefix="/api/v1")
    app.include_router(permissions_router, prefix="/api/v1")
    app.include_router(access_requests_router, prefix="/api/v1")
    app.include_router(clients_router, prefix="/api/v1")
    app.include_router(catalog_router, prefix="/api/v1")
    app.include_router(tickets_router, prefix="/api/v1")
    app.include_router(local_ai_router, prefix="/api/v1")
    app.include_router(news_router, prefix="/api/v1")
    app.include_router(pre_tickets_router, prefix="/api/v1")
    app.include_router(complaints_router, prefix="/api/v1")
    app.include_router(complaint_public_router, prefix="/api/v1")
    app.include_router(satisfaction_router, prefix="/api/v1")
    app.include_router(satisfaction_management_router, prefix="/api/v1")
    app.include_router(ticket_live_update_public_router, prefix="/api/v1")
    app.include_router(ticket_live_update_management_router, prefix="/api/v1")
    app.include_router(ticket_catalog_router, prefix="/api/v1")
    app.include_router(ticket_flags_router, prefix="/api/v1")
    app.include_router(ticket_reports_router, prefix="/api/v1")
    app.include_router(ticket_reports_public_router, prefix="/api/v1")
    app.include_router(client_portal_router, prefix="/api/v1")
    app.include_router(contracts_router, prefix="/api/v1")
    app.include_router(customer_success_router, prefix="/api/v1")
    app.include_router(notifications_router, prefix="/api/v1")
    app.include_router(shifts_router, prefix="/api/v1")
    app.include_router(knowledge_router, prefix="/api/v1")
    app.include_router(kpis_router, prefix="/api/v1")
    app.include_router(imports_router, prefix="/api/v1")
    app.include_router(dashboards_router, prefix="/api/v1")
    app.include_router(management_dashboards_router, prefix="/api/v1")
    app.include_router(reports_router, prefix="/api/v1")
    app.include_router(dynamic_reports_router, prefix="/api/v1")
    app.include_router(operational_reports_router, prefix="/api/v1")
    app.include_router(client_profile_reports_router, prefix="/api/v1")
    app.include_router(integrations_router, prefix="/api/v1")
    app.include_router(vendor_integrations_router, prefix="/api/v1")
    app.include_router(internal_operations_router, prefix="/api/v1")
    app.include_router(project_handovers_router, prefix="/api/v1")
    app.include_router(configuration_router, prefix="/api/v1")
    app.include_router(feature_policy_router, prefix="/api/v1")
    app.include_router(entitlement_approvals_router, prefix="/api/v1")
    app.include_router(manager_finance_router, prefix="/api/v1")
    app.include_router(visits_router, prefix="/api/v1")
    app.include_router(outlook_email_router, prefix="/api/v1")
    app.include_router(onboarding_router, prefix="/api/v1")
    app.include_router(service_checklists_router, prefix="/api/v1")
    app.include_router(service_management_router, prefix="/api/v1")
    app.include_router(service_checklists_public_router, prefix="/api/v1")
    app.include_router(uat_router, prefix="/api/v1")
    app.include_router(deployment_router, prefix="/api/v1")
    app.include_router(portal_deployment_router, prefix="/api/v1")
    app.include_router(public_deployment_router, prefix="/api/v1")
    app.include_router(uat_portal_router, prefix="/api/v1")
    app.include_router(uat_collaboration_router, prefix="/api/v1")
    app.include_router(uat_portal_collaboration_router, prefix="/api/v1")
    app.include_router(uat_ticket_evidence_router, prefix="/api/v1")
    app.include_router(uat_reporting_router, prefix="/api/v1")
    app.include_router(uat_share_router, prefix="/api/v1")
    app.include_router(uat_public_share_router, prefix="/api/v1")
    app.include_router(uat_import_router, prefix="/api/v1")
    app.include_router(uat_saved_view_router, prefix="/api/v1")
    return app


app = create_app()
