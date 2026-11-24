import {
  Add,
  ContentCopy,
  Edit,
  Visibility,
  VisibilityOff,
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
import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";

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
const TYPES = ["SERVER", "VPN", "ANYDESK", "SYSTEM_ADMIN", "OTHER"];

export function ClientAccessVault({ clientId }: { clientId: string }) {
  const { t } = useTranslation();
  const { hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const editMode = searchParams.get("access_mode") === "edit";
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Access | null>(null);
  const [branchId, setBranchId] = useState<number | "">("");
  const [addingBranch, setAddingBranch] = useState(false);
  const [newBranchName, setNewBranchName] = useState("");
  const [revealed, setRevealed] = useState<Record<number, string>>({});
  const records = useQuery({
    queryKey: ["client-access", clientId],
    queryFn: async () =>
      (await api.get<Access[]>(`/clients/${clientId}/access`)).data,
    enabled: hasPermission("client_access.view"),
  });
  const branches = useQuery({
    queryKey: ["client-branches", clientId],
    queryFn: async () =>
      (await api.get<Branch[]>(`/clients/${clientId}/branches`)).data,
    enabled: hasPermission("client_access.view"),
  });
  const createBranch = useMutation({
    mutationFn: async () =>
      (
        await api.post<Branch>(`/clients/${clientId}/branches`, {
          name: newBranchName.trim(),
        })
      ).data,
    onSuccess: async (branch) => {
      setBranchId(branch.id);
      setNewBranchName("");
      setAddingBranch(false);
      await queryClient.invalidateQueries({
        queryKey: ["client-branches", clientId],
      });
    },
  });
  useEffect(() => {
    if (editMode && !hasPermission("client_access.manage")) {
      const next = new URLSearchParams(searchParams);
      next.delete("access_mode");
      setSearchParams(next, { replace: true });
    }
  }, [editMode, hasPermission, searchParams, setSearchParams]);
  const save = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      editing
        ? api.patch(`/clients/${clientId}/access/${editing.id}`, payload)
        : api.post(`/clients/${clientId}/access`, payload),
    onSuccess: async () => {
      setOpen(false);
      setEditing(null);
      setBranchId("");
      setAddingBranch(false);
      await queryClient.invalidateQueries({
        queryKey: ["client-access", clientId],
      });
    },
  });
  async function secret(item: Access) {
    if (revealed[item.id] !== undefined) return revealed[item.id];
    const response = await api.post<{ password: string }>(
      `/clients/${clientId}/access/${item.id}/reveal`,
      {},
    );
    setRevealed((current) => ({
      ...current,
      [item.id]: response.data.password,
    }));
    return response.data.password;
  }
  async function copy(value: string | null) {
    if (value) await navigator.clipboard.writeText(value);
  }
  async function copySecret(item: Access) {
    const value = await secret(item);
    if (value !== null) await navigator.clipboard.writeText(value);
  }
  function hide(id: number) {
    setRevealed((current) => {
      const next = { ...current };
      delete next[id];
      return next;
    });
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    const payload: Record<string, unknown> = {
      branch_id: branchId || null,
      access_type: values.access_type,
      label: String(values.label).trim(),
      server_or_address: String(values.server_or_address).trim() || null,
      username: String(values.username).trim() || null,
      notes: String(values.notes).trim() || null,
      is_active: values.is_active === "true",
    };
    const password = String(values.password);
    if (!editing || password) payload.password = password || null;
    save.mutate(payload);
  }
  if (!hasPermission("client_access.view")) return null;
  return (
    <Paper id="client-access" sx={{ p: 3, scrollMarginTop: 96 }}>
      <Stack direction="row" alignItems="center" mb={2}>
        <div style={{ flexGrow: 1 }}>
          <Typography variant="h5">{t("clientAccess.vaultTitle")}</Typography>
          <Typography variant="body2" color="text.secondary">
            {t("clientAccess.vaultHelp")}
          </Typography>
        </div>
        {hasPermission("client_access.manage") && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setEditing(null);
              setBranchId("");
              setAddingBranch(false);
              setOpen(true);
            }}
          >
            {t("clientAccess.add")}
          </Button>
        )}
      </Stack>
      {editMode && hasPermission("client_access.manage") && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Access editing mode is active. Use Edit beside an existing access
          record, or Add access to create one.
        </Alert>
      )}
      {records.isError && (
        <Alert severity="error">{t("clientAccess.loadFailed")}</Alert>
      )}
      {records.data?.length === 0 && (
        <Alert severity="info">{t("clientAccess.empty")}</Alert>
      )}
      {!!records.data?.length && (
        <Table>
          <TableHead>
            <TableRow>
              {(
                [
                  "type",
                  "branch",
                  "label",
                  "username",
                  "password",
                  "status",
                  "actions",
                ] as const
              ).map((column) => (
                <TableCell
                  key={column}
                  align={column === "actions" ? "right" : undefined}
                >
                  {t(`clientAccess.columns.${column}`)}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {records.data.map((item) => (
              <TableRow key={item.id}>
                <TableCell>
                  {t(`clientAccess.types.${item.access_type}`, {
                    defaultValue: item.access_type,
                  })}
                </TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    variant="outlined"
                    color={item.branch_id ? "primary" : "default"}
                    label={item.branch_name ?? t("clientAccess.allBranches")}
                  />
                </TableCell>
                <TableCell>
                  {item.label}
                  <Typography variant="body2" color="text.secondary" dir="ltr">
                    {item.server_or_address ?? "—"}{" "}
                    {item.server_or_address && (
                      <Tooltip title={t("clientAccess.copyAddress")}>
                        <IconButton
                          size="small"
                          onClick={() => copy(item.server_or_address)}
                        >
                          <ContentCopy fontSize="inherit" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Typography>
                </TableCell>
                <TableCell dir="ltr">
                  {item.username ?? "—"}{" "}
                  {item.username && (
                    <Tooltip title={t("clientAccess.copyUsername")}>
                      <IconButton
                        size="small"
                        onClick={() => copy(item.username)}
                      >
                        <ContentCopy fontSize="inherit" />
                      </IconButton>
                    </Tooltip>
                  )}
                </TableCell>
                <TableCell dir="ltr">
                  {revealed[item.id] !== undefined
                    ? revealed[item.id]
                    : item.has_password
                      ? "••••••••"
                      : "—"}{" "}
                  {item.has_password &&
                    hasPermission("client_access.reveal") && (
                      <>
                        <Tooltip
                          title={t(
                            revealed[item.id] !== undefined
                              ? "clientAccess.hidePassword"
                              : "clientAccess.revealPassword",
                          )}
                        >
                          <IconButton
                            size="small"
                            onClick={() =>
                              revealed[item.id] !== undefined
                                ? hide(item.id)
                                : secret(item)
                            }
                          >
                            {revealed[item.id] !== undefined ? (
                              <VisibilityOff fontSize="inherit" />
                            ) : (
                              <Visibility fontSize="inherit" />
                            )}
                          </IconButton>
                        </Tooltip>
                        <Tooltip title={t("clientAccess.copyPassword")}>
                          <IconButton
                            size="small"
                            onClick={() => copySecret(item)}
                          >
                            <ContentCopy fontSize="inherit" />
                          </IconButton>
                        </Tooltip>
                      </>
                    )}
                </TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={t(
                      item.is_active
                        ? "clientAccess.active"
                        : "clientAccess.inactive",
                    )}
                    color={item.is_active ? "success" : "default"}
                  />
                </TableCell>
                <TableCell align="right">
                  {hasPermission("client_access.manage") && (
                    <IconButton
                      aria-label={t("clientAccess.edit")}
                      onClick={() => {
                        setEditing(item);
                        setBranchId(item.branch_id ?? "");
                        setOpen(true);
                      }}
                    >
                      <Edit />
                    </IconButton>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      <Dialog
        open={open}
        onClose={() => {
          setOpen(false);
          setEditing(null);
          setBranchId("");
          setAddingBranch(false);
        }}
        fullWidth
        maxWidth="sm"
      >
        <Stack component="form" key={editing?.id ?? "new"} onSubmit={submit}>
          <DialogTitle>
            {t(editing ? "clientAccess.edit" : "clientAccess.addTitle")}
          </DialogTitle>
          <DialogContent>
            <TextField
              select
              label={t("clientAccess.branchScope")}
              value={branchId}
              onChange={(event) =>
                setBranchId(event.target.value ? Number(event.target.value) : "")
              }
              helperText={t("clientAccess.branchScopeHelp")}
              fullWidth
              margin="normal"
            >
              <MenuItem value="">{t("clientAccess.allBranches")}</MenuItem>
              {branches.data?.filter((branch) => branch.is_active).map((branch) => (
                <MenuItem key={branch.id} value={branch.id}>
                  {branch.name}
                </MenuItem>
              ))}
            </TextField>
            {!addingBranch ? (
              <Button
                size="small"
                startIcon={<Add />}
                onClick={() => setAddingBranch(true)}
              >
                {t("clientAccess.addBranch")}
              </Button>
            ) : (
              <Stack direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ sm: "center" }}>
                <TextField
                  size="small"
                  label={t("clientAccess.newBranchName")}
                  value={newBranchName}
                  onChange={(event) => setNewBranchName(event.target.value)}
                  fullWidth
                  autoFocus
                />
                <Button
                  variant="outlined"
                  disabled={newBranchName.trim().length < 2 || createBranch.isPending}
                  onClick={() => createBranch.mutate()}
                  sx={{ whiteSpace: "nowrap" }}
                >
                  {t("clientAccess.createBranch")}
                </Button>
                <Button onClick={() => { setAddingBranch(false); setNewBranchName(""); }}>
                  {t("clientAccess.cancel")}
                </Button>
              </Stack>
            )}
            <TextField
              select
              name="access_type"
              label={t("clientAccess.accessType")}
              defaultValue={editing?.access_type ?? "SERVER"}
              required
              fullWidth
              margin="normal"
            >
              {TYPES.map((value) => (
                <MenuItem key={value} value={value}>
                  {t(`clientAccess.types.${value}`)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              name="label"
              label={t("clientAccess.label")}
              defaultValue={editing?.label ?? ""}
              required
              fullWidth
              margin="normal"
            />
            <TextField
              name="server_or_address"
              label={t("clientAccess.address")}
              defaultValue={editing?.server_or_address ?? ""}
              fullWidth
              margin="normal"
              inputProps={{ dir: "ltr" }}
            />
            <TextField
              name="username"
              label={t("clientAccess.username")}
              defaultValue={editing?.username ?? ""}
              fullWidth
              margin="normal"
              autoComplete="off"
              inputProps={{ dir: "ltr" }}
            />
            <TextField
              name="password"
              label={t(
                editing ? "clientAccess.newPassword" : "clientAccess.password",
              )}
              type="password"
              fullWidth
              margin="normal"
              autoComplete="new-password"
              inputProps={{ dir: "ltr" }}
            />
            <TextField
              name="notes"
              label={t("clientAccess.notes")}
              defaultValue={editing?.notes ?? ""}
              multiline
              rows={3}
              fullWidth
              margin="normal"
            />
            <TextField
              select
              name="is_active"
              label={t("clientAccess.status")}
              defaultValue={String(editing?.is_active ?? true)}
              fullWidth
              margin="normal"
            >
              <MenuItem value="true">{t("clientAccess.active")}</MenuItem>
              <MenuItem value="false">{t("clientAccess.inactive")}</MenuItem>
            </TextField>
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                setOpen(false);
                setEditing(null);
                setBranchId("");
                setAddingBranch(false);
              }}
            >
              {t("clientAccess.cancel")}
            </Button>
            <Button type="submit" variant="contained" disabled={save.isPending}>
              {t("clientAccess.save")}
            </Button>
          </DialogActions>
        </Stack>
      </Dialog>
    </Paper>
  );
}
