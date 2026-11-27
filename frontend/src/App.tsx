import { Box, CircularProgress } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { api } from "./api/client";
import { AppLayout } from "./layouts/AppLayout";
import { ProjectManagementPage } from "./pages/ProjectManagementPage";
import { ProjectSchedulePage } from "./pages/ProjectSchedulePage";
import { ProjectRevisionQueue, ProjectWorkPackagesPage } from "./pages/ProjectWorkPackagesPage";
import { ProjectRegisterPage } from "./pages/ProjectRegisterPage";
import { ImplementationWorkspacePage } from "./pages/ImplementationWorkspacePage";
import { SupportHandoverInboxPage } from "./pages/SupportHandoverInboxPage";
import { implementationWorkspacePath, implementationWorkspacePermission, projectMyWorkPath, projectWorkspacePath, projectWorkspacePermission } from "./auth/projectWorkspaceAccess";
import {
  ProjectWorkspaceCollaboration,
  ProjectWorkspaceHandover,
  ProjectWorkspaceIntake,
  ProjectWorkspaceOverview,
  ProjectWorkspacePage,
} from "./pages/ProjectWorkspacePage";
import { ProjectTemplatesPage } from "./pages/ProjectTemplatesPage";
import { ProtectedRoute } from "./routes/ProtectedRoute";
import { PermissionRoute } from "./routes/PermissionRoute";
import { InternalUserRoute } from "./routes/InternalUserRoute";
import { setServerTimezone } from "./utils/serverTime";

const ClientsPage = lazy(() =>
  import("./pages/ClientsPage").then((module) => ({
    default: module.ClientsPage,
  })),
);
const CustomerStructurePage = lazy(() =>
  import("./pages/CustomerStructurePage").then((module) => ({
    default: module.CustomerStructurePage,
  })),
);
const CompanyOperationsSetupPage = lazy(() =>
  import("./pages/CompanyOperationsSetupPage").then((module) => ({
    default: module.CompanyOperationsSetupPage,
  })),
);
const ProjectsPage = lazy(() =>
  import("./pages/ProjectsPage").then((module) => ({ default: module.ProjectsPage })),
);
const ProjectExecutionPage = lazy(() =>
  import("./pages/ProjectExecutionPage").then((module) => ({ default: module.ProjectExecutionPage })),
);
const ProjectAnalyticsPage = lazy(() =>
  import("./pages/ProjectAnalyticsPage").then((module) => ({ default: module.ProjectAnalyticsPage })),
);
const ImplementationAnalyticsPage = lazy(() =>
  import("./pages/ImplementationAnalyticsPage").then((module) => ({ default: module.ImplementationAnalyticsPage })),
);
const ImplementationIntakePage = lazy(() =>
  import("./pages/ImplementationIntakePage").then((module) => ({ default: module.ImplementationIntakePage })),
);
const SupportReadinessAnalyticsPage = lazy(() =>
  import("./pages/SupportReadinessAnalyticsPage").then((module) => ({ default: module.SupportReadinessAnalyticsPage })),
);
const ComplaintsPage = lazy(() =>
  import("./pages/ComplaintsPage").then((module) => ({
    default: module.ComplaintsPage,
  })),
);
const CustomerSuccessPage = lazy(() =>
  import("./pages/CustomerSuccessPage").then((module) => ({
    default: module.CustomerSuccessPage,
  })),
);
const ComplaintTrackingPage = lazy(() =>
  import("./pages/ComplaintTrackingPage").then((module) => ({
    default: module.ComplaintTrackingPage,
  })),
);
const PublicChecklistEventPage = lazy(() =>
  import("./pages/PublicChecklistEventPage").then((module) => ({
    default: module.PublicChecklistEventPage,
  })),
);
const AuditLogsPage = lazy(() =>
  import("./pages/AuditLogsPage").then((module) => ({
    default: module.AuditLogsPage,
  })),
);
const AccessRequestsPage = lazy(() =>
  import("./pages/AccessRequestsPage").then((module) => ({
    default: module.AccessRequestsPage,
  })),
);
const ChangePasswordPage = lazy(() =>
  import("./pages/ChangePasswordPage").then((module) => ({
    default: module.ChangePasswordPage,
  })),
);
const ContractWorkspacePage = lazy(() =>
  import("./pages/ContractWorkspacePage").then((module) => ({
    default: module.ContractWorkspacePage,
  })),
);
const CreateTicketPage = lazy(() =>
  import("./pages/CreateTicketPage").then((module) => ({
    default: module.CreateTicketPage,
  })),
);
const CreateUserPage = lazy(() =>
  import("./pages/CreateUserPage").then((module) => ({
    default: module.CreateUserPage,
  })),
);
const CrmCatalogsPage = lazy(() =>
  import("./pages/CrmCatalogsPage").then((module) => ({
    default: module.CrmCatalogsPage,
  })),
);
const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((module) => ({
    default: module.DashboardPage,
  })),
);
const MyWorkspacePage = lazy(() =>
  import("./pages/MyWorkspacePage").then((module) => ({
    default: module.MyWorkspacePage,
  })),
);
const WorkAssignmentsPage = lazy(() => import("./pages/WorkAssignmentsPage").then((module) => ({ default: module.WorkAssignmentsPage })));
const MaintenancePage = lazy(() => import("./pages/MaintenancePage").then((module) => ({ default: module.MaintenancePage })));
const PublicWorkAssignmentPage = lazy(() => import("./pages/PublicWorkAssignmentPage").then((module) => ({ default: module.PublicWorkAssignmentPage })));
const DashboardAdminPage = lazy(() =>
  import("./pages/DashboardAdminPage").then((module) => ({
    default: module.DashboardAdminPage,
  })),
);
const ManagementDashboardsPage = lazy(() =>
  import("./pages/ManagementDashboardsPage").then((module) => ({
    default: module.ManagementDashboardsPage,
  })),
);
const FinancialPage = lazy(() =>
  import("./pages/FinancialPage").then((module) => ({
    default: module.FinancialPage,
  })),
);
const OperationsWorkspacePage = lazy(() =>
  import("./pages/OperationsWorkspacePage").then((module) => ({
    default: module.OperationsWorkspacePage,
  })),
);
const OnboardingPage = lazy(() =>
  import("./pages/OnboardingPage").then((module) => ({
    default: module.OnboardingPage,
  })),
);
const OrganizationHierarchyPage = lazy(() =>
  import("./pages/OrganizationHierarchyPage").then((module) => ({
    default: module.OrganizationHierarchyPage,
  })),
);
const EditClientPage = lazy(() =>
  import("./pages/EditClientPage").then((module) => ({
    default: module.EditClientPage,
  })),
);
const ClientProfilePage = lazy(() =>
  import("./pages/ClientProfilePage").then((module) => ({
    default: module.ClientProfilePage,
  })),
);
const ClientEvidencePage = lazy(() =>
  import("./pages/ClientEvidencePage").then((module) => ({
    default: module.ClientEvidencePage,
  })),
);
const EditUserPage = lazy(() =>
  import("./pages/EditUserPage").then((module) => ({
    default: module.EditUserPage,
  })),
);
const EmailIntegrationPage = lazy(() =>
  import("./pages/EmailIntegrationPage").then((module) => ({
    default: module.EmailIntegrationPage,
  })),
);
const EscalationsPage = lazy(() =>
  import("./pages/EscalationsPage").then((module) => ({
    default: module.EscalationsPage,
  })),
);
const ImportsPage = lazy(() =>
  import("./pages/ImportsPage").then((module) => ({
    default: module.ImportsPage,
  })),
);
const ProjectHandoversPage = lazy(() =>
  import("./pages/ProjectHandoversPage").then((module) => ({
    default: module.ProjectHandoversPage,
  })),
);
const KnowledgePage = lazy(() =>
  import("./pages/KnowledgePage").then((module) => ({
    default: module.KnowledgePage,
  })),
);
const KpiReviewsPage = lazy(() =>
  import("./pages/KpiReviewsPage").then((module) => ({
    default: module.KpiReviewsPage,
  })),
);
const LoginPage = lazy(() =>
  import("./pages/LoginPage").then((module) => ({ default: module.LoginPage })),
);
const ForgotPasswordPage = lazy(() =>
  import("./pages/ForgotPasswordPage").then((module) => ({
    default: module.ForgotPasswordPage,
  })),
);
const HomePage = lazy(() =>
  import("./pages/HomePage").then((module) => ({ default: module.HomePage })),
);
const MyFieldVisitsPage = lazy(() =>
  import("./pages/MyFieldVisitsPage").then((module) => ({
    default: module.MyFieldVisitsPage,
  })),
);
const ResetPasswordPage = lazy(() =>
  import("./pages/ResetPasswordPage").then((module) => ({
    default: module.ResetPasswordPage,
  })),
);
const SatisfactionPage = lazy(() =>
  import("./pages/SatisfactionPage").then((module) => ({
    default: module.SatisfactionPage,
  })),
);
const TicketLiveUpdatePage = lazy(() =>
  import("./pages/TicketLiveUpdatePage").then((module) => ({
    default: module.TicketLiveUpdatePage,
  })),
);
const NotFoundPage = lazy(() =>
  import("./pages/NotFoundPage").then((module) => ({
    default: module.NotFoundPage,
  })),
);
const NotificationsPage = lazy(() =>
  import("./pages/NotificationsPage").then((module) => ({
    default: module.NotificationsPage,
  })),
);
const NewsPage = lazy(() =>
  import("./pages/NewsPage").then((module) => ({ default: module.NewsPage })),
);
const PortalCreateTicketPage = lazy(() =>
  import("./pages/PortalCreateTicketPage").then((module) => ({
    default: module.PortalCreateTicketPage,
  })),
);
const PortalDashboardPage = lazy(() =>
  import("./pages/PortalDashboardPage").then((module) => ({
    default: module.PortalDashboardPage,
  })),
);
const PortalClientProfilePage = lazy(() =>
  import("./pages/PortalClientProfilePage").then((module) => ({
    default: module.PortalClientProfilePage,
  })),
);
const PortalTicketDetailPage = lazy(() =>
  import("./pages/PortalTicketDetailPage").then((module) => ({
    default: module.PortalTicketDetailPage,
  })),
);
const PortalTicketsPage = lazy(() =>
  import("./pages/PortalTicketsPage").then((module) => ({
    default: module.PortalTicketsPage,
  })),
);
const PortalUatPage = lazy(() =>
  import("./pages/PortalUatPage").then((module) => ({
    default: module.PortalUatPage,
  })),
);
const PublicUatTrackingPage = lazy(() =>
  import("./pages/PublicUatTrackingPage").then((module) => ({
    default: module.PublicUatTrackingPage,
  })),
);
const PublicDeploymentTrackingPage = lazy(() =>
  import("./pages/PublicDeploymentTrackingPage").then((module) => ({
    default: module.PublicDeploymentTrackingPage,
  })),
);
const ExternalPreTicketPage = lazy(() =>
  import("./pages/ExternalPreTicketPage").then((module) => ({
    default: module.ExternalPreTicketPage,
  })),
);
const PreTicketsPage = lazy(() =>
  import("./pages/PreTicketsPage").then((module) => ({
    default: module.PreTicketsPage,
  })),
);
const SupportWorkspacePage = lazy(() =>
  import("./pages/SupportWorkspacePage").then((module) => ({
    default: module.SupportWorkspacePage,
  })),
);
const ProfilesPage = lazy(() =>
  import("./pages/ProfilesPage").then((module) => ({
    default: module.ProfilesPage,
  })),
);
const SavedViewsPage = lazy(() =>
  import("./pages/SavedViewsPage").then((module) => ({
    default: module.SavedViewsPage,
  })),
);
const SystemOperationsPage = lazy(() =>
  import("./pages/SystemOperationsPage").then((module) => ({
    default: module.SystemOperationsPage,
  })),
);
const TicketDetailPage = lazy(() =>
  import("./pages/TicketDetailPage").then((module) => ({
    default: module.TicketDetailPage,
  })),
);
const ChangeRequestWorkspacePage = lazy(() =>
  import("./pages/ChangeRequestWorkspacePage").then((module) => ({
    default: module.ChangeRequestWorkspacePage,
  })),
);
const ChangeRequestsPage = lazy(() =>
  import("./pages/ChangeRequestsPage").then((module) => ({
    default: module.ChangeRequestsPage,
  })),
);
const ProblemsPage = lazy(() =>
  import("./pages/ProblemsPage").then((module) => ({
    default: module.ProblemsPage,
  })),
);
const ProblemWorkspacePage = lazy(() =>
  import("./pages/ProblemWorkspacePage").then((module) => ({
    default: module.ProblemWorkspacePage,
  })),
);
const MajorIncidentsPage = lazy(() =>
  import("./pages/MajorIncidentsPage").then((module) => ({
    default: module.MajorIncidentsPage,
  })),
);
const MajorIncidentWorkspacePage = lazy(() =>
  import("./pages/MajorIncidentWorkspacePage").then((module) => ({
    default: module.MajorIncidentWorkspacePage,
  })),
);
const TicketFormSettingsPage = lazy(() =>
  import("./pages/TicketFormSettingsPage").then((module) => ({
    default: module.TicketFormSettingsPage,
  })),
);
const TicketsPage = lazy(() =>
  import("./pages/TicketsPage").then((module) => ({
    default: module.TicketsPage,
  })),
);
const TicketTemplatesPage = lazy(() =>
  import("./pages/TicketTemplatesPage").then((module) => ({
    default: module.TicketTemplatesPage,
  })),
);
const ServiceChecklistsPage = lazy(() =>
  import("./pages/ServiceChecklistsPage").then((module) => ({
    default: module.ServiceChecklistsPage,
  })),
);
const UatPage = lazy(() =>
  import("./pages/UatPage").then((module) => ({ default: module.UatPage })),
);
const UnauthorizedPage = lazy(() =>
  import("./pages/UnauthorizedPage").then((module) => ({
    default: module.UnauthorizedPage,
  })),
);
const UsersPage = lazy(() =>
  import("./pages/UsersPage").then((module) => ({ default: module.UsersPage })),
);
const ReportsCenterPage = lazy(() =>
  import("./pages/ReportsCenterPage").then((module) => ({
    default: module.ReportsCenterPage,
  })),
);
const PublicTicketReportPage = lazy(() =>
  import("./pages/PublicTicketReportPage").then((module) => ({
    default: module.PublicTicketReportPage,
  })),
);

export function App() {
  const serverClock = useQuery({
    queryKey: ["server-clock"],
    queryFn: async () =>
      (await api.get<{ server_timezone: string }>("/system/time-settings"))
        .data,
    staleTime: 60_000,
  });
  useEffect(() => {
    if (serverClock.data?.server_timezone)
      setServerTimezone(serverClock.data.server_timezone);
  }, [serverClock.data?.server_timezone]);
  return (
    <Suspense
      fallback={
        <Box sx={{ minHeight: "60vh", display: "grid", placeItems: "center" }}>
          <CircularProgress aria-label="Loading page" />
        </Box>
      }
    >
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/satisfaction" element={<SatisfactionPage />} />
        <Route path="/ticket-update" element={<TicketLiveUpdatePage />} />
        <Route path="/complaint-track" element={<ComplaintTrackingPage />} />
        <Route
          path="/shared/checklists/:token"
          element={<PublicChecklistEventPage />}
        />
        <Route path="/uat-share/:token" element={<PublicUatTrackingPage />} />
        <Route path="/deployment-live/:token" element={<PublicDeploymentTrackingPage />} />
        <Route path="/work-assignment-live/:token" element={<PublicWorkAssignmentPage />} />
        <Route
          path="/shared/reports/:token"
          element={<PublicTicketReportPage />}
        />
        <Route
          path="/external/pre-ticket/:token"
          element={<ExternalPreTicketPage />}
        />
        <Route element={<ProtectedRoute />}>
          <Route path="change-password" element={<ChangePasswordPage />} />
          <Route
            element={
              <PermissionRoute
                anyOf={[
                  "ticket.view.own",
                  "ticket.view.team",
                  "ticket.view.department",
                  "ticket.view.all",
                  "ticket.pre_ticket.view.own",
                  "ticket.pre_ticket.queue.view",
                ]}
              />
            }
          >
            <Route
              path="support-assistant-app"
              element={<SupportWorkspacePage />}
            />
          </Route>
          <Route element={<AppLayout />}>
            <Route index element={<Navigate to="/home" replace />} />
            <Route element={<InternalUserRoute />}>
              <Route path="home" element={<HomePage />} />
              <Route path="my-workspace" element={<MyWorkspacePage />} />
              <Route path="work-assignments" element={<WorkAssignmentsPage />} />
              <Route element={<PermissionRoute anyOf={["maintenance.view"]} />}><Route path="maintenance" element={<MaintenancePage />} /></Route>
              <Route
                path="organization"
                element={<OrganizationHierarchyPage />}
              />
            </Route>
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="users" element={<UsersPage />} />
            <Route element={<PermissionRoute anyOf={["user.manage"]} />}>
              <Route
                path="organization/configure"
                element={<OrganizationHierarchyPage />}
              />
            </Route>
            <Route
              element={
                <PermissionRoute anyOf={["topmanagementdashboard.view"]} />
              }
            >
              <Route
                path="management-dashboards"
                element={<ManagementDashboardsPage />}
              />
            </Route>
            <Route
              element={<PermissionRoute anyOf={["dashboard.manage_widgets"]} />}
            >
              <Route path="dashboard-admin" element={<DashboardAdminPage />} />
            </Route>
            <Route path="financial" element={<FinancialPage />} />
            <Route path="manager-finance" element={<FinancialPage />} />
            <Route path="payments" element={<FinancialPage />} />
            <Route path="clients" element={<ClientsPage />} />
            <Route
              element={
                <PermissionRoute
                  anyOf={["customer_structure.policy.view", "client.view"]}
                />
              }
            >
              <Route
                path="customer-structure"
                element={<CustomerStructurePage />}
              />
            </Route>
            <Route
              element={
                <PermissionRoute
                  anyOf={["customer_structure.policy.view", "client.manage", "project.manage"]}
                />
              }
            >
              <Route path="company-operations-setup" element={<CompanyOperationsSetupPage />} />
            </Route>
            <Route path="customer-success" element={<CustomerSuccessPage />} />
            <Route path="clients/:id/edit" element={<EditClientPage />} />
            <Route path="clients/:id/profile" element={<ClientProfilePage />} />
            <Route
              path="clients/:id/evidence"
              element={<ClientEvidencePage />}
            />
            <Route path="crm" element={<CrmCatalogsPage />} />
            <Route
              element={
                <PermissionRoute
                  anyOf={["contract.view", "contract.template.view"]}
                />
              }
            >
              <Route path="contracts" element={<ContractWorkspacePage />} />
              <Route
                path="contract-templates"
                element={<Navigate to="/contracts?section=templates" replace />}
              />
            </Route>
            <Route path="notifications" element={<NotificationsPage />} />
            <Route path="escalations" element={<EscalationsPage />} />
            <Route element={<PermissionRoute anyOf={["news.view"]} />}>
              <Route path="news" element={<NewsPage />} />
            </Route>
            <Route
              element={
                <PermissionRoute
                  anyOf={[
                    "internal_operation.workspace.view",
                    "internal_operation.view",
                    "shift.view",
                    "visit.entitlement.view",
                    "dashboard.manager",
                  ]}
                />
              }
            >
              <Route
                path="shifts"
                element={
                  <Navigate
                    to="/internal-operations?section=calendar"
                    replace
                  />
                }
              />
              <Route
                path="visit-operations"
                element={<OperationsWorkspacePage />}
              />
              <Route
                path="internal-operations"
                element={<OperationsWorkspacePage />}
              />
              <Route
                path="operational-reports"
                element={<OperationsWorkspacePage />}
              />
            </Route>
            <Route path="onboarding" element={<OnboardingPage />} />
            <Route element={<PermissionRoute anyOf={["project.portfolio.view"]} />}>
              <Route element={<PermissionRoute anyOf={[projectWorkspacePermission]} />}>
                <Route path={projectWorkspacePath.slice(1)} element={<ProjectManagementPage key="overview" />} />
                <Route path={projectMyWorkPath.slice(1)} element={<ProjectManagementPage key="my-work" personal />} />
                <Route path="project-management" element={<Navigate to={projectWorkspacePath} replace />} />
              </Route>
              <Route path="projects" element={<ProjectsPage />} />
              <Route path="projects/:id" element={<ProjectWorkspacePage />}>
                <Route index element={<ProjectWorkspaceOverview />} />
                <Route path="work-packages" element={<ProjectWorkPackagesPage />} />
                <Route path="revisions" element={<ProjectRevisionQueue />} />
                <Route path="register" element={<ProjectRegisterPage />} />
                <Route path="schedule" element={<ProjectSchedulePage />} />
                <Route path="intake" element={<ProjectWorkspaceIntake />} />
                <Route element={<PermissionRoute anyOf={["implementation.task.view"]} />}>
                  <Route path="execution" element={<ProjectExecutionPage />} />
                </Route>
                <Route element={<PermissionRoute anyOf={["cross_department.request.create"]} />}>
                  <Route path="collaboration" element={<ProjectWorkspaceCollaboration />} />
                </Route>
                <Route element={<PermissionRoute anyOf={["handover.view"]} />}>
                  <Route path="handover" element={<ProjectWorkspaceHandover />} />
                </Route>
              </Route>
            </Route>
            <Route element={<PermissionRoute anyOf={[projectWorkspacePermission]} />}>
              <Route element={<PermissionRoute anyOf={["project.create"]} />}>
                <Route path="project-templates" element={<ProjectTemplatesPage />} />
              </Route>
            </Route>
            <Route element={<PermissionRoute anyOf={["analytics.project.view"]} />}>
              <Route path="project-analytics" element={<ProjectAnalyticsPage />} />
            </Route>
            <Route element={<PermissionRoute anyOf={["analytics.implementation.view"]} />}>
              <Route path="implementation-analytics" element={<ImplementationAnalyticsPage />} />
            </Route>
            <Route element={<PermissionRoute anyOf={[implementationWorkspacePermission]} />}>
              <Route path={implementationWorkspacePath.slice(1)} element={<ImplementationWorkspacePage />} />
              <Route element={<PermissionRoute anyOf={["project.assignment.respond"]} />}>
                <Route path="implementation-intake" element={<ImplementationIntakePage />} />
              </Route>
            </Route>
            <Route element={<PermissionRoute anyOf={["handover.review"]} />}>
              <Route path="support-handover-inbox" element={<SupportHandoverInboxPage />} />
            </Route>
            <Route element={<PermissionRoute anyOf={["analytics.support_readiness.view"]} />}>
              <Route path="support-readiness" element={<SupportReadinessAnalyticsPage />} />
            </Route>
            <Route element={<PermissionRoute anyOf={["report.view"]} />}>
              <Route path="reports" element={<ReportsCenterPage />} />
            </Route>
            <Route
              element={
                <PermissionRoute
                  anyOf={[
                    "service_checklist.view_own",
                    "service_checklist.template.view",
                    "service_checklist.template.manage",
                  ]}
                />
              }
            >
              <Route
                path="service-checklists"
                element={<ServiceChecklistsPage />}
              />
            </Route>
            <Route element={<PermissionRoute anyOf={["uat.view"]} />}>
              <Route path="uat" element={<UatPage />} />
            </Route>
            <Route
              element={<PermissionRoute anyOf={["project_handover.view"]} />}
            >
              <Route
                path="project-handovers"
                element={<ProjectHandoversPage />}
              />
            </Route>
            <Route path="knowledge" element={<KnowledgePage />} />
            <Route path="kpis" element={<KpiReviewsPage />} />
            <Route path="imports" element={<ImportsPage />} />
            <Route path="system" element={<SystemOperationsPage />} />
            <Route
              path="system/email-integration"
              element={<EmailIntegrationPage />}
            />
            <Route
              path="ticket-form-settings"
              element={<TicketFormSettingsPage />}
            />
            <Route path="audit" element={<AuditLogsPage />} />
            <Route path="access-requests" element={<AccessRequestsPage />} />
            <Route path="saved-views" element={<SavedViewsPage />} />
            <Route path="tickets" element={<TicketsPage />} />
            <Route
              element={<PermissionRoute anyOf={["ticket.template.manage"]} />}
            >
              <Route
                path="ticket-templates"
                element={<TicketTemplatesPage />}
              />
            </Route>
            <Route element={<PermissionRoute anyOf={["ticket.create"]} />}>
              <Route path="tickets/create" element={<CreateTicketPage />} />
            </Route>
            <Route
              element={<PermissionRoute anyOf={["visit.field.create.self"]} />}
            >
              <Route path="field-visits" element={<MyFieldVisitsPage />} />
            </Route>
            <Route path="tickets/:id" element={<TicketDetailPage />} />
            <Route
              element={<PermissionRoute anyOf={["change_request.view"]} />}
            >
              <Route path="change-requests" element={<ChangeRequestsPage />} />
              <Route
                path="tickets/:id/change-request"
                element={<ChangeRequestWorkspacePage />}
              />
            </Route>
            <Route element={<PermissionRoute anyOf={["problem.view"]} />}>
              <Route path="problems" element={<ProblemsPage />} />
              <Route path="problems/:id" element={<ProblemWorkspacePage />} />
            </Route>
            <Route
              element={<PermissionRoute anyOf={["major_incident.view"]} />}
            >
              <Route path="major-incidents" element={<MajorIncidentsPage />} />
              <Route
                path="major-incidents/:id"
                element={<MajorIncidentWorkspacePage />}
              />
            </Route>
            <Route
              element={
                <PermissionRoute
                  anyOf={[
                    "ticket.pre_ticket.create",
                    "ticket.pre_ticket.view.own",
                    "ticket.pre_ticket.queue.view",
                  ]}
                />
              }
            >
              <Route path="tickets/pre-tickets" element={<PreTicketsPage />} />
            </Route>
            <Route
              element={
                <PermissionRoute
                  anyOf={[
                    "ticket.view.own",
                    "ticket.view.team",
                    "ticket.view.department",
                    "ticket.view.all",
                    "ticket.pre_ticket.view.own",
                    "ticket.pre_ticket.queue.view",
                  ]}
                />
              }
            >
              <Route
                path="support-workspace"
                element={<SupportWorkspacePage />}
              />
            </Route>
            <Route path="complaints" element={<ComplaintsPage />} />
            <Route path="complaints/:id" element={<ComplaintsPage />} />
            <Route path="portal" element={<PortalDashboardPage />} />
            <Route
              element={
                <PermissionRoute anyOf={["portal.client_profile.view"]} />
              }
            >
              <Route
                path="portal/profile"
                element={<PortalClientProfilePage />}
              />
            </Route>
            <Route
              path="portal/training"
              element={<Navigate to="/knowledge?section=training" replace />}
            />
            <Route path="portal/tickets" element={<PortalTicketsPage />} />
            <Route
              path="portal/tickets/create"
              element={<PortalCreateTicketPage />}
            />
            <Route
              path="portal/tickets/:id"
              element={<PortalTicketDetailPage />}
            />
            <Route element={<PermissionRoute anyOf={["uat.portal.view"]} />}>
              <Route path="portal/uat" element={<PortalUatPage />} />
            </Route>
            <Route path="users/create" element={<CreateUserPage />} />
            <Route path="users/:id/edit" element={<EditUserPage />} />
            <Route path="profiles" element={<ProfilesPage />} />
            <Route path="profiles/:id/permissions" element={<ProfilesPage />} />
            <Route path="unauthorized" element={<UnauthorizedPage />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}
