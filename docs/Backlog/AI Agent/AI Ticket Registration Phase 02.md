You are working on an existing enterprise application named **Support Hub**.

Before implementing any new feature, perform a **full technical review of the current codebase**.

Do NOT start coding the AI, Outlook, WhatsApp, or Third-Party Integration Framework yet.

Your first task is assessment, architecture mapping, gap analysis, and implementation planning.

The objective is to understand what already exists so the new work can reuse current services, database structures, permissions, APIs, UI patterns, background jobs, notifications, audit, Knowledge Base, Pre-Tickets, tickets, integrations, and configuration mechanisms without creating duplicate architecture.

# Target Future Scope

The system will later be enhanced to support:

* Unified Communication Center
* Outlook / Microsoft Graph
* WhatsApp Business API
* AI communication agents
* AI ticket classification
* AI priority/product/module suggestions
* Missing-information detection
* Similar-ticket detection
* Knowledge Base suggestions
* Root Cause suggestion
* Professional Resolution Refactoring
* AI-assisted ticket closure review
* Third-party API management
* Integration profiles/configuration
* Webhooks
* Background integration processing
* Retry and health monitoring
* AI audit and action controls

However, **do not implement these yet**.

First review the existing code.

---

# 1. Review the Project Structure

Inspect the full solution/project structure.

Identify:

* Backend technology/framework
* Frontend technology/framework
* Database access technology
* Dependency injection model
* API architecture
* Service layer architecture
* Repository/data-access patterns
* Domain/model structure
* Configuration approach
* Logging approach
* Background processing
* Authentication
* Authorization
* Permissions
* Audit
* Notifications
* File/attachment storage
* Existing external integrations

Document the main folders/projects and their responsibility.

Do not assume the architecture.

Base the report on the actual code.

---

# 2. Review Ticket Architecture

Inspect the complete ticket lifecycle.

Identify:

* Ticket model/entity
* Ticket creation service
* Ticket update service
* Ticket status workflow
* Priority model
* Ticket type model
* Category model
* Product model
* Module model
* Assignment model
* Team assignment
* Engineer assignment
* Escalation
* SLA integration
* Resolution fields
* Root Cause fields
* Closure workflow
* Ticket history
* Attachments
* Notes/comments
* Notifications

Document which parts should be reused for AI-assisted ticket creation.

Do not create duplicate ticket logic.

---

# 3. Review Pre-Ticket Architecture

Inspect the existing Pre-Ticket implementation.

Identify:

* Database tables/entities
* API endpoints
* UI pages
* creation logic
* approval/conversion logic
* conversion to official ticket
* assignment
* rejection
* status flow
* audit
* attachments
* source tracking

Determine whether the existing Pre-Ticket module is suitable to become the intake layer for:

* Outlook
* WhatsApp
* Portal
* AI

Identify required extensions instead of proposing a replacement unless replacement is technically necessary.

---

# 4. Review Client and Contact Data

Inspect:

* Clients
* Client branches
* Client users
* contacts
* phone numbers
* emails
* portal users
* contract relationships
* dedicated engineer relationships
* department ownership

Determine whether incoming Outlook/WhatsApp senders can be mapped to existing records.

Report:

* what exists
* what is missing
* what should be extended

Do not create a duplicate client/contact structure if one already exists.

---

# 5. Review Existing Third-Party Integrations

This is especially important.

Search the current codebase for all existing integrations.

Look for:

* Microsoft Graph
* Outlook
* email sending
* SMTP
* WhatsApp
* SMS
* Fawry
* patient portal
* SAP
* external APIs
* webhooks
* HTTP clients
* RestSharp
* HttpClient
* API keys
* OAuth
* Bearer tokens
* client IDs
* client secrets
* callback URLs
* external database integrations

Search configuration sources including:

* appsettings.json
* appsettings.*.json
* web.config
* environment variables
* database configuration tables
* secrets
* hard-coded URLs
* hard-coded credentials
* service classes

Produce an **Integration Inventory**.

For each integration report:

* Integration name
* Location in code
* Current configuration source
* Authentication method
* Base URL
* Webhook usage
* Retry support
* Logging support
* Health-check support
* Whether configuration is hard-coded
* Whether credentials are securely stored
* Reusable components

Do not expose actual secrets in the report.

Mask all credentials.

---

# 6. Review Configuration Management

Identify how Support Hub currently stores:

* API URLs
* usernames
* passwords
* tokens
* API keys
* tenant IDs
* client IDs
* client secrets
* feature settings
* notification settings

Classify current configuration as:

* environment variable
* application config
* database
* secrets store
* hard-coded
* other

Identify security risks.

Do not print actual secret values.

---

# 7. Review Outlook / Email Code

Search specifically for existing email capabilities.

Identify:

* sending service
* SMTP
* Microsoft Graph
* inbound email processing
* mailbox polling
* webhook endpoints
* email templates
* attachments
* conversation IDs
* message IDs

Also search for existing environment/configuration names such as:

MICROSOFT_GRAPH_TENANT_ID
MICROSOFT_GRAPH_CLIENT_ID
MICROSOFT_GRAPH_CLIENT_SECRET
MICROSOFT_GRAPH_CLIENT_STATE
MICROSOFT_GRAPH_NOTIFICATION_URL
MICROSOFT_GRAPH_LIFECYCLE_URL

If these already exist, document:

* where they are used
* whether the Graph integration is partially implemented
* what remains missing
* what can be reused

---

# 8. Review WhatsApp Code

Search for:

* WhatsApp
* Meta
* WhatsApp Business
* webhook
* phone number ID
* access token
* incoming message
* message templates
* external_message_id

If any implementation exists, document it.

If none exists, state clearly that no implementation was found.

Do not create placeholder code during this review.

---

# 9. Review Knowledge Base

Inspect current Knowledge Base implementation.

Identify:

* article model
* categories
* Product association
* Module association
* visibility
* status
* approval
* internal/customer visibility
* search functionality
* API endpoints

Determine whether it can support:

* AI article suggestions
* customer-safe KB
* engineer-only KB
* similar resolution search

Identify only necessary schema changes.

---

# 10. Review Root Cause Architecture

Inspect the current Root Cause implementation.

Identify:

* master table
* ticket relationship
* resolution relationship
* classification
* API
* UI
* reporting

Determine how AI can suggest an existing Root Cause without creating arbitrary new values.

Do not replace current Root Cause logic.

---

# 11. Review Ticket Resolution

Inspect how resolution is currently stored.

Identify:

* resolution fields
* closure notes
* root cause
* workaround
* resolution type
* solved date
* customer confirmation
* audit/history

Determine where the future:

**AI Improve Resolution**

feature should integrate.

The AI must refactor existing engineer notes but must not bypass closure rules.

---

# 12. Review Permission System

Map the complete permission model.

Identify:

* roles
* profiles
* permission tables
* user-role mapping
* team/department restrictions
* client visibility
* ticket visibility
* API authorization checks
* frontend permission checks

Determine how future permissions should integrate.

Possible future permissions include:

COMMUNICATION_CENTER_VIEW
COMMUNICATION_REPLY
OUTLOOK_VIEW
OUTLOOK_REPLY
WHATSAPP_VIEW
WHATSAPP_REPLY
AI_USE
AI_CLASSIFICATION
AI_KB_SUGGESTION
AI_ROOT_CAUSE
AI_RESOLUTION_REFACTOR
AI_ADMIN
CHANNEL_CONFIGURATION

Do not implement them yet.

Identify the correct existing mechanism to add them later.

---

# 13. Review Notification Architecture

Inspect:

* internal notifications
* email notifications
* templates
* event-based notifications
* status notifications
* escalation notifications
* scheduled notifications

Determine whether this service can later handle:

* ticket acknowledgement
* ticket created
* more information required
* ticket status updates
* resolved
* closed
* WhatsApp notifications

Avoid creating another notification engine if one already exists.

---

# 14. Review Background Processing

Identify existing background processing technology.

Examples:

* Hangfire
* Quartz
* hosted services
* SQL Agent
* internal worker
* queue table
* message broker
* custom scheduler

Determine whether it can handle future:

* Outlook webhook processing
* WhatsApp webhook processing
* AI processing
* retries
* outbound communication
* dead-letter jobs

Report whether the existing mechanism is adequate.

---

# 15. Review Webhook Architecture

Search for existing webhook controllers/endpoints.

Identify:

* endpoint security
* verification
* request logging
* idempotency
* retry
* asynchronous processing
* webhook event storage

Determine whether a generic webhook layer already exists.

---

# 16. Review HTTP/API Client Pattern

Search how external HTTP APIs are currently called.

Identify:

* HttpClient
* HttpClientFactory
* RestSharp
* custom wrappers
* timeout handling
* authentication headers
* retries
* logging
* serialization
* error handling

Recommend reusing the strongest existing pattern.

Do not add a new third-party HTTP library unless required.

---

# 17. Review Audit Architecture

Inspect current audit capabilities.

Identify whether Support Hub already records:

* record changes
* ticket changes
* user actions
* authentication events
* admin changes
* configuration changes

Determine whether future AI audit events can reuse this system.

Future AI audit should eventually capture:

* suggestion
* accepted
* edited
* rejected
* executed

But do not implement yet.

---

# 18. Review File and Attachment Handling

Inspect how Support Hub stores:

* ticket attachments
* uploaded files
* KB files
* client files

Determine whether Outlook/WhatsApp message attachments can reuse the existing storage system.

Identify:

* size limits
* allowed MIME types
* storage path
* file security
* virus scanning if any

---

# 19. Review Database Schema

Review the relevant existing schema.

Focus on:

* tickets
* Pre-Tickets
* clients
* contacts
* contracts
* products
* modules
* priorities
* teams
* users
* permissions
* root causes
* KB
* notifications
* integrations
* audit
* attachments
* background jobs

Identify foreign-key and naming conventions.

Any future migration must follow existing conventions.

---

# 20. Identify Duplicate Architecture Risk

Actively look for cases where the proposed new architecture would duplicate existing functionality.

Examples:

If there is already:

* integration configuration
* background job queue
* notification service
* contact table
* external message log
* API audit table
* webhook framework

recommend extending it instead of creating a new parallel structure.

This is one of the main goals of this review.

---

# 21. Security Review

Inspect the current integration/security approach.

Identify:

* credentials in source code
* plain-text passwords
* API keys in config
* tokens stored without encryption
* unrestricted logging of sensitive requests
* overly broad permissions
* missing webhook verification

Do not modify them during this review.

Report severity:

* CRITICAL
* HIGH
* MEDIUM
* LOW

Do not expose secret values.

---

# 22. Produce a Gap Analysis

Create a table containing:

Area
Current Capability
Reusable
Missing
Required Change
Risk
Recommended Priority

Cover at minimum:

* Communication Center
* Outlook
* WhatsApp
* AI
* Pre-Ticket
* Contacts
* KB
* Root Cause
* Resolution
* Third-party integrations
* Webhooks
* Background processing
* Audit
* Permissions
* Notifications
* Attachments
* Analytics

---

# 23. Proposed Target Architecture

After reviewing the actual code, propose a target architecture that fits the existing project.

Do NOT blindly use the originally proposed architecture if the current system already has equivalent components.

Use existing services wherever possible.

Show:

Existing Component
→ Required Extension
→ New Component only where necessary

---

# 24. Database Change Plan

Do not execute migrations.

Propose:

* tables that can be reused
* tables that require columns
* tables that require relationships
* genuinely new tables

For every proposed new table explain why an existing table cannot handle the requirement.

Avoid unnecessary schema growth.

---

# 25. API Change Plan

Do not implement APIs.

List:

* reusable existing APIs
* APIs that need extension
* genuinely new APIs

Follow current routing and response conventions.

---

# 26. Frontend Change Plan

Review the existing UI structure.

Identify the best location for:

* Communication Center
* Unified Inbox
* AI Assistant panel
* Integration Administration
* AI Settings

Reuse existing:

* table components
* card layouts
* drawers
* dialogs
* filters
* permission directives
* status badges
* notifications

Do not introduce a new UI framework.

---

# 27. Recommended Implementation Sequence

After review, provide the safest sequence.

For example:

Phase 0 — Fix prerequisite architectural/security issues

Phase 1 — Reuse/extend current integration foundation

Phase 2 — Communication model

Phase 3 — Pre-Ticket linkage

Phase 4 — Outlook

Phase 5 — AI intake

Phase 6 — KB / Similar Tickets

Phase 7 — Root Cause / Resolution

Phase 8 — WhatsApp

Phase 9 — Controlled automation

But adapt the phases based on what actually exists.

---

# 28. Identify Quick Wins

Identify features that can be implemented quickly using existing architecture.

Examples may include:

* AI resolution refactoring
* Root Cause suggestion
* ticket summary
* KB suggestion

Only list these if the existing architecture supports them.

---

# 29. Identify High-Risk Changes

Clearly identify anything that could impact:

* ticket creation
* SLA
* permissions
* security
* production integrations
* notifications
* database performance
* existing integrations

Explain mitigation.

---

# 30. Final Review Deliverable

Do not modify code.

Produce a structured technical assessment containing:

## A. Executive Technical Summary

Short summary of current readiness.

## B. Existing Architecture

Actual architecture found in the code.

## C. Reusable Components

List what should be reused.

## D. Existing Integration Inventory

All third-party integrations found.

## E. Configuration and Secret Storage Review

Without exposing credentials.

## F. Ticket / Pre-Ticket Readiness

## G. Outlook Readiness

## H. WhatsApp Readiness

## I. AI Readiness

## J. Knowledge Base / Root Cause / Resolution Readiness

## K. Permission and Security Readiness

## L. Background Job / Webhook Readiness

## M. Gap Analysis

## N. Proposed Target Architecture

Based on the existing code.

## O. Database Change Plan

No execution.

## P. API Change Plan

No execution.

## Q. Frontend Change Plan

No execution.

## R. Risks and Technical Debt

## S. Recommended Implementation Phases

## T. Files/Modules That Will Need Changes

Give exact project paths/file names where possible.

## U. Files/Modules That Should NOT Be Changed

Where existing functionality should remain untouched.

## V. Final Recommendation

State the safest implementation approach.

---

# Mandatory Rules

1. **Do not change code in this task.**
2. Do not create database migrations.
3. Do not install packages.
4. Do not change configuration.
5. Do not expose secrets.
6. Do not create temporary placeholder integrations.
7. Inspect existing implementation before proposing new structures.
8. Prefer extending existing functionality over duplication.
9. Identify exact files/classes/services wherever possible.
10. Clearly distinguish:

* Already exists
* Partially exists
* Missing
* Needs refactoring

11. If current code contradicts this specification, report the conflict instead of forcing the new design.
12. Finish with a clear implementation plan that can be used as the input to the next Codex task.

The purpose of this task is to answer:

**"What does Support Hub already have, what can we reuse, what is missing, and what is the safest way to prepare the current system for AI Agents, Outlook, WhatsApp and centralized third-party integrations without damaging or duplicating the existing architecture?"**
