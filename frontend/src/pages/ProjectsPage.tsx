import { Add, CalendarMonthOutlined, ListAlt, Search, Timeline, ViewListOutlined } from "@mui/icons-material";
import { Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, InputAdornment, LinearProgress, MenuItem, Stack, Tab, Table, TableBody, TableCell, TableContainer, TableHead, TablePagination, TableRow, Tabs, TextField, Typography } from "@mui/material";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ProjectCreationWizard } from "../components/ProjectCreationWizard";
import { ProjectPortfolioPlanning, type PortfolioProduct } from "../components/ProjectPortfolioPlanning";

type Project = {
  id: number; project_number: string; name: string; status: string; health: string;
  progress_percent: number; client_id: number; project_manager_user_id: number;
  planned_start_date: string | null; planned_end_date: string | null;
  account_id: number; organization_id: number; owning_department_id: number; priority: string;
};
type Option = { id: number; name: string };
type Options = { clients: Option[]; managers: Option[]; accounts: Option[]; organizations: Option[]; departments: Option[] };
const label = (value: string) => value.toLowerCase().replaceAll("_", " ");
const backlogStatuses = new Set(["DRAFT", "AWAITING_IMPLEMENTATION_ACCEPTANCE", "INTAKE_RETURNED", "INTAKE_PROPOSED", "INTAKE_REJECTED"]);
export const projectMatches = (project: Project, search: string, status: string) =>
  (!status || project.status === status) && `${project.project_number} ${project.name}`.toLowerCase().includes(search.trim().toLowerCase());

export function ProjectsPage() {
  const { hasPermission, user } = useAuth();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const requestedView = params.get("view");
  const view = requestedView === "backlog" || requestedView === "calendar" || requestedView === "timeline" ? requestedView : "portfolio";
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [mine, setMine] = useState(false);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Project | null>(null);
  const projects = useQuery({
    queryKey: ["projects"], queryFn: async () => (await api.get<Project[]>("/projects")).data,
  });
  const options = useQuery({
    queryKey: ["project-options"], queryFn: async () => (await api.get<Options>("/projects/options")).data,
  });
  const products = useQuery({
    queryKey: ["project-portfolio-products"],
    queryFn: async () => (await api.get<PortfolioProduct[]>("/projects/portfolio-products")).data,
    enabled: view === "timeline",
  });
  const all = (projects.data ?? []).filter((project) => view !== "backlog" || backlogStatuses.has(project.status));
  const statuses = [...new Set(all.map((project) => project.status))].sort();
  const visible = all.filter((project) => projectMatches(project, search, statuses.includes(status) ? status : "")
    && (!mine || project.project_manager_user_id === user?.id));
  const pageIndex = Math.min(page, Math.max(0, Math.ceil(visible.length / pageSize) - 1));
  const names = new Map(options.data?.clients.map((item) => [item.id, item.name]));
  const managers = new Map(options.data?.managers.map((item) => [item.id, item.name]));
  return (
    <Stack gap={2} sx={{ width: "100%", minWidth: 0 }}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ sm: "center" }} gap={2}>
        <Box>
          <Typography variant="h4" component="h1" fontWeight={800}>Project Portfolio</Typography>
          <Typography color="text.secondary">Track project ownership, intake decisions, and delivery dates.</Typography>
        </Box>
        {hasPermission("project.create") && <Button variant="contained" startIcon={<Add />} onClick={() => setOpen(true)}>New project</Button>}
      </Stack>
      {projects.isError && <Alert severity="error">{apiErrorMessage(projects.error)}</Alert>}
      <Tabs value={view} variant="scrollable" scrollButtons="auto" aria-label="Project portfolio views"
        sx={{ borderBottom: 1, borderColor: "divider", "& .MuiTab-root": { minHeight: 46, textTransform: "none" } }}
        onChange={(_, next: string) => {
          setParams((current) => {
            const updated = new URLSearchParams(current);
            if (next === "portfolio") updated.delete("view");
            else updated.set("view", next);
            return updated;
          });
          setStatus(""); setPage(0);
        }}>
        <Tab value="portfolio" label="Portfolio" icon={<ViewListOutlined />} iconPosition="start" />
        <Tab value="backlog" label="Backlog" icon={<ListAlt />} iconPosition="start" />
        <Tab value="calendar" label="Calendar" icon={<CalendarMonthOutlined />} iconPosition="start" />
        <Tab value="timeline" label="Product Timeline" icon={<Timeline />} iconPosition="start" />
      </Tabs>
      <Box role="tabpanel" aria-label={view === "timeline" ? "Product timeline" : view} sx={{ minWidth: 0 }}>
        <Stack direction={{ xs: "column", md: "row" }} gap={1.5} sx={{ pb: 2 }}>
          <TextField size="small" fullWidth label="Search projects" placeholder="Project name or number" value={search}
            onChange={(event) => { setSearch(event.target.value); setPage(0); }}
            InputProps={{ startAdornment: <InputAdornment position="start"><Search fontSize="small" /></InputAdornment> }} />
          <TextField select size="small" label="Status" value={statuses.includes(status) ? status : "all"}
            onChange={(event) => { setStatus(event.target.value === "all" ? "" : event.target.value); setPage(0); }} sx={{ minWidth: { md: 220 } }}>
            <MenuItem value="all">All statuses</MenuItem>
            {statuses.map((item) => <MenuItem key={item} value={item} sx={{ textTransform: "capitalize" }}>{label(item)}</MenuItem>)}
          </TextField>
          <Button sx={{ flexShrink: 0 }} variant={mine ? "contained" : "outlined"} aria-pressed={mine}
            onClick={() => { setMine(!mine); setPage(0); }}>My projects</Button>
        </Stack>
        {projects.isPending && <LinearProgress />}
        {projects.isSuccess && !visible.length && (
          <Stack gap={1} alignItems="center" sx={{ p: 5, borderTop: 1, borderColor: "divider" }}>
            <Typography fontWeight={700}>{all.length ? "No projects match these filters" : view === "backlog" ? "No projects in the planning backlog" : "No projects in your portfolio"}</Typography>
            {!!all.length && <Button onClick={() => { setSearch(""); setStatus(""); setMine(false); setPage(0); }}>Clear filters</Button>}
          </Stack>
        )}
        {view === "timeline" && products.isFetching && <LinearProgress aria-label="Loading product timeline" />}
        {view === "timeline" && products.isError && <Alert severity="error" action={<Button onClick={() => products.refetch()}>Retry</Button>}>{apiErrorMessage(products.error)}</Alert>}
        {view === "timeline" && products.data && visible.length > 0 &&
          <ProjectPortfolioPlanning key={view} view={view} projects={visible} products={products.data} />}
        {view === "calendar" && projects.isSuccess &&
          <ProjectPortfolioPlanning key={view} view={view} projects={visible} />}
        {(view === "portfolio" || view === "backlog") && !!visible.length && <>
          <TableContainer>
            <Table size="small" aria-label={view === "backlog" ? "Project backlog" : "Project portfolio"}
              sx={{ display: "table", width: "100%", minWidth: 840, bgcolor: "background.paper" }}>
              <TableHead><TableRow sx={{ bgcolor: "action.hover" }}>
                <TableCell>Project</TableCell><TableCell>Status</TableCell><TableCell>Manager</TableCell>
                <TableCell>Due date</TableCell><TableCell>Progress</TableCell><TableCell align="right">Actions</TableCell>
              </TableRow></TableHead>
              <TableBody>{visible.slice(pageIndex * pageSize, (pageIndex + 1) * pageSize).map((project) => (
                <TableRow key={project.id} hover>
                  <TableCell component="th" scope="row" sx={{ py: 1.5 }}>
                    <Button onClick={() => setSelected(project)} sx={{ p: 0, textAlign: "start", fontWeight: 750, textTransform: "none", display: "block" }}>{project.name}</Button>
                    <Typography variant="caption" color="text.secondary">
                      {project.project_number}{names.has(project.client_id) ? ` · ${names.get(project.client_id)}` : ""}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" gap={0.5} flexWrap="wrap">
                      <Chip size="small" label={label(project.status)} sx={{ textTransform: "capitalize" }} />
                      {["AT_RISK", "CRITICAL"].includes(project.health) && <Chip size="small" color="error"
                        variant="outlined" label={label(project.health)} sx={{ textTransform: "capitalize" }} />}
                    </Stack>
                  </TableCell>
                  <TableCell>{managers.get(project.project_manager_user_id) ?? "—"}</TableCell>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>{project.planned_end_date ?? "—"}</TableCell>
                  <TableCell sx={{ minWidth: 95 }}>
                    <Typography variant="caption">{project.progress_percent}%</Typography>
                    <LinearProgress aria-label="Project progress" variant="determinate" value={project.progress_percent} />
                  </TableCell>
                  <TableCell align="right">
                    <Stack direction="row" gap={0.5} justifyContent="flex-end">
                      <Button component={Link} size="small" startIcon={<Timeline />} to={`/projects/${project.id}/schedule`}>Schedule</Button>
                      {hasPermission("implementation.task.view") && <Button component={Link} size="small"
                        to={`/projects/${project.id}/execution`}>Execution</Button>}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}</TableBody>
            </Table>
          </TableContainer>
          <TablePagination component="div" count={visible.length} page={pageIndex} rowsPerPage={pageSize}
            rowsPerPageOptions={[10, 25, 50]} onPageChange={(_, next) => setPage(next)}
            onRowsPerPageChange={(event) => { setPageSize(Number(event.target.value)); setPage(0); }} />
        </>}
      </Box>
      <Dialog open={Boolean(selected)} onClose={() => setSelected(null)} fullWidth maxWidth="sm">
        {selected && <>
          <DialogTitle>{selected.project_number} · {selected.name}</DialogTitle>
          <DialogContent dividers>
            <Stack gap={1.5}>
              {[
                ["Customer", [options.data?.accounts.find((x) => x.id === selected.account_id)?.name,
                  options.data?.organizations.find((x) => x.id === selected.organization_id)?.name,
                  names.get(selected.client_id)].filter(Boolean).join(" / ")],
                ["Owning department", options.data?.departments.find((x) => x.id === selected.owning_department_id)?.name],
                ["Project Manager", managers.get(selected.project_manager_user_id)],
                ["Status and health", `${label(selected.status)} · ${label(selected.health)}`],
                ["Priority", label(selected.priority)],
                ["Planned dates", `${selected.planned_start_date ?? "—"} to ${selected.planned_end_date ?? "—"}`],
              ].map(([heading, value]) => (
                <Box key={heading}><Typography variant="caption" color="text.secondary">{heading}</Typography>
                  <Typography variant="body2">{value || "—"}</Typography></Box>
              ))}
            </Stack>
          </DialogContent>
          <DialogActions><Button onClick={() => setSelected(null)}>Close</Button>
            <Button component={Link} to={`/projects/${selected.id}`}>Open project</Button>
            <Button component={Link} to={`/projects/${selected.id}/schedule`}>Gantt &amp; Schedule</Button>
          </DialogActions>
        </>}
      </Dialog>
      {open && <ProjectCreationWizard open onClose={() => setOpen(false)} onCreated={() => {
        setSearch(""); setStatus(""); setMine(false); setPage(0);
        void queryClient.invalidateQueries({ queryKey: ["projects"] });
        void queryClient.invalidateQueries({ queryKey: ["project-summary"] });
        void queryClient.invalidateQueries({ queryKey: ["project-portfolio-products"] });
      }} />}
    </Stack>
  );
}
