Onboarding Module – Final Feature Summary

The Onboarding module will provide a simple central page for new employees joining the department. Its purpose is to help newcomers understand the department structure, access required training materials, and complete their onboarding checklist without turning Support Hub into a complex LMS.

The module will contain three main areas:

My Checklist | Training Materials | Department Hierarchy

1. My Onboarding Checklist

The system will support reusable Onboarding Checklist Templates.

An administrator or authorized manager can create a template such as:

Technical Support Newcomer

Example checklist:

Department Introduction
Company / Department Policies
Support Hub Introduction
MiClinic / RIS Overview
WorkspaceVNA / PACS Overview
SQL Basics
Windows Server / IIS Basics
Ticket Lifecycle
Escalation Process
Client Communication
Shift / Handover Process
Shadowing
Access Verification
Final Onboarding Review

Each checklist item can contain:

Field	Purpose
Title	Checklist task name
Description	Instructions for the newcomer
Display Order	Order inside the checklist
Required	Required or optional
Related Material	Optional link to a training material
Due After Days	Expected completion after onboarding begins
Active	Enable/disable the item
Assigning a checklist

When a newcomer is created or edited, an authorized user can select:

Onboarding Template: Technical Support Newcomer
Start Date: 24-Aug-2026

Then click:

Assign Onboarding

The system creates a personal copy of that checklist for the user.

This personal checklist should be a snapshot of the template at assignment time. Changes to the master template later should not unexpectedly modify already assigned onboarding plans.

Checklist status

Keep the statuses simple:

Pending → In Progress → Completed → Skipped

The newcomer can see progress such as:

My Onboarding
7 of 13 completed — 54%

Each item can provide:

Open Material
Mark Complete

If a training material is linked to the checklist item, the newcomer can access it directly before completing the task.

2. Training Materials

The Training Materials area will organize onboarding topics.

A Training Material represents one topic, not one individual file.

For example:

PACS Architecture

Introduction to PACS architecture, workflow and basic concepts.

One topic may contain multiple resources:

PDF
SharePoint document
SharePoint folder
YouTube video
Internal Knowledge Base article
External website
Microsoft Learn page

Therefore, the system should separate:

Training Material
Field	Example
Title	PACS Architecture
Category	PACS
Description	Introduction to PACS workflow
Required	Yes
Display Order	3
Active	Yes
Material Resources

Each material can contain unlimited resources.

Field	Example
Resource Name	PACS Training PDF
Resource Type	PDF
URL	SharePoint URL
Display Order	1
Active	Yes

Another resource under the same topic could be:

Resource Name	PACS Overview Video
Type	YouTube
URL	YouTube URL

This avoids creating separate materials such as:

PACS PDF
PACS Video
PACS SharePoint

Instead, they appear under one clean topic:

PACS Architecture

📄 PDF 🔗 SharePoint ▶ Video

Material categories

Simple categories can be used, for example:

Department
Support
MiClinic / RIS
PACS / DICOM
SQL
Windows Server
IIS
Integration
HL7 / APIs
Operations
Policies

Categories should remain configurable as master data.

3. Resource Behavior

Support Hub should not duplicate SharePoint or YouTube content.

It will act as an organized index.

When the user clicks a resource:

Open Material

the URL opens in a new browser tab.

Example:

SQL Fundamentals

Open PDF
Open SharePoint
Watch Video

The application therefore stores the URL only while the real document/video remains hosted in its original location.

This makes future maintenance much easier.

4. Department Hierarchy

The Onboarding module will contain a visual Department Hierarchy so a newcomer can quickly understand:

Who is the department manager
Who their Team Leader is
Who belongs to their team
Who reports to whom
Their position inside the department

The design should follow the visual organizational-chart direction represented by the uploaded Organizational Charts reference rather than using a basic table/tree.

5. One Hierarchy Source Only

A second hierarchy must not be maintained specifically for Onboarding.

The hierarchy should come directly from the existing user structure:

User → Reports To → Manager

For example:

                    Department Manager
                           │
          ┌────────────────┼────────────────┐
          │                │                │
     Team Leader      Team Leader      Team Leader
          │
     ┌────┼────┐
     │    │    │
   User User  User

If the administrator changes:

Ahmed → Reports To → Metwally

then both the existing User Hierarchy and the Onboarding Department Hierarchy update automatically.

Therefore:

Reports To remains the master relationship.

6. User Management Enhancement

The existing User Management should continue to contain the user information required to generate the hierarchy.

Recommended fields:

Full Name
Profile Image / Avatar
Job Title
Department
Profile / System Role
Reports To
Email
Active / Inactive

The important field is:

Reports To

It should allow selecting another active user as the employee's manager.

Example:

Full Name: Ahmed Mohamed
Job Title: Support Engineer
Department: Support
Reports To: Metwally Hammam

No manual organizational-chart editing should be required.

7. User Hierarchy Redesign

The existing User Hierarchy page should also be updated to use the new organizational-chart component.

Each user should appear as a card.

Example:

┌─────────────────────────┐
│      Profile Photo      │
│                         │
│    Metwally Hammam      │
│ Support Team Leader     │
│ Support Department      │
└─────────────────────────┘

Connector lines represent the reporting relationships.

Recommended controls:

Search User | Department | Profile | Active Only | Fit Screen

The hierarchy should support:

Zoom in
Zoom out
Pan
Fit to screen
Expand team
Collapse team
Search user
Focus selected user
Show/hide direct reports
8. User Card Interaction

Clicking an employee card can open a small detail panel containing:

Employee Name
Job Title
Department
Email
Reports To
System Profile

For administrators, an optional:

Open User

button can navigate to User Management.

For newcomers using the Onboarding page, the hierarchy should remain read-only.

9. Hierarchy Validation

The system must prevent invalid Reports To relationships.

Self-reporting

Do not allow:

Ahmed → Reports To → Ahmed

Circular hierarchy

Do not allow:

Ahmed → Metwally
Metwally → Ahmed

or larger cycles such as:

A → B → C → A

The backend should validate the reporting path before saving changes.

10. Difference Between the Two Hierarchy Views

Both pages use the exact same component and data, but their purposes are different.

Administration → User Hierarchy

Management/administration view.

Can include:

Search
Filters
User details
Edit user shortcut
Full department hierarchy
Onboarding → Department Hierarchy

Newcomer-friendly view.

Mostly:

Read-only
Clean organizational chart
Employee name
Position
Department
Reporting relationship

This avoids duplicating business logic.

11. Simple Onboarding Navigation

The module should remain intentionally simple:

Onboarding

My Checklist

Assigned onboarding tasks and progress.

Training Materials

Training topics with PDFs, SharePoint links, YouTube videos, KB links, etc.

Department Hierarchy

Visual organizational chart generated from Users + Reports To.

For administrators/managers, additional management actions can appear:

Manage Materials
Checklist Templates
Newcomer Progress

These do not need to appear for normal engineers.

12. Newcomer Progress

Managers should have a small overview table.

Newcomer	Template	Start Date	Completed	Progress
Ahmed	Support Newcomer	24-Aug	7/13	54%
Sara	Support Newcomer	20-Aug	11/13	85%

Clicking the employee opens their checklist.

No complicated scoring system is required.

13. Notifications

For the first version, notifications can remain simple.

Possible events:

Onboarding assigned
Checklist item approaching due date
Checklist overdue
Onboarding completed

Example:

Onboarding Assigned
Your Technical Support onboarding checklist has been assigned.

And:

Onboarding Task Due
"SQL Fundamentals" is due tomorrow.

This can use the existing Support Hub internal notification mechanism rather than creating a separate notification engine.

14. Recommended Permission Model

Keep permissions minimal.

Normal User

Can:

View own checklist
Complete own checklist items
View training materials
Open resource URLs
View department hierarchy
Manager / Team Leader

Can additionally:

View newcomer progress
View employee onboarding checklist
Administrator / Authorized Profile

Can additionally:

Create/edit checklist templates
Assign onboarding
Create/edit materials
Add/remove resource URLs
Manage categories
Configure checklist items

User hierarchy modification should continue to follow the existing User Management permissions.

15. Suggested Data Structure

Conceptually, the feature only needs a few entities:

OnboardingChecklistTemplate
        │
        └── ChecklistTemplateItem

User
 │
 └── UserOnboarding
        │
        └── UserOnboardingItem

TrainingMaterial
        │
        └── TrainingMaterialResource

User
 └── ReportsToUserID

The hierarchy does not need a separate table unless the current user architecture requires it.

The organization chart should simply interpret:

UserID + ReportsToUserID

Final Feature Concept

The resulting workflow is very simple:

Administrator creates
Onboarding Checklist Template
            │
            ▼
New User Created
            │
            ▼
Select Template + Start Date
            │
            ▼
Checklist Assigned
            │
            ▼
Newcomer Opens ONBOARDING
            │
       ┌────┼───────────────┐
       ▼    ▼               ▼
 Checklist Training     Department
          Materials      Hierarchy
             │
             ▼
       PDF / SharePoint
       YouTube / KB / URL

The main principle should be:

Support Hub organizes the onboarding journey; it does not replace SharePoint, YouTube, the Knowledge Base, or User Management.

That gives you a lightweight but useful onboarding feature with centralized training access, reusable checklists, progress tracking, and a modern automatically generated department hierarchy.