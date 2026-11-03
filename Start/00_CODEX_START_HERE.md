# CODEX START HERE — PHASE 0 & PHASE 1

## Instruction to Codex

Read this file completely before making any changes.

You are building a production-ready web application called **Millensys Support Hub**.

The system will be used by the Millensys Support Department as a customized Ticketing System, CRM, Client Portal, Contract Management, SLA and Escalation System, Knowledge Base, Employee Shift Calendar, Notification System, Reporting Platform, and Support Dashboard.

Before starting, read all planning files in this project:

- `README.md`
- `01_IMPLEMENTATION_PLAN.md`
- `02_ARCHITECTURE.md`
- `03_DATABASE_DESIGN.md`
- `04_WORKFLOWS_AND_SLA.md`
- `05_UI_UX_SPECIFICATION.md`
- `06_SECURITY_BEST_PRACTICES.md`
- `07_TESTING_AND_DEVOPS.md`
- `08_CODEX_EXECUTION_PROMPTS.md`
- `09_INITIAL_SQL_SCHEMA.sql`
- `10_EXCEL_IMPORT_SPEC.md`
- `11_PRODUCT_BACKLOG.md`
- `12_USER_PROFILES_AND_PRIVILEGES.md`
- `.env.example`

## Technology Stack

### Backend

- Python 3.12+
- FastAPI
- SQLAlchemy 2
- Alembic
- Pydantic
- Microsoft SQL Server
- pyodbc
- JWT authentication initially
- Microsoft Entra ID support later
- WebSockets for real-time notifications
- Redis for caching, real-time messaging, and background jobs
- Celery or Dramatiq for background processing

### Frontend

- React
- TypeScript
- Vite
- Material UI
- React Router
- TanStack Query
- React Hook Form
- Zod
- AG Grid or Material UI Data Grid
- FullCalendar

### Infrastructure

- Docker for local development where practical
- SQL Server may run externally
- IIS or Nginx reverse proxy for production
- HTTPS required
- Environment-based configuration

## Architecture Rules

Build the application as a **modular monolith**.

Do not use microservices.

Use these backend modules:

- `iam`
- `users`
- `clients`
- `contacts`
- `contracts`
- `tickets`
- `sla`
- `escalations`
- `notifications`
- `knowledge_base`
- `shifts`
- `imports`
- `dashboards`
- `reports`
- `audit`
- `configuration`

Keep a clear separation between API routers, application services, repositories, SQLAlchemy models, Pydantic schemas, authorization policies, background jobs, and domain events.

Do not place business logic directly inside API endpoints.

## Current Scope

Implement only:

- Phase 0: Project Foundation
- Phase 1: Authentication, Users, Profiles, and Privileges

Do not implement the full ticketing, CRM, contract, SLA, notification, or dashboard business modules yet.

Create placeholders for future modules where needed.

## Required Deliverables

Implement:

1. Backend and frontend workspace structure.
2. FastAPI application startup.
3. React application startup.
4. Environment configuration.
5. SQL Server connection.
6. SQLAlchemy session management.
7. Alembic migrations.
8. Structured logging.
9. Global API exception handling.
10. Health-check endpoints.
11. Authentication foundation.
12. User management foundation.
13. User profile and privilege system.
14. Initial database migration.
15. Seed data for default profiles and permissions.
16. Automated backend and frontend tests.
17. Developer documentation.
18. Updated project README.

## Recommended Project Structure

```text
millensys-support-hub/
  backend/
    app/
      api/
      core/
      db/
      modules/
        iam/
        users/
        clients/
        contracts/
        tickets/
        sla/
        escalations/
        notifications/
        knowledge_base/
        shifts/
        imports/
        dashboards/
        reports/
        audit/
        configuration/
      tests/
      main.py
    alembic/
    alembic.ini
    requirements.txt
    pyproject.toml
    .env.example

  frontend/
    src/
      api/
      components/
      features/
      layouts/
      pages/
      routes/
      hooks/
      types/
      utils/
    package.json
    vite.config.ts
    tsconfig.json

  docs/
  scripts/
  docker-compose.yml
  README.md
```

You may improve the structure where necessary, but keep it clear, maintainable, and simple.

## Authentication Requirements

Implement secure local authentication initially.

Required features:

- Login using username or email
- Secure password hashing using Argon2 or bcrypt
- Short-lived access token
- Refresh token
- Refresh-token rotation
- Logout
- Account active status
- Failed-login tracking
- Account lockout support
- Last-login timestamp
- Password-change timestamp
- Require password change on next login
- Authentication event auditing

Security rules:

- Never store plain-text passwords.
- Never store plain-text refresh tokens.
- Store only hashed refresh tokens.
- Reject inactive users.
- Rate-limit login attempts.
- Do not expose internal exception details.
- Prepare the design for future Microsoft Entra ID integration.

## User Profiles and Privileges

When creating a user, the administrator must select a default profile.

Default system profiles:

- `CALL_CENTER`
- `L1_SUPPORT`
- `L2_SUPPORT`
- `L3_SUPPORT`
- `SUPPORT_MANAGER`
- `ADMINISTRATOR`
- `CLIENT_PORTAL`

Use permission codes instead of checking profile names directly.

Examples:

- `ticket.create`
- `ticket.view.own`
- `ticket.view.team`
- `ticket.view.all`
- `ticket.assign.self`
- `ticket.assign.team`
- `ticket.reassign`
- `ticket.comment.public`
- `ticket.comment.internal`
- `ticket.change.status`
- `ticket.change.priority`
- `ticket.resolve`
- `ticket.close`
- `ticket.reopen`
- `ticket.escalate`
- `client.view`
- `client.manage`
- `contract.view`
- `contract.manage`
- `knowledge.view`
- `knowledge.create`
- `knowledge.approve`
- `shift.view`
- `shift.manage`
- `dashboard.agent`
- `dashboard.manager`
- `report.view`
- `report.export`
- `user.manage`
- `profile.manage`
- `configuration.manage`
- `audit.view`

Required profile behavior:

- One primary default profile per user
- Optional additional profiles
- Active and inactive profiles
- Optional profile assignment expiry
- User-level permission allow overrides
- User-level permission deny overrides
- Client scope restrictions
- Branch scope restrictions
- System profiles cannot be deleted
- Custom profiles can be created and cloned
- Permission preview before user creation
- Full audit trail

Effective permission calculation:

1. Collect permissions from all active, non-expired assigned profiles.
2. Apply explicit user-level allow overrides.
3. Apply explicit user-level deny overrides last.
4. Apply client and branch scope restrictions separately.
5. Deny access by default.

## Required SQL Server Tables

Create SQL Server-compatible tables for:

- `users`
- `profiles`
- `permissions`
- `profile_permissions`
- `user_profiles`
- `user_permission_overrides`
- `user_client_scopes`
- `user_branch_scopes`
- `refresh_tokens`
- `authentication_events`
- `audit_logs`

Use `BIGINT IDENTITY`, `DATETIME2`, `BIT`, `NVARCHAR`, `DECIMAL` for business values, and `ROWVERSION` where useful.

Create proper foreign keys, unique constraints, check constraints, indexes, filtered indexes where useful, and auditing fields.

Do not use PostgreSQL-specific syntax or features.

## Required API Endpoints

### Health

- `GET /api/v1/health`
- `GET /api/v1/health/database`

### Authentication

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### Users

- `GET /api/v1/users`
- `POST /api/v1/users`
- `GET /api/v1/users/{user_id}`
- `PATCH /api/v1/users/{user_id}`
- `POST /api/v1/users/{user_id}/profiles`
- `DELETE /api/v1/users/{user_id}/profiles/{profile_id}`
- `GET /api/v1/users/{user_id}/effective-permissions`

### Profiles and Permissions

- `GET /api/v1/profiles`
- `POST /api/v1/profiles`
- `GET /api/v1/profiles/{profile_id}`
- `PATCH /api/v1/profiles/{profile_id}`
- `POST /api/v1/profiles/{profile_id}/clone`
- `GET /api/v1/permissions`

All protected endpoints must enforce permission dependencies on the backend.

## Frontend Requirements

Create:

- Login page
- Authenticated application layout
- Left navigation
- Top header
- Notification icon placeholder
- User profile menu
- Dashboard placeholder
- Users page
- Create User page
- Edit User page
- Profiles page
- Profile permission matrix page
- Unauthorized page
- Not Found page

The Create User page must include:

- Full name
- Username
- Email
- Employee code
- Phone number
- Department
- Job title
- Primary profile
- Additional profiles
- Client scopes
- Branch scopes
- Active account toggle
- Temporary password option
- Require password change option

When a profile is selected, display a readable permission summary before saving.

The frontend may hide or disable actions based on effective permissions, but the backend must enforce all permissions again.

## Coding Standards

### Backend

- Use type hints everywhere.
- Use async endpoints where appropriate.
- Keep services and repositories separate.
- Avoid raw SQL unless necessary.
- Use parameterized SQL only.
- Use dependency injection.
- Use Pydantic validation.
- Centralize configuration and authorization.
- Use clear custom exceptions.
- Do not use silent broad exception handling.
- Do not commit secrets.

### Frontend

- Enable TypeScript strict mode.
- Use reusable components.
- Use feature-based organization.
- Use a centralized API client.
- Use centralized authentication state.
- Use consistent validation.
- Implement loading, empty, and error states.
- Use accessible controls.
- Use a responsive layout.

## Security Requirements

Apply from the beginning:

- Password hashing
- Token expiration
- Refresh-token rotation
- Secure CORS
- Login rate limiting
- Audit sensitive actions
- Mass-assignment protection
- Privilege-escalation protection
- Inactive-account enforcement
- Client Portal isolation
- Least privilege
- Deny by default
- Server-side permission enforcement
- Safe error messages
- Secret management through environment variables

## Testing Requirements

Implement backend tests for:

- Health endpoint
- Database health endpoint
- Login success
- Login failure
- Inactive-user login denial
- Refresh-token rotation
- Logout
- Permission enforcement
- Effective-permission calculation
- Deny override winning over allow
- Expired profile assignment being ignored
- Client scope enforcement
- System-profile deletion prevention
- User creation
- Duplicate username validation
- Duplicate email validation

Implement frontend tests for:

- Login page rendering
- Protected route behavior
- Permission-based menu rendering
- Create User form validation
- Profile permission preview

## Seed Data

Seed:

- All default system profiles
- Initial permission catalog
- Profile-permission mappings
- One development administrator account

The development administrator credentials must come from environment variables.

Never hardcode administrator credentials.

## Execution Rules

Before coding:

1. Inspect the current repository.
2. Read every planning file listed at the beginning.
3. Identify existing files that should be preserved.
4. Document assumptions.
5. Create a short implementation checklist.

During implementation:

1. Work module by module.
2. Do not generate the entire application in one uncontrolled change.
3. Run tests after each meaningful module.
4. Fix errors before moving to the next module.
5. Keep SQL Server compatibility.
6. Keep the modular monolith architecture.
7. Do not add unrequested technologies without justification.
8. Do not remove working code without explaining why.
9. Update documentation as the implementation changes.

At completion:

1. Run backend tests.
2. Run frontend tests.
3. Run linting.
4. Run type checking.
5. Verify migrations.
6. Verify seed scripts.
7. Show the complete directory tree.
8. Summarize all created and changed files.
9. Explain SQL Server configuration.
10. Explain migration commands.
11. Explain seed commands.
12. Explain backend startup.
13. Explain frontend startup.
14. Explain test commands.
15. List assumptions.
16. List incomplete items.
17. Update `README.md`.

Stop after Phase 0 and Phase 1 are complete and tested.

Do not continue into tickets, CRM, contracts, SLA, escalations, notifications, client portal, knowledge base, shifts, imports, dashboards, or reports except for empty module placeholders.
