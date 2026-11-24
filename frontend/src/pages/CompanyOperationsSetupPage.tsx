import {
  AccountTree,
  AdminPanelSettings,
  Assignment,
  Business,
  FactCheck,
  Groups,
  LockOutlined,
  SettingsSuggest,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Chip,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

type SetupCardProps = {
  icon: ReactNode;
  title: string;
  description: string;
  items: string[];
  path?: string;
  action: string;
  editable?: boolean;
};

function SetupCard({ icon, title, description, items, path, action, editable = true }: SetupCardProps) {
  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 3, height: "100%" }}>
      <Stack gap={1.5} height="100%">
        <Stack direction="row" alignItems="center" gap={1}>
          {icon}
          <Typography variant="h6" fontWeight={900}>{title}</Typography>
          <Chip
            size="small"
            sx={{ ml: "auto" }}
            icon={editable ? undefined : <LockOutlined />}
            color={editable ? "success" : "default"}
            variant="outlined"
            label={editable ? "Governed editor" : "System controlled"}
          />
        </Stack>
        <Typography variant="body2" color="text.secondary">{description}</Typography>
        <Stack direction="row" gap={0.75} flexWrap="wrap" useFlexGap>
          {items.map((item) => <Chip key={item} size="small" label={item} />)}
        </Stack>
        <Box sx={{ flex: 1 }} />
        {path ? <Button component={Link} to={path} variant="outlined" size="small">{action}</Button> : <Alert severity="info">{action}</Alert>}
      </Stack>
    </Paper>
  );
}

export function CompanyOperationsSetupPage() {
  const { hasPermission } = useAuth();
  const canManageHierarchy = hasPermission("client.manage") || hasPermission("customer_structure.policy.manage");
  const canManageProjects = hasPermission("project.manage");

  return (
    <Stack gap={2}>
      <Paper variant="outlined" sx={{ p: { xs: 2, md: 2.5 }, borderRadius: 3 }}>
        <Stack direction={{ xs: "column", md: "row" }} gap={1.5} alignItems={{ md: "center" }}>
          <SettingsSuggest color="primary" sx={{ fontSize: 34 }} />
          <Box>
            <Typography variant="h4" fontWeight={950}>Company operations setup</Typography>
            <Typography color="text.secondary">
              One administration map for collaboration master data. Mature editors remain the source of truth; system definitions stay read-only until governance approves configurability.
            </Typography>
          </Box>
          <Chip sx={{ ml: { md: "auto" } }} color="primary" label="Unified operations · revision 0292" />
        </Stack>
      </Paper>

      <Alert severity="warning">
        The local migration baseline still has 422 Clients awaiting approved Organization mapping. Use Customer hierarchy review before creating pilot Projects.
      </Alert>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "repeat(2,minmax(0,1fr))" }, gap: 1.5 }}>
        <SetupCard
          icon={<AccountTree color="primary" />}
          title="Company and customer hierarchy"
          description="Own the Account → Organization → Client → Branch structure and effective department-sharing policies."
          items={["Accounts", "Organizations", "Clients", "Branches", "Department policies"]}
          path="/customer-structure"
          action={canManageHierarchy ? "Manage customer structure" : "Review customer structure"}
        />
        <SetupCard
          icon={<Groups color="secondary" />}
          title="Departments, teams and people"
          description="Maintain departments, reporting structure, Support/Implementation teams, engineers and Project managers."
          items={["Departments", "Teams", "Team members", "Managers", "Skills"]}
          path="/crm"
          action="Open CRM master data"
        />
        <SetupCard
          icon={<AdminPanelSettings color="warning" />}
          title="Collaboration access governance"
          description="Assign primary/shared/temporary responsibility and named access profiles without exposing unrelated tickets or private implementation history."
          items={["PRIMARY OWNER", "SHARED OPERATOR", "VIEWER", "TEMPORARY OPERATOR", "INHERIT / EXTEND / OVERRIDE"]}
          path="/customer-structure"
          action="Manage scoped access policies"
        />
        <SetupCard
          icon={<Assignment color="info" />}
          title="Project and implementation setup"
          description="Create governed Projects and configure their phases, milestones, planned/unplanned tasks, teams and delivery ownership."
          items={["Projects", "Phases", "Milestones", "Tasks", "Assignment requests", "Blockers"]}
          path="/projects"
          action={canManageProjects ? "Manage Project portfolio" : "Review Project portfolio"}
        />
        <SetupCard
          icon={<FactCheck color="success" />}
          title="Support handover governance"
          description="Review the controlled readiness model used for evidence, Support acceptance, residual work and stabilization."
          items={["Readiness sections", "Required evidence", "Residual work", "Stabilization", "Support activation"]}
          path="/support-readiness"
          action="Open Support-readiness workspace"
        />
        <SetupCard
          icon={<Business color="disabled" />}
          title="System-controlled definitions"
          description="These definitions are intentionally versioned in code until owners approve editable catalogs, effective dates and migration rules."
          items={["Access profiles", "Task classifications", "Evidence types", "Handover template", "KPI dictionary"]}
          action="Read-only: configuration changes require a governed schema and approval."
          editable={false}
        />
      </Box>
    </Stack>
  );
}
