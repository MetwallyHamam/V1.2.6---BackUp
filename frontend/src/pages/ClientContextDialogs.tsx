import {
  Add,
  ContentCopy,
  Edit,
  Send,
  Visibility,
  VisibilityOff,
  WhatsApp,
} from "@mui/icons-material";
import {
  Alert,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { TicketSendActionsDialog } from "../components/TicketSendActions";

type Access = {
  id: number;
  branch_id: number | null;
  branch_name: string | null;
  access_type: string;
  label: string;
  server_or_address: string | null;
  username: string | null;
  notes: string | null;
  has_password: boolean;
  is_active: boolean;
};
type Branch = { id: number; name: string; is_active: boolean };
type Contact = {
  id: number;
  full_name: string;
  phone_number?: string | null;
  email?: string | null;
  job_title?: string | null;
  contact_role?: string | null;
  is_active: boolean;
};
const emptyAccess = {
  id: 0,
  branch_id: null,
  branch_name: null,
  access_type: "OTHER",
  label: "",
  server_or_address: "",
  username: "",
  notes: "",
  has_password: false,
  is_active: true,
};
function whatsapp(phone: string) {
  let digits = phone.replace(/\D/g, "");
  if (digits.startsWith("00")) digits = digits.slice(2);
  if (!digits.startsWith("20"))
    digits = digits.startsWith("0") ? `20${digits.slice(1)}` : `20${digits}`;
  window.open(`https://wa.me/${digits}`, "_blank", "noopener,noreferrer");
}

export function ClientAccessManagerDialog({
  clientId,
  open,
  onClose,
  editMode,
}: {
  clientId: number | null;
  open: boolean;
  onClose: () => void;
  editMode: boolean;
}) {
  const { hasPermission } = useAuth(),
    cache = useQueryClient(),
    [editing, setEditing] = useState<Access | null>(null),
    [password, setPassword] = useState(""),
    [revealed, setRevealed] = useState<Record<number, string>>({}),
    [error, setError] = useState("");
  const records = useQuery({
    queryKey: ["client-access", String(clientId)],
    enabled: open && !!clientId && hasPermission("client_access.view"),
    queryFn: async () =>
      (await api.get<Access[]>(`/clients/${clientId}/access`)).data,
  });
  const branches = useQuery({
    queryKey: ["client-branches", String(clientId)],
    enabled: open && !!clientId && hasPermission("client_access.view"),
    queryFn: async () =>
      (await api.get<Branch[]>(`/clients/${clientId}/branches`)).data,
  });
  useEffect(() => {
    if (!open) {
      setEditing(null);
      setPassword("");
      setRevealed({});
      setError("");
    }
  }, [open]);
  const save = useMutation({
    mutationFn: async () => {
      if (!clientId || !editing) return;
      const payload = {
        branch_id: editing.branch_id,
        access_type: editing.access_type,
        label: editing.label,
        server_or_address: editing.server_or_address || null,
        username: editing.username || null,
        notes: editing.notes || null,
        is_active: editing.is_active,
        ...(password ? { password } : {}),
      };
      return editing.id
        ? api.patch(`/clients/${clientId}/access/${editing.id}`, payload)
        : api.post(`/clients/${clientId}/access`, payload);
    },
    onSuccess: async () => {
      setEditing(null);
      setPassword("");
      await cache.invalidateQueries({
        queryKey: ["client-access", String(clientId)],
      });
    },
    onError: (e) =>
      setError(apiErrorMessage(e, "Access record could not be saved.")),
  });
  async function reveal(item: Access) {
    const result = (
      await api.post<{ password: string }>(
        `/clients/${clientId}/access/${item.id}/reveal`,
        {},
      )
    ).data;
    setRevealed((x) => ({ ...x, [item.id]: result.password }));
  }
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="lg">
      <DialogTitle>
        {editMode ? "Edit client access" : "Client access"}
      </DialogTitle>
      <DialogContent dividers>
        {error && <Alert severity="error">{error}</Alert>}
        {records.isError && (
          <Alert severity="error">Client access could not be loaded.</Alert>
        )}
        {editMode && hasPermission("client_access.manage") && (
          <Button
            startIcon={<Add />}
            onClick={() => setEditing({ ...emptyAccess })}
            sx={{ mb: 1 }}
          >
            Add access record
          </Button>
        )}
        <Paper variant="outlined" sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                {[
                  "Type",
                  "Client / branch",
                  "Label / address",
                  "Username",
                  "Password",
                  "Notes",
                  "Status",
                  "Actions",
                ].map((x) => (
                  <TableCell key={x}>{x}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {records.data?.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.access_type}</TableCell>
                  <TableCell>{item.branch_name ?? "Entire client"}</TableCell>
                  <TableCell>
                    {item.label}
                    <Typography variant="caption" display="block" dir="ltr">
                      {item.server_or_address || "—"}
                    </Typography>
                  </TableCell>
                  <TableCell dir="ltr">{item.username || "—"}</TableCell>
                  <TableCell dir="ltr">
                    {revealed[item.id] ??
                      (item.has_password ? "••••••••" : "—")}
                    {item.has_password &&
                      hasPermission("client_access.reveal") && (
                        <>
                          <Tooltip title="Reveal">
                            <IconButton
                              size="small"
                              onClick={() =>
                                revealed[item.id]
                                  ? setRevealed((x) => {
                                      const n = { ...x };
                                      delete n[item.id];
                                      return n;
                                    })
                                  : reveal(item)
                              }
                            >
                              {revealed[item.id] ? (
                                <VisibilityOff fontSize="inherit" />
                              ) : (
                                <Visibility fontSize="inherit" />
                              )}
                            </IconButton>
                          </Tooltip>
                          {revealed[item.id] && (
                            <IconButton
                              size="small"
                              onClick={() =>
                                navigator.clipboard.writeText(revealed[item.id])
                              }
                            >
                              <ContentCopy fontSize="inherit" />
                            </IconButton>
                          )}
                        </>
                      )}
                  </TableCell>
                  <TableCell>{item.notes || "—"}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={item.is_active ? "Active" : "Inactive"}
                      color={item.is_active ? "success" : "default"}
                    />
                  </TableCell>
                  <TableCell>
                    {editMode && hasPermission("client_access.manage") && (
                      <Button
                        size="small"
                        startIcon={<Edit />}
                        onClick={() => setEditing({ ...item })}
                      >
                        Edit
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
        {editing && (
          <Stack spacing={1.5} mt={2}>
            <Typography fontWeight={800}>
              {editing.id ? "Edit access record" : "New access record"}
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
              <TextField
                select
                label="Client or branch access"
                value={editing.branch_id ?? ""}
                onChange={(e) =>
                  setEditing({
                    ...editing,
                    branch_id: e.target.value ? Number(e.target.value) : null,
                  })
                }
                sx={{ minWidth: 210 }}
              >
                <MenuItem value="">Entire client</MenuItem>
                {branches.data?.filter((branch) => branch.is_active).map((branch) => (
                  <MenuItem key={branch.id} value={branch.id}>
                    {branch.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                label="Type"
                value={editing.access_type}
                onChange={(e) =>
                  setEditing({ ...editing, access_type: e.target.value })
                }
                sx={{ minWidth: 180 }}
              >
                {["SERVER", "VPN", "ANYDESK", "SYSTEM_ADMIN", "OTHER"].map(
                  (x) => (
                    <MenuItem key={x} value={x}>
                      {x.replaceAll("_", " ")}
                    </MenuItem>
                  ),
                )}
              </TextField>
              <TextField
                required
                fullWidth
                label="Label"
                value={editing.label}
                onChange={(e) =>
                  setEditing({ ...editing, label: e.target.value })
                }
              />
            </Stack>
            <TextField
              label="Server or address"
              value={editing.server_or_address ?? ""}
              onChange={(e) =>
                setEditing({ ...editing, server_or_address: e.target.value })
              }
            />
            <TextField
              label="Username"
              value={editing.username ?? ""}
              onChange={(e) =>
                setEditing({ ...editing, username: e.target.value })
              }
            />
            <TextField
              type="password"
              label={
                editing.has_password
                  ? "New password (leave empty to keep current)"
                  : "Password"
              }
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <TextField
              multiline
              minRows={2}
              label="Notes"
              value={editing.notes ?? ""}
              onChange={(e) =>
                setEditing({ ...editing, notes: e.target.value })
              }
            />
            <Stack direction="row" gap={1}>
              <Button onClick={() => setEditing(null)}>Cancel edit</Button>
              <Button
                variant="contained"
                disabled={editing.label.trim().length < 2 || save.isPending}
                onClick={() => save.mutate()}
              >
                Save access
              </Button>
            </Stack>
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}

export function ClientContactsDialog({
  clientId,
  ticketId,
  open,
  onClose,
}: {
  clientId: number | null;
  ticketId: number | null;
  open: boolean;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState<Contact | null>(null),
    [sendOpen, setSendOpen] = useState(false);
  const contacts = useQuery({
    queryKey: ["client-contacts", clientId],
    enabled: open && !!clientId,
    queryFn: async () =>
      (
        await api.get<Contact[]>("/contacts", {
          params: { client_id: clientId },
        })
      ).data,
  });
  useEffect(() => {
    if (!open) {
      setSelected(null);
      setSendOpen(false);
    }
  }, [open]);
  return (
    <>
      <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
        <DialogTitle>Client contacts</DialogTitle>
        <DialogContent dividers>
          {contacts.isError && (
            <Alert severity="error">Client contacts could not be loaded.</Alert>
          )}
          <Stack spacing={1}>
            {contacts.data?.map((contact) => (
              <Paper key={contact.id} variant="outlined" sx={{ p: 1.5 }}>
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  gap={1}
                  alignItems={{ sm: "center" }}
                >
                  <Stack flex={1}>
                    <Typography fontWeight={800}>
                      {contact.full_name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {[
                        contact.job_title,
                        contact.contact_role,
                        contact.phone_number,
                        contact.email,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </Typography>
                  </Stack>
                  <Chip
                    size="small"
                    label={contact.is_active ? "Active" : "Inactive"}
                  />
                  {contact.phone_number && (
                    <Button
                      startIcon={<WhatsApp />}
                      onClick={() => whatsapp(contact.phone_number!)}
                    >
                      WhatsApp
                    </Button>
                  )}
                  <Button
                    startIcon={<Send />}
                    disabled={!ticketId}
                    onClick={() => {
                      setSelected(contact);
                      setSendOpen(true);
                    }}
                  >
                    Rating / live tracking
                  </Button>
                </Stack>
              </Paper>
            ))}
          </Stack>
          {contacts.data?.length === 0 && (
            <Alert severity="info">No client contacts are available.</Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Close</Button>
        </DialogActions>
      </Dialog>
      <TicketSendActionsDialog
        ticketId={ticketId}
        contactId={selected?.id}
        open={sendOpen}
        onClose={() => setSendOpen(false)}
      />
    </>
  );
}
