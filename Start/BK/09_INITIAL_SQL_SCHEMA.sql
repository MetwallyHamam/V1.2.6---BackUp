/*
  Millensys Support Hub - starter SQL Server schema
  This is a foundation example, not the complete production schema.
  Prefer Alembic migrations as the authoritative implementation.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'iam') EXEC('CREATE SCHEMA iam');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'crm') EXEC('CREATE SCHEMA crm');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'tkt') EXEC('CREATE SCHEMA tkt');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'audit') EXEC('CREATE SCHEMA audit');
GO

CREATE TABLE crm.ClientStatus (
    ClientStatusId INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ClientStatus PRIMARY KEY,
    Code NVARCHAR(50) NOT NULL CONSTRAINT UQ_ClientStatus_Code UNIQUE,
    Name NVARCHAR(100) NOT NULL,
    PortalAllowed BIT NOT NULL CONSTRAINT DF_ClientStatus_PortalAllowed DEFAULT (1),
    TicketCreationAllowed BIT NOT NULL CONSTRAINT DF_ClientStatus_TicketAllowed DEFAULT (1),
    IsActive BIT NOT NULL CONSTRAINT DF_ClientStatus_IsActive DEFAULT (1)
);
GO

CREATE TABLE crm.Client (
    ClientId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Client PRIMARY KEY,
    PublicId UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_Client_PublicId DEFAULT NEWSEQUENTIALID(),
    ClientCode NVARCHAR(50) NOT NULL,
    ClientName NVARCHAR(200) NOT NULL,
    ClientStatusId INT NOT NULL,
    DefaultTimeZoneId NVARCHAR(100) NOT NULL CONSTRAINT DF_Client_TimeZone DEFAULT ('Africa/Cairo'),
    IsDeleted BIT NOT NULL CONSTRAINT DF_Client_IsDeleted DEFAULT (0),
    CreatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_Client_CreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_Client_UpdatedAt DEFAULT SYSUTCDATETIME(),
    RowVersion ROWVERSION NOT NULL,
    CONSTRAINT UQ_Client_PublicId UNIQUE (PublicId),
    CONSTRAINT UQ_Client_ClientCode UNIQUE (ClientCode),
    CONSTRAINT FK_Client_ClientStatus FOREIGN KEY (ClientStatusId) REFERENCES crm.ClientStatus(ClientStatusId)
);
GO

CREATE TABLE crm.Branch (
    BranchId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Branch PRIMARY KEY,
    PublicId UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_Branch_PublicId DEFAULT NEWSEQUENTIALID(),
    ClientId BIGINT NOT NULL,
    BranchCode NVARCHAR(50) NOT NULL,
    BranchName NVARCHAR(200) NOT NULL,
    TimeZoneId NVARCHAR(100) NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_Branch_IsActive DEFAULT (1),
    CreatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_Branch_CreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_Branch_UpdatedAt DEFAULT SYSUTCDATETIME(),
    RowVersion ROWVERSION NOT NULL,
    CONSTRAINT UQ_Branch_PublicId UNIQUE (PublicId),
    CONSTRAINT UQ_Branch_Client_Code UNIQUE (ClientId, BranchCode),
    CONSTRAINT FK_Branch_Client FOREIGN KEY (ClientId) REFERENCES crm.Client(ClientId)
);
GO

CREATE TABLE iam.[User] (
    UserId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_User PRIMARY KEY,
    PublicId UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_User_PublicId DEFAULT NEWSEQUENTIALID(),
    UserName NVARCHAR(150) NOT NULL,
    Email NVARCHAR(320) NOT NULL,
    DisplayName NVARCHAR(200) NOT NULL,
    PasswordHash NVARCHAR(500) NULL,
    IdentityProvider NVARCHAR(50) NOT NULL CONSTRAINT DF_User_Provider DEFAULT ('local'),
    ExternalSubject NVARCHAR(255) NULL,
    IsEmployee BIT NOT NULL CONSTRAINT DF_User_IsEmployee DEFAULT (0),
    ClientId BIGINT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_User_IsActive DEFAULT (1),
    CreatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_User_CreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_User_UpdatedAt DEFAULT SYSUTCDATETIME(),
    RowVersion ROWVERSION NOT NULL,
    CONSTRAINT UQ_User_PublicId UNIQUE (PublicId),
    CONSTRAINT UQ_User_UserName UNIQUE (UserName),
    CONSTRAINT UQ_User_Email UNIQUE (Email),
    CONSTRAINT FK_User_Client FOREIGN KEY (ClientId) REFERENCES crm.Client(ClientId),
    CONSTRAINT CK_User_ClientEmployee CHECK ((IsEmployee = 1 AND ClientId IS NULL) OR (IsEmployee = 0))
);
GO

CREATE TABLE tkt.TicketType (
    TicketTypeId INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_TicketType PRIMARY KEY,
    Code NVARCHAR(30) NOT NULL CONSTRAINT UQ_TicketType_Code UNIQUE,
    Name NVARCHAR(100) NOT NULL,
    NumberPrefix NVARCHAR(10) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_TicketType_IsActive DEFAULT (1)
);
GO

CREATE TABLE tkt.TicketStatus (
    TicketStatusId INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_TicketStatus PRIMARY KEY,
    Code NVARCHAR(50) NOT NULL CONSTRAINT UQ_TicketStatus_Code UNIQUE,
    Name NVARCHAR(100) NOT NULL,
    IsClosedState BIT NOT NULL CONSTRAINT DF_TicketStatus_Closed DEFAULT (0),
    IsSlaPauseState BIT NOT NULL CONSTRAINT DF_TicketStatus_Pause DEFAULT (0),
    SortOrder INT NOT NULL
);
GO

CREATE TABLE tkt.Ticket (
    TicketId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Ticket PRIMARY KEY,
    PublicId UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_Ticket_PublicId DEFAULT NEWSEQUENTIALID(),
    TicketNumber NVARCHAR(40) NOT NULL,
    TicketTypeId INT NOT NULL,
    ClientId BIGINT NOT NULL,
    BranchId BIGINT NULL,
    CreatedByUserId BIGINT NOT NULL,
    RequesterUserId BIGINT NULL,
    TicketStatusId INT NOT NULL,
    PriorityCode NVARCHAR(10) NOT NULL,
    AssignedUserId BIGINT NULL,
    Subject NVARCHAR(300) NOT NULL,
    [Description] NVARCHAR(MAX) NOT NULL,
    PatientSafetyFlag BIT NOT NULL CONSTRAINT DF_Ticket_PatientSafety DEFAULT (0),
    FirstResponseDueAtUtc DATETIME2(3) NULL,
    ResolutionDueAtUtc DATETIME2(3) NULL,
    FirstRespondedAtUtc DATETIME2(3) NULL,
    ResolvedAtUtc DATETIME2(3) NULL,
    ClosedAtUtc DATETIME2(3) NULL,
    LastActivityAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_Ticket_LastActivity DEFAULT SYSUTCDATETIME(),
    CreatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_Ticket_CreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_Ticket_UpdatedAt DEFAULT SYSUTCDATETIME(),
    RowVersion ROWVERSION NOT NULL,
    CONSTRAINT UQ_Ticket_PublicId UNIQUE (PublicId),
    CONSTRAINT UQ_Ticket_TicketNumber UNIQUE (TicketNumber),
    CONSTRAINT FK_Ticket_Type FOREIGN KEY (TicketTypeId) REFERENCES tkt.TicketType(TicketTypeId),
    CONSTRAINT FK_Ticket_Client FOREIGN KEY (ClientId) REFERENCES crm.Client(ClientId),
    CONSTRAINT FK_Ticket_Branch FOREIGN KEY (BranchId) REFERENCES crm.Branch(BranchId),
    CONSTRAINT FK_Ticket_CreatedBy FOREIGN KEY (CreatedByUserId) REFERENCES iam.[User](UserId),
    CONSTRAINT FK_Ticket_Requester FOREIGN KEY (RequesterUserId) REFERENCES iam.[User](UserId),
    CONSTRAINT FK_Ticket_Status FOREIGN KEY (TicketStatusId) REFERENCES tkt.TicketStatus(TicketStatusId),
    CONSTRAINT FK_Ticket_AssignedUser FOREIGN KEY (AssignedUserId) REFERENCES iam.[User](UserId),
    CONSTRAINT CK_Ticket_Priority CHECK (PriorityCode IN ('P1','P2','P3','P4'))
);
GO

CREATE INDEX IX_Ticket_Client_Status_Updated
ON tkt.Ticket (ClientId, TicketStatusId, UpdatedAtUtc DESC)
INCLUDE (TicketNumber, PriorityCode, AssignedUserId, Subject, ResolutionDueAtUtc);
GO

CREATE INDEX IX_Ticket_Assigned_Status_Due
ON tkt.Ticket (AssignedUserId, TicketStatusId, ResolutionDueAtUtc)
INCLUDE (TicketNumber, ClientId, PriorityCode, Subject, UpdatedAtUtc);
GO

CREATE TABLE tkt.TicketComment (
    TicketCommentId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_TicketComment PRIMARY KEY,
    TicketId BIGINT NOT NULL,
    AuthorUserId BIGINT NOT NULL,
    IsInternal BIT NOT NULL,
    Body NVARCHAR(MAX) NOT NULL,
    CreatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_TicketComment_CreatedAt DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_TicketComment_Ticket FOREIGN KEY (TicketId) REFERENCES tkt.Ticket(TicketId),
    CONSTRAINT FK_TicketComment_Author FOREIGN KEY (AuthorUserId) REFERENCES iam.[User](UserId)
);
GO

CREATE INDEX IX_TicketComment_Ticket_Created
ON tkt.TicketComment (TicketId, CreatedAtUtc);
GO

CREATE TABLE audit.AuditEvent (
    AuditEventId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_AuditEvent PRIMARY KEY,
    EventId UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_AuditEvent_EventId DEFAULT NEWSEQUENTIALID(),
    ActorUserId BIGINT NULL,
    ClientId BIGINT NULL,
    EntityType NVARCHAR(100) NOT NULL,
    EntityId NVARCHAR(100) NOT NULL,
    ActionCode NVARCHAR(100) NOT NULL,
    SourceCode NVARCHAR(50) NOT NULL,
    Reason NVARCHAR(500) NULL,
    CorrelationId UNIQUEIDENTIFIER NULL,
    IpAddress NVARCHAR(64) NULL,
    OldValuesJson NVARCHAR(MAX) NULL,
    NewValuesJson NVARCHAR(MAX) NULL,
    CreatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_AuditEvent_CreatedAt DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_AuditEvent_EventId UNIQUE (EventId),
    CONSTRAINT FK_AuditEvent_Actor FOREIGN KEY (ActorUserId) REFERENCES iam.[User](UserId),
    CONSTRAINT FK_AuditEvent_Client FOREIGN KEY (ClientId) REFERENCES crm.Client(ClientId),
    CONSTRAINT CK_AuditEvent_OldJson CHECK (OldValuesJson IS NULL OR ISJSON(OldValuesJson) = 1),
    CONSTRAINT CK_AuditEvent_NewJson CHECK (NewValuesJson IS NULL OR ISJSON(NewValuesJson) = 1)
);
GO

CREATE INDEX IX_AuditEvent_Entity
ON audit.AuditEvent (EntityType, EntityId, CreatedAtUtc DESC);
GO
