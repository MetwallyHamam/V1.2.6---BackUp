from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local", "test", "staging", "production"] = "local"
    app_name: str = "Millensys Support Hub"
    app_version: str = "0.1.0"
    secret_key: str = Field(default="development-only-change-this-secret-key", min_length=32)
    database_url: str = "sqlite+pysqlite:///./support_hub.db"
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=5, ge=0, le=50)
    database_pool_timeout_seconds: int = Field(default=15, ge=1, le=120)
    database_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)
    database_read_uncommitted: bool = True
    worker_max_requests: int = Field(default=10_000, ge=100, le=1_000_000)
    worker_max_requests_jitter: int = Field(default=1_000, ge=0, le=100_000)
    frontend_origin: str = "http://localhost:5173,http://127.0.0.1:5173"
    frontend_base_url_override: str | None = Field(default=None, validation_alias="FRONTEND_BASE_URL")
    trusted_hosts: str = "localhost,127.0.0.1,testserver"
    application_path_base: str = ""
    max_request_bytes: int = Field(default=10_485_760, ge=1024, le=104_857_600)
    attachment_storage_path: str = "./storage/attachments"
    attachment_max_bytes: int = Field(default=8_388_608, ge=1024, le=52_428_800)
    database_backup_path: str = "../backups"
    maintenance_backup_path: str = "../backups/application"
    maintenance_application_paths: str = ".,../frontend"
    maintenance_scheduler_enabled: bool = True
    maintenance_scheduler_interval_seconds: int = Field(default=60, ge=15, le=3600)
    error_log_enabled: bool = True
    error_log_path: str = "./logs/errors"
    error_log_timezone: str = "Africa/Cairo"
    error_log_retention_days: int = Field(default=30, ge=1, le=3650)
    error_log_max_total_mb: int = Field(default=512, ge=1, le=10240)
    error_log_compress_archives: bool = True
    deployment_instance_id: str = "support-hub"
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_days: int = Field(default=30, ge=1, le=90)
    login_max_failures: int = Field(default=5, ge=2, le=20)
    login_lockout_minutes: int = Field(default=15, ge=1, le=1440)
    login_hash_concurrency_per_process: int = Field(default=2, ge=1, le=16)
    login_hash_wait_seconds: int = Field(default=15, ge=1, le=120)
    password_reset_minutes: int = Field(default=30, ge=5, le=120)
    password_reset_allowed_domains: str = ""
    dev_admin_username: str | None = None
    dev_admin_email: str | None = None
    dev_admin_password: str | None = None
    monitoring_webhook_key: str = Field(default="local-monitoring-key-change-me", min_length=16)
    inbound_email_webhook_key: str = Field(default="local-email-key-change-me", min_length=16)
    integration_actor_username: str = "admin"
    microsoft_graph_tenant_id: str | None = None
    microsoft_graph_client_id: str | None = None
    microsoft_graph_client_secret: str | None = None
    microsoft_graph_client_state: str | None = None
    microsoft_graph_notification_url: str | None = None
    microsoft_graph_lifecycle_url: str | None = None
    microsoft_graph_timeout_seconds: int = Field(default=20, ge=5, le=120)
    smtp_enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_address: str = "support@localhost"
    smtp_from_name: str = "Millensys Support Hub"
    smtp_use_tls: bool = True
    email_max_attempts: int = Field(default=5, ge=1, le=20)
    sms_enabled: bool = False
    sms_gateway_url: str = "http://localhost:8080/messages"
    sms_api_token: str | None = None
    sms_sender_id: str = "Millensys"
    sms_max_attempts: int = Field(default=5, ge=1, le=20)
    teams_enabled: bool = False
    teams_webhook_url: str | None = None
    teams_max_attempts: int = Field(default=5, ge=1, le=20)
    escalation_scheduler_enabled: bool = False
    escalation_scheduler_interval_seconds: int = Field(default=60, ge=15, le=3600)
    escalation_scheduler_batch_size: int = Field(default=500, ge=25, le=5000)
    database_compatibility_check_enabled: bool = True
    local_ai_enabled: bool = True
    local_ai_base_url: str = "http://127.0.0.1:8090"
    local_ai_timeout_seconds: int = Field(default=120, ge=5, le=600)

    @property
    def frontend_base_url(self) -> str:
        """Public SPA URL, including the deployment subdirectory."""
        if self.frontend_base_url_override:
            return self.frontend_base_url_override.strip().rstrip("/")
        origin = self.frontend_origin.split(",")[0].strip().rstrip("/")
        api_base = self.application_path_base.rstrip("/")
        frontend_path = api_base.removesuffix("/backend") if api_base else ""
        return f"{origin}{frontend_path}"

    @model_validator(mode="after")
    def validate_deployment_configuration(self) -> "Settings":
        if self.app_env != "production":
            return self
        errors: list[str] = []
        if (
            self.secret_key == "development-only-change-this-secret-key"
            or self.secret_key.startswith("REPLACE_")
        ):
            errors.append("SECRET_KEY must be replaced")
        if self.database_url.startswith("sqlite"):
            errors.append("DATABASE_URL must use the production SQL Server")
        origins = [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]
        if not origins or any(not origin.startswith("https://") for origin in origins):
            errors.append("FRONTEND_ORIGIN must contain only HTTPS origins")
        if self.frontend_base_url_override and not self.frontend_base_url.startswith("https://"):
            errors.append("FRONTEND_BASE_URL must use HTTPS")
        if not self.attachment_storage_path.strip():
            errors.append("ATTACHMENT_STORAGE_PATH is required")
        if any((self.dev_admin_username, self.dev_admin_email, self.dev_admin_password)):
            errors.append("development administrator settings must be empty")
        if self.smtp_enabled and not self.smtp_host:
            errors.append("SMTP_HOST is required when SMTP is enabled")
        if self.sms_enabled and (not self.sms_gateway_url or not self.sms_api_token):
            errors.append("SMS gateway URL and token are required when SMS is enabled")
        if self.teams_enabled and not self.teams_webhook_url:
            errors.append("TEAMS_WEBHOOK_URL is required when Teams is enabled")
        if errors:
            raise ValueError("Invalid production configuration: " + "; ".join(errors))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
