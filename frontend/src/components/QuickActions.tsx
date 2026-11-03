import {
  Add,
  Assistant,
  ConfirmationNumber,
  Description,
  DirectionsCar,
  Close,
  Work,
  HomeWork,
  Groups,
  Science,
  AccessTime,
  RestartAlt,
} from "@mui/icons-material";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Fab,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  TextField,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, ReactNode, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { InternalOperationsPage } from "../pages/InternalOperationsPage";
import { CreateTicketPage } from "../pages/CreateTicketPage";
import { PreTicketsPage } from "../pages/PreTicketsPage";

type ClientOption = { id: number; code: string; name: string };
type OperationType = {
  id: number;
  code: string;
  name: string;
  is_active: boolean;
};
type QuickActionPreferences = {
  hidden: string[];
  position?: { x: number; y: number };
};
const defaultPreferences: QuickActionPreferences = { hidden: [] };
const buttonSize = 56;
const buttonMargin = 8;
function clamp(value: number) { return Math.min(1, Math.max(0, value)); }

export function QuickActions() {
  const theme = useTheme();
  const mobile = useMediaQuery(theme.breakpoints.down("md"));
  const navigate = useNavigate();
  const cache = useQueryClient();
  const { hasPermission, user } = useAuth();
  const [visitOpen, setVisitOpen] = useState(false);
  const [client, setClient] = useState<ClientOption | null>(null);
  const [error, setError] = useState("");
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const [settingsAnchor, setSettingsAnchor] = useState<HTMLElement | null>(null);
  const [preferences, setPreferences] = useState<QuickActionPreferences>(defaultPreferences);
  const [draftPosition, setDraftPosition] = useState<{ x: number; y: number } | null>(null);
  const [viewport, setViewport] = useState({ width: window.innerWidth, height: window.innerHeight });
  const drag = useRef<{ pointerId: number; startX: number; startY: number; left: number; top: number; moved: boolean } | null>(null);
  const suppressClick = useRef(false);
  const [dialogAction, setDialogAction] = useState<
    "ticket" | "pre-ticket" | null
  >(null);
  const [ticketFormKey, setTicketFormKey] = useState(0);
  const [operationType, setOperationType] = useState<string | null>(null);
  const preferenceKey = user ? `supporthub-quick-actions-${user.id}` : null;
  useEffect(() => {
    if (!preferenceKey) { setPreferences(defaultPreferences); setDraftPosition(null); return; }
    try {
      const stored = JSON.parse(window.localStorage.getItem(preferenceKey) ?? "{}") as Partial<QuickActionPreferences>;
      setPreferences({
        hidden: Array.isArray(stored.hidden) ? stored.hidden.filter((item): item is string => typeof item === "string") : [],
        position: stored.position && Number.isFinite(stored.position.x) && Number.isFinite(stored.position.y)
          ? { x: clamp(stored.position.x), y: clamp(stored.position.y) } : undefined,
      });
    } catch { setPreferences(defaultPreferences); }
    setDraftPosition(null);
  }, [preferenceKey]);
  useEffect(() => {
    const resize = () => setViewport({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);
  const savePreferences = (next: QuickActionPreferences) => {
    setPreferences(next);
    if (preferenceKey) window.localStorage.setItem(preferenceKey, JSON.stringify(next));
  };
  const position = draftPosition ?? preferences.position;
  const availableWidth = Math.max(0, viewport.width - buttonSize - buttonMargin * 2);
  const availableHeight = Math.max(0, viewport.height - buttonSize - buttonMargin * 2);
  const left = position ? buttonMargin + position.x * availableWidth : viewport.width - buttonSize - (mobile ? 18 : 26);
  const top = position ? buttonMargin + position.y * availableHeight : viewport.height - buttonSize - (mobile ? 18 : 26);
  const clients = useQuery({
    queryKey: ["field-visit-client-options"],
    queryFn: async () =>
      (await api.get<ClientOption[]>("/visits/field-request/clients")).data,
    enabled: visitOpen,
  });
  const operationTypes = useQuery({
    queryKey: ["quick-operation-types"],
    enabled:
      hasPermission("internal_operation.create") ||
      hasPermission("internal_operation.manage"),
    queryFn: async () =>
      (await api.get<OperationType[]>("/internal-operations/types")).data,
  });
  const createVisit = useMutation({
    mutationFn: async (form: HTMLFormElement) => {
      const values = new FormData(form);
      const from = new Date(String(values.get("date_from")));
      const to = new Date(String(values.get("date_to")));
      if (
        !client ||
        Number.isNaN(from.getTime()) ||
        Number.isNaN(to.getTime()) ||
        to <= from
      )
        throw new Error("Date to must be later than Date from.");
      return api.post("/visits/field-request", {
        client_id: client.id,
        starts_at: from.toISOString(),
        ends_at: to.toISOString(),
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        notes: String(values.get("notes") ?? "").trim() || null,
      });
    },
    onSuccess: async () => {
      setVisitOpen(false);
      setClient(null);
      setError("");
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["visit-planner"] }),
        cache.invalidateQueries({ queryKey: ["my-field-visits"] }),
      ]);
      navigate("/field-visits");
    },
    onError: (reason) =>
      setError(
        reason instanceof Error && !("response" in reason)
          ? reason.message
          : apiErrorMessage(reason),
      ),
  });
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    createVisit.mutate(event.currentTarget);
  };
  const actions = [
    hasPermission("ticket.create")
      ? {
          key: "ticket",
          name: "Create ticket",
          icon: <ConfirmationNumber />,
          color: "#1976d2",
          run: () => setDialogAction("ticket"),
        }
      : null,
    hasPermission("ticket.pre_ticket.create")
      ? {
          key: "pre-ticket",
          name: "Create Pre-Ticket",
          icon: <Description />,
          color: "#7b1fa2",
          run: () => setDialogAction("pre-ticket"),
        }
      : null,
    hasPermission("visit.field.create.self")
      ? {
          key: "field-visit",
          name: "Request field visit",
          icon: <DirectionsCar />,
          color: "#ef6c00",
          run: () => setVisitOpen(true),
        }
      : null,
    [
      "support_assistant.queue.view",
      "support_assistant.mine.view",
      "support_assistant.backlog.view",
      "support_assistant.sla_risk.view",
      "support_assistant.follow_up.view",
      "support_assistant.pre_ticket.view",
      "support_assistant.ops.view",
    ].some(hasPermission)
      ? {
          key: "assistant",
          name: "Support Assistant",
          icon: <Assistant />,
          color: "#00897b",
          run: () => navigate("/support-workspace"),
        }
      : null,
    ...(operationTypes.data ?? [])
      .filter((type) => type.is_active !== false)
      .map((type) => ({
        key: `operation:${type.code}`,
        name: `Create ${type.name}`,
        icon:
          type.code === "OUTDOOR_VISIT" ? (
            <DirectionsCar />
          ) : type.code === "WORK_FROM_HOME" ? (
            <HomeWork />
          ) : type.code === "MEETING" ? (
            <Groups />
          ) : type.code === "DEMO" ? (
            <Science />
          ) : type.code === "AFTER_SHIFT" ? (
            <AccessTime />
          ) : (
            <Work />
          ),
        color:
          type.code === "OUTDOOR_VISIT"
            ? "#f4511e"
            : type.code === "WORK_FROM_HOME"
              ? "#00897b"
              : type.code === "MEETING"
                ? "#5e35b1"
                : type.code === "DEMO"
                  ? "#c2185b"
                  : type.code === "AFTER_SHIFT"
                    ? "#3949ab"
                    : "#546e7a",
        run: () => setOperationType(type.code),
      })),
  ]
    .filter(Boolean)
    .sort(
      (a, b) =>
        (b?.name.length ?? 0) - (a?.name.length ?? 0) ||
        (a?.name ?? "").localeCompare(b?.name ?? ""),
  ) as Array<{
    key: string;
    name: string;
    icon: ReactNode;
    color: string;
    run: () => void;
  }>;
  if (!actions.length) return null;
  const visibleActions = actions.filter((action) => !preferences.hidden.includes(action.key));

  return (
    <>
      <Box
        sx={{
          position: "fixed",
          zIndex: theme.zIndex.speedDial,
          left,
          top,
          touchAction: "none",
        }}
      >
        <Fab
          color="primary"
          aria-label="Quick actions"
          title="Drag to move; right-click to customize"
          onContextMenu={(event) => {
            event.preventDefault();
            setAnchor(null);
            setSettingsAnchor(event.currentTarget);
          }}
          onPointerDown={(event) => {
            if (event.button !== 0) return;
            drag.current = { pointerId: event.pointerId, startX: event.clientX, startY: event.clientY, left, top, moved: false };
            event.currentTarget.setPointerCapture(event.pointerId);
          }}
          onPointerMove={(event) => {
            const current = drag.current;
            if (!current || current.pointerId !== event.pointerId) return;
            const dx = event.clientX - current.startX;
            const dy = event.clientY - current.startY;
            if (!current.moved && Math.hypot(dx, dy) < 6) return;
            current.moved = true;
            setDraftPosition({
              x: clamp((current.left + dx - buttonMargin) / Math.max(availableWidth, 1)),
              y: clamp((current.top + dy - buttonMargin) / Math.max(availableHeight, 1)),
            });
          }}
          onPointerUp={(event) => {
            const current = drag.current;
            if (!current || current.pointerId !== event.pointerId) return;
            if (current.moved) {
              const next = {
                x: clamp((current.left + event.clientX - current.startX - buttonMargin) / Math.max(availableWidth, 1)),
                y: clamp((current.top + event.clientY - current.startY - buttonMargin) / Math.max(availableHeight, 1)),
              };
              savePreferences({ ...preferences, position: next });
              setDraftPosition(null);
              suppressClick.current = true;
            }
            drag.current = null;
          }}
          onPointerCancel={() => { drag.current = null; setDraftPosition(null); }}
          onClick={(event) => {
            if (suppressClick.current) { suppressClick.current = false; return; }
            setSettingsAnchor(null);
            setAnchor(event.currentTarget);
          }}
        >
          <Add />
        </Fab>
        <Menu
          anchorEl={anchor}
          open={Boolean(anchor)}
          onClose={() => setAnchor(null)}
          anchorOrigin={{ vertical: "top", horizontal: "right" }}
          transformOrigin={{ vertical: "bottom", horizontal: "right" }}
        >
          {visibleActions.length === 0 && <MenuItem disabled>No actions selected. Right-click + to customize.</MenuItem>}
          {visibleActions.map((action) => (
            <MenuItem
              key={action.key}
              onClick={() => {
                setAnchor(null);
                action.run();
              }}
            >
              <ListItemIcon sx={{ color: action.color }}>
                {action.icon}
              </ListItemIcon>
              <ListItemText>{action.name}</ListItemText>
            </MenuItem>
          ))}
        </Menu>
        <Menu
          anchorEl={settingsAnchor}
          open={Boolean(settingsAnchor)}
          onClose={() => setSettingsAnchor(null)}
          anchorOrigin={{ vertical: "top", horizontal: "right" }}
          transformOrigin={{ vertical: "bottom", horizontal: "right" }}
        >
          <MenuItem disabled>Show quick actions</MenuItem>
          {actions.map((action) => (
            <MenuItem key={action.key} onClick={() => savePreferences({
              ...preferences,
              hidden: preferences.hidden.includes(action.key)
                ? preferences.hidden.filter((key) => key !== action.key)
                : [...preferences.hidden, action.key],
            })}>
              <Checkbox size="small" checked={!preferences.hidden.includes(action.key)} />
              <ListItemText>{action.name}</ListItemText>
            </MenuItem>
          ))}
          <MenuItem onClick={() => { savePreferences({ ...preferences, position: undefined }); setSettingsAnchor(null); }}>
            <ListItemIcon><RestartAlt /></ListItemIcon>
            <ListItemText>Reset button position</ListItemText>
          </MenuItem>
        </Menu>
      </Box>
      <Dialog
        open={visitOpen}
        onClose={() => setVisitOpen(false)}
        fullWidth
        maxWidth="sm"
        fullScreen={mobile}
      >
        <Box component="form" onSubmit={submit}>
          <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <DirectionsCar color="primary" /> Request field visit
            <Box flex={1} />
            <Button aria-label="Close" onClick={() => setVisitOpen(false)}>
              <Close />
            </Button>
          </DialogTitle>
          <DialogContent>
            <Alert severity="info" sx={{ mb: 2 }}>
              The visit will be assigned to {user?.full_name} and submitted for
              team-leader approval.
            </Alert>
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}
            <Autocomplete
              options={clients.data ?? []}
              loading={clients.isFetching}
              value={client}
              onChange={(_, value) => setClient(value)}
              getOptionLabel={(item) => `${item.code} — ${item.name}`}
              renderInput={(params) => (
                <TextField {...params} required label="Client" />
              )}
            />
            <TextField
              required
              fullWidth
              type="datetime-local"
              name="date_from"
              label="Date from"
              margin="normal"
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              required
              fullWidth
              type="datetime-local"
              name="date_to"
              label="Date to"
              margin="normal"
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              fullWidth
              multiline
              minRows={3}
              name="notes"
              label="Visit purpose / notes"
              margin="normal"
              inputProps={{ maxLength: 2000 }}
            />
          </DialogContent>
          <DialogActions sx={{ p: 2 }}>
            <Button onClick={() => setVisitOpen(false)}>Cancel</Button>
            <Button
              type="submit"
              variant="contained"
              disabled={!client || createVisit.isPending}
            >
              {createVisit.isPending ? "Submitting…" : "Submit for approval"}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={dialogAction === "ticket"}
        onClose={() => setDialogAction(null)}
        fullScreen={mobile}
        fullWidth
        maxWidth="xl"
      >
        <DialogContent dividers sx={{ p: { xs: 1, md: 2 } }}>
          <CreateTicketPage
            key={ticketFormKey}
            onCreated={(mode) => {
              if (mode === "close") setDialogAction(null);
              else setTicketFormKey((value) => value + 1);
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogAction(null)}>Close</Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={dialogAction === "pre-ticket"}
        onClose={() => setDialogAction(null)}
        fullScreen={mobile}
        fullWidth
        maxWidth="xl"
      >
        <DialogContent dividers sx={{ p: { xs: 1, md: 2 } }}>
          <PreTicketsPage />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogAction(null)}>Close</Button>
        </DialogActions>
      </Dialog>
      {operationType && (
        <InternalOperationsPage
          key={operationType}
          dialogOnly
          initialCreateType={operationType}
          onClose={() => setOperationType(null)}
        />
      )}
    </>
  );
}
