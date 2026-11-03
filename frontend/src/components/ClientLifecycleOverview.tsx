import { AccountTree, BugReport, CloudDone, FactCheck, PublishedWithChanges } from "@mui/icons-material";
import { Card, CardActionArea, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Grid, List, ListItemButton, ListItemText, Button, Stack, Typography } from "@mui/material";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

export type LifecycleRecord = { id: number; number: string; title: string; status: string; route: string };
export type LifecycleArea = { count: number; active: number; records: LifecycleRecord[] };
export type ClientLifecycle = Record<"uat" | "deployments" | "incidents" | "changes" | "problems", LifecycleArea>;

const definitions = [
  ["uat", "UAT", <FactCheck color="primary" />],
  ["deployments", "Deployments", <CloudDone color="success" />],
  ["incidents", "Incidents", <BugReport color="error" />],
  ["changes", "Change Requests", <PublishedWithChanges color="info" />],
  ["problems", "Problems", <AccountTree color="warning" />],
] as const;

export function ClientLifecycleOverview({ lifecycle }: { lifecycle: ClientLifecycle }) {
  const navigate = useNavigate();
  const [selected, setSelected] = useState<(typeof definitions)[number][0] | null>(null);
  const current = selected ? lifecycle[selected] : null;
  const title = definitions.find(([key]) => key === selected)?.[1];
  return <>
    <Stack spacing={1.5}>
      <Typography variant="h5" fontWeight={900}>Service delivery lifecycle</Typography>
      <Typography color="text.secondary">UAT, deployment, support incidents, controlled changes, and underlying problems for this client.</Typography>
      <Grid container spacing={2}>
        {definitions.map(([key, label, icon]) => {
          const area = lifecycle[key];
          return <Grid key={key} size={{ xs: 12, sm: 6, lg: key === "problems" ? 4 : 2 }}>
            <Card variant="outlined" sx={{ height: "100%" }}>
              <CardActionArea sx={{ height: "100%" }} onClick={() => setSelected(key)}>
                <CardContent>{icon}<Typography variant="h4" fontWeight={900}>{area.count}</Typography><Typography fontWeight={700}>{label}</Typography><Chip size="small" sx={{ mt: 1 }} color={area.active ? "warning" : "success"} label={`${area.active} active`} /></CardContent>
              </CardActionArea>
            </Card>
          </Grid>;
        })}
      </Grid>
    </Stack>
    <Dialog open={Boolean(selected)} onClose={() => setSelected(null)} fullWidth maxWidth="md">
      <DialogTitle>{title} · {current?.count ?? 0}</DialogTitle>
      <DialogContent>
        {!current?.records.length && <Typography color="text.secondary">No records are available.</Typography>}
        <List>{current?.records.map((record) => <ListItemButton key={`${selected}-${record.id}`} onClick={() => { setSelected(null); navigate(record.route); }}><ListItemText primary={`${record.number} · ${record.title}`} secondary={record.status.replaceAll("_", " ")} /></ListItemButton>)}</List>
        {(current?.count ?? 0) > 10 && <Typography variant="caption" color="text.secondary">Showing the latest 10 records.</Typography>}
      </DialogContent>
      <DialogActions><Button onClick={() => setSelected(null)}>Close</Button></DialogActions>
    </Dialog>
  </>;
}
