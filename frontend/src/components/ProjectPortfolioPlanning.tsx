import { ChevronLeft, ChevronRight, Today } from "@mui/icons-material";
import { Box, Button, Chip, IconButton, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useState } from "react";
import { Link } from "react-router-dom";

type ScheduledProject = {
  id: number;
  name: string;
  project_number: string;
  planned_start_date: string | null;
  planned_end_date: string | null;
};
export type PortfolioProduct = { project_id: number; product_id: number; name: string };
const monthAt = (date: Date, offset = 0) => new Date(date.getFullYear(), date.getMonth() + offset, 1);
const dateKey = (date: Date) => date.toLocaleDateString("sv-SE");
const dateText = (date: Date, options: Intl.DateTimeFormatOptions) => date.toLocaleDateString(undefined, options);
const dayNumber = (key: string) => Date.parse(key) / 86_400_000;
const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export function ProjectPortfolioPlanning({ view, projects, products = [] }: {
  view: "calendar" | "timeline";
  projects: ScheduledProject[];
  products?: PortfolioProduct[];
}) {
  const [month, setMonth] = useState(() => monthAt(new Date()));
  const [product, setProduct] = useState("");
  const [calendarMode, setCalendarMode] = useState<"month" | "gantt">("month");
  const productTimeline = view === "timeline";
  const timeline = productTimeline || calendarMode === "gantt";
  const span = productTimeline ? 6 : 1;
  const months = Array.from({ length: span }, (_, index) => monthAt(month, index));
  const windowStart = dayNumber(dateKey(month));
  const windowEnd = dayNumber(dateKey(monthAt(month, span)));
  const projectById = new Map(projects.map((item) => [item.id, item]));
  const groups = new Map<number, { name: string; projects: ScheduledProject[] }>();
  for (const scope of products) {
    const item = projectById.get(scope.project_id);
    if (!item) continue;
    const group = groups.get(scope.product_id) ?? { name: scope.name, projects: [] };
    group.projects.push(item);
    groups.set(scope.product_id, group);
  }
  if (!productTimeline) groups.set(0, { name: "", projects });
  const events = new Map<string, { project: ScheduledProject; kind: string }[]>();
  if (!timeline) for (const project of projects) {
    for (const [date, kind] of [[project.planned_start_date, "Start"], [project.planned_end_date, "Due"]] as const) {
      if (date) events.set(date, [...(events.get(date) ?? []), { project, kind }]);
    }
  }
  const mondayOffset = (month.getDay() + 6) % 7;
  const days = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
  const today = dateKey(new Date());
  const productFilter = productTimeline && groups.has(Number(product)) ? product : "all";
  const visibleGroups = [...groups].filter(([id]) => productFilter === "all" || String(id) === productFilter).map(([id, group]) => ({
    id, name: group.name, projects: group.projects.flatMap((project) => {
      if (!project.planned_start_date || !project.planned_end_date) return [];
      const start = Math.max(windowStart, dayNumber(project.planned_start_date));
      const end = Math.min(windowEnd, dayNumber(project.planned_end_date) + 1);
      return end > start ? [{ project, start, end }] : [];
    }),
  })).filter((group) => group.projects.length);
  const percentage = (days: number) => `${100 * days / (windowEnd - windowStart)}%`;

  return <Stack gap={1.5}>
    <Stack direction="row" flexWrap="wrap" alignItems="center" gap={0.75}>
      {!productTimeline && <Stack direction="row" gap={0.5} aria-label="Calendar display" role="group" sx={{ mr: 1 }}>
        <Button size="small" aria-pressed={calendarMode === "month"} variant={calendarMode === "month" ? "contained" : "outlined"} onClick={() => setCalendarMode("month")}>Month</Button>
        <Button size="small" aria-pressed={calendarMode === "gantt"} variant={calendarMode === "gantt" ? "contained" : "outlined"} onClick={() => setCalendarMode("gantt")}>Gantt</Button>
      </Stack>}
      <IconButton size="small" aria-label={productTimeline ? "Previous six months" : "Previous month"} onClick={() => setMonth(monthAt(month, -span))}><ChevronLeft /></IconButton>
      <Typography component="h2" variant="subtitle1" fontWeight={750}>
        {dateText(month, { month: "long", year: "numeric" })}
        {productTimeline && ` – ${dateText(months[span - 1], { month: "long", year: "numeric" })}`}
      </Typography>
      <IconButton size="small" aria-label={productTimeline ? "Next six months" : "Next month"} onClick={() => setMonth(monthAt(month, span))}><ChevronRight /></IconButton>
      <Button size="small" startIcon={<Today />} onClick={() => setMonth(monthAt(new Date()))}>Today</Button>
      {productTimeline && <TextField select size="small" label="Product" value={productFilter}
        onChange={(event) => setProduct(event.target.value === "all" ? "" : event.target.value)}
        sx={{ minWidth: 180, ml: { sm: "auto" } }}>
        <MenuItem value="all">All products</MenuItem>
        {[...groups].map(([id, group]) => <MenuItem key={id} value={String(id)}>{group.name}</MenuItem>)}
      </TextField>}
      {!timeline && <Stack direction="row" gap={1} sx={{ ml: { sm: "auto" } }}>
        <Chip label="Start" size="small" color="primary" variant="outlined" />
        <Chip label="Due" size="small" color="warning" variant="outlined" />
      </Stack>}
    </Stack>
    <Paper variant="outlined" sx={{ overflowX: "auto", borderRadius: 2 }}>
      {timeline ? <Box sx={{ minWidth: 760, "--label-width": "250px" }}>
        <Box sx={{ display: "grid", gridTemplateColumns: "var(--label-width) minmax(0, 1fr)", bgcolor: "action.hover", borderBottom: 1, borderColor: "divider" }}>
          <Typography variant="subtitle2" sx={{ p: 1.5 }}>{productTimeline ? "Product / project" : "Project"}</Typography>
          <Box sx={{ display: "flex" }}>
            {productTimeline ? months.map((item, index) => <Typography key={dateKey(item)} variant="caption" sx={{
              width: percentage(dayNumber(dateKey(monthAt(month, index + 1))) - dayNumber(dateKey(item))),
              p: 1.5, boxSizing: "border-box", flexShrink: 0, borderLeft: 1, borderColor: "divider",
            }}>{dateText(item, { month: "short", year: "numeric" })}</Typography>) :
              Array.from({ length: days }, (_, index) => <Typography key={index} variant="caption"
                sx={{ width: percentage(1), flexShrink: 0, textAlign: "center", py: 1.5, borderLeft: 1,
                  borderColor: "divider", boxSizing: "border-box" }}>{index + 1}</Typography>)}
          </Box>
        </Box>
        {visibleGroups.map((group) => <Box key={group.id}>
          {productTimeline && <Typography variant="subtitle2" sx={{ px: 1.5, py: 0.75, bgcolor: "action.selected", borderBottom: 1, borderColor: "divider" }}>{group.name}</Typography>}
          {group.projects.map(({ project, start, end }) => <Box key={project.id} sx={{
            display: "grid", gridTemplateColumns: "var(--label-width) minmax(0, 1fr)", borderBottom: 1, borderColor: "divider",
          }}>
            <Button component={Link} to={`/projects/${project.id}/schedule`} size="small"
              sx={{ m: 0.5, textTransform: "none", justifyContent: "flex-start", textAlign: "start" }}>{project.project_number} · {project.name}</Button>
            <Box sx={{ position: "relative", minHeight: 38 }}>
              {(productTimeline ? months.map((item) => dayNumber(dateKey(item)) - windowStart)
                : Array.from({ length: days }, (_, index) => index)).map((offset) => <Box key={offset} sx={{
                position: "absolute", left: percentage(offset),
                insetBlock: 0, borderLeft: 1, borderColor: "divider",
              }} />)}
              <Box component={Link} to={`/projects/${project.id}/schedule`}
                aria-label={`${project.name}, ${project.planned_start_date} to ${project.planned_end_date}`}
                title={`${project.name} · ${project.planned_start_date} to ${project.planned_end_date}`}
                sx={{ position: "absolute", insetBlock: 9, left: percentage(start - windowStart),
                  width: percentage(end - start), minWidth: 3, borderRadius: 1, bgcolor: "primary.main",
                  "&:hover": { bgcolor: "primary.dark" } }} />
            </Box>
          </Box>)}
        </Box>)}
        {!visibleGroups.length && <Typography color="text.secondary" sx={{ p: 3 }}>
          {productTimeline ? "No product delivery windows overlap these months." : "No scheduled projects overlap this month."}
        </Typography>}
      </Box> : <Box sx={{ minWidth: 720, display: "grid", gridTemplateColumns: "repeat(7, minmax(0, 1fr))" }}>
        {weekdays.map((day) => <Typography key={day} variant="subtitle2" sx={{ p: 1, bgcolor: "action.hover" }}>{day}</Typography>)}
        {Array.from({ length: Math.ceil((mondayOffset + days) / 7) * 7 }, (_, index) => {
          const day = index - mondayOffset + 1;
          const date = dateKey(new Date(month.getFullYear(), month.getMonth(), day));
          const inMonth = day >= 1 && day <= days;
          return <Stack key={date} gap={0.5} sx={{
            minHeight: 86, minWidth: 0, p: 0.75, borderTop: 1, borderRight: 1, borderColor: "divider",
            bgcolor: !inMonth ? "action.hover" : date === today ? "action.selected" : undefined,
          }}>
            {inMonth && <>
              <Typography variant="caption" fontWeight={750} color={date === today ? "primary.main" : "text.secondary"}>{day}</Typography>
              {(events.get(date) ?? []).map(({ project, kind }) => <Button key={`${project.id}-${kind}`} component={Link}
                to={`/projects/${project.id}/schedule`} size="small" color={kind === "Start" ? "primary" : "warning"}
                sx={{ minWidth: 0, justifyContent: "flex-start", textTransform: "none", px: 0.5, lineHeight: 1.3 }}
                title={`${kind} · ${project.name}`}>
                <Typography variant="caption" noWrap>{kind} · {project.project_number} {project.name}</Typography>
              </Button>)}
            </>}
          </Stack>;
        })}
      </Box>}
    </Paper>
  </Stack>;
}
