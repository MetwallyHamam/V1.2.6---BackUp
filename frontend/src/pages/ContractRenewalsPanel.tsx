import {
  Alert,
  Button,
  Chip,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, apiErrorMessage } from "../api/client";
import { randomUuid } from "../utils/randomUuid";

type Coverage = {
  id: number;
  product_id?: number;
  service_id?: number;
  product_module_id?: number;
  is_covered?: boolean;
  retired_at?: string;
};
type Employee = { id: number; full_name: string };
type RenewalLine = {
  id: number;
  coverage_id: number;
  outcome: string;
  successor_coverage_id?: number | null;
  reason?: string | null;
};
type Renewal = {
  id: number;
  stage: string;
  outcome?: string | null;
  successor_contract_id?: number | null;
  owner_user_id: number;
  target_close_date: string;
  reason: string;
  version: number;
  lines: RenewalLine[];
};
type Contract = {
  id: number;
  client_id: number;
  linked_client_ids?: number[];
  applies_to_all_clients?: boolean;
  contract_number: string;
  start_date: string;
  end_date: string;
  status: string;
  is_active: boolean;
};

function RenewalEditor({
  item,
  contractId,
  employees,
  contracts,
  onSaved,
}: {
  item: Renewal;
  contractId: number;
  employees: Employee[];
  contracts: Contract[];
  onSaved: () => Promise<void>;
}) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState(item);
  const current = contracts.find((contract) => contract.id === contractId);
  const successors = contracts.filter(
    (contract) =>
      current &&
      contract.id !== contractId &&
      (contract.applies_to_all_clients || (!current.applies_to_all_clients &&
        (current.linked_client_ids?.length ? current.linked_client_ids : [current.client_id]).every(id =>
          (contract.linked_client_ids?.length ? contract.linked_client_ids : [contract.client_id]).includes(id)))) &&
      contract.start_date > current.end_date &&
      contract.is_active &&
      ["DRAFT", "ACTIVE"].includes(contract.status),
  );
  const coverage = useQuery({
    queryKey: ["renewal-successor-coverage", draft.successor_contract_id],
    queryFn: async () =>
      (
        await api.get<Coverage[]>(
          `/contracts/${draft.successor_contract_id}/coverage`,
        )
      ).data,
    enabled: Boolean(draft.successor_contract_id),
  });
  const save = useMutation({
    mutationFn: async () =>
      api.put(`/contracts/${contractId}/renewal-opportunities/${item.id}`, {
        stage: draft.stage,
        outcome: draft.stage === "CLOSED" ? draft.outcome : null,
        successor_contract_id: draft.successor_contract_id || null,
        owner_user_id: draft.owner_user_id,
        target_close_date: draft.target_close_date,
        reason: draft.reason,
        version: item.version,
        lines: draft.lines.map(
          ({ coverage_id, outcome, successor_coverage_id, reason }) => ({
            coverage_id,
            outcome,
            successor_coverage_id: successor_coverage_id || null,
            reason,
          }),
        ),
      }),
    onSuccess: onSaved,
  });
  const changeLine = (id: number, changes: Partial<RenewalLine>) =>
    setDraft((previous) => ({
      ...previous,
      lines: previous.lines.map((line) =>
        line.id === id ? { ...line, ...changes } : line,
      ),
    }));
  return (
    <Stack
      component="form"
      spacing={2}
      mt={2}
      onSubmit={(event: FormEvent) => {
        event.preventDefault();
        save.mutate();
      }}
    >
      {save.isError && (
        <Alert severity="error">
          {apiErrorMessage(save.error, t("contractRenewals.editor.saveFailed"))}
        </Alert>
      )}
      <Stack direction={{ xs: "column", md: "row" }} gap={2}>
        <TextField
          select
          fullWidth
          label={t("contractRenewals.editor.stage")}
          value={draft.stage}
          onChange={(event) =>
            setDraft({ ...draft, stage: event.target.value, outcome: null })
          }
        >
          {[
            "IDENTIFIED",
            "QUALIFYING",
            "PROPOSAL",
            "NEGOTIATION",
            "CLOSED",
          ].map((stage) => (
            <MenuItem key={stage} value={stage}>
              {stage}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          fullWidth
          label={t("contractRenewals.editor.owner")}
          value={draft.owner_user_id}
          onChange={(event) =>
            setDraft({ ...draft, owner_user_id: Number(event.target.value) })
          }
        >
          {employees.map((employee) => (
            <MenuItem key={employee.id} value={employee.id}>
              {employee.full_name}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          required
          fullWidth
          type="date"
          label={t("contractRenewals.editor.targetDate")}
          value={draft.target_close_date}
          onChange={(event) =>
            setDraft({ ...draft, target_close_date: event.target.value })
          }
          slotProps={{ inputLabel: { shrink: true } }}
        />
      </Stack>
      {draft.stage === "CLOSED" && (
        <TextField
          select
          required
          label={t("contractRenewals.editor.outcome")}
          value={draft.outcome || ""}
          onChange={(event) =>
            setDraft({
              ...draft,
              outcome: event.target.value,
              successor_contract_id: ["LOST", "CANCELLED"].includes(
                event.target.value,
              )
                ? null
                : draft.successor_contract_id,
            })
          }
        >
          {["RENEWED", "PARTIAL", "LOST", "CANCELLED"].map((outcome) => (
            <MenuItem key={outcome} value={outcome}>
              {outcome}
            </MenuItem>
          ))}
        </TextField>
      )}
      <TextField
        select
        label={t("contractRenewals.editor.successor")}
        value={draft.successor_contract_id || ""}
        disabled={["LOST", "CANCELLED"].includes(draft.outcome || "")}
        onChange={(event) =>
          setDraft({
            ...draft,
            successor_contract_id: Number(event.target.value) || null,
            lines: draft.lines.map((line) => ({
              ...line,
              successor_coverage_id: null,
            })),
          })
        }
        helperText={t("contractRenewals.editor.successorHelp")}
      >
        <MenuItem value="">{t("contractRenewals.editor.none")}</MenuItem>
        {successors.map((contract) => (
          <MenuItem key={contract.id} value={contract.id}>
            {contract.contract_number} · {contract.start_date} —{" "}
            {contract.end_date}
          </MenuItem>
        ))}
      </TextField>
      {coverage.isError && (
        <Alert severity="error">
          {t("contractRenewals.editor.coverageFailed")}
        </Alert>
      )}
      {draft.lines.map((line) => (
        <Paper key={line.id} variant="outlined" sx={{ p: 2 }}>
          <Stack spacing={1}>
            <Typography>
              {t("contractRenewals.editor.coverage", { id: line.coverage_id })}
            </Typography>
            <TextField
              select
              label={t("contractRenewals.editor.coverageOutcome")}
              value={line.outcome}
              onChange={(event) =>
                changeLine(line.id, {
                  outcome: event.target.value,
                  ...(["LOST", "EXCLUDED", "PENDING"].includes(
                    event.target.value,
                  )
                    ? { successor_coverage_id: null }
                    : {}),
                })
              }
            >
              {["PENDING", "RENEWED", "CHANGED", "LOST", "EXCLUDED"].map(
                (outcome) => (
                  <MenuItem key={outcome} value={outcome}>
                    {outcome}
                  </MenuItem>
                ),
              )}
            </TextField>
            {["RENEWED", "CHANGED"].includes(line.outcome) && (
              <TextField
                select
                required
                label={t("contractRenewals.editor.successorCoverage")}
                value={line.successor_coverage_id || ""}
                onChange={(event) =>
                  changeLine(line.id, {
                    successor_coverage_id: Number(event.target.value),
                  })
                }
              >
                {coverage.data
                  ?.filter((row) => row.is_covered && !row.retired_at)
                  .map((row) => (
                    <MenuItem key={row.id} value={row.id}>
                      {t("contractRenewals.editor.coverageOption", {
                        id: row.id,
                        product:
                          row.product_id || t("contractRenewals.editor.any"),
                        module:
                          row.product_module_id ||
                          t("contractRenewals.editor.any"),
                        service:
                          row.service_id || t("contractRenewals.editor.any"),
                      })}
                    </MenuItem>
                  ))}
              </TextField>
            )}
            <TextField
              label={t("contractRenewals.editor.coverageNote")}
              value={line.reason || ""}
              onChange={(event) =>
                changeLine(line.id, { reason: event.target.value })
              }
            />
          </Stack>
        </Paper>
      ))}
      <TextField
        required
        label={t("contractRenewals.editor.reason")}
        multiline
        minRows={2}
        value={draft.reason}
        onChange={(event) => setDraft({ ...draft, reason: event.target.value })}
        inputProps={{ minLength: 5, maxLength: 1000 }}
      />
      <Button type="submit" variant="contained" disabled={save.isPending}>
        {t("contractRenewals.editor.save")}
      </Button>
    </Stack>
  );
}

export function ContractRenewalsPanel({
  contractId,
  coverage,
  canManage,
}: {
  contractId: number;
  coverage: Coverage[];
  canManage: boolean;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [creationKey, setCreationKey] = useState(() => randomUuid());
  const renewals = useQuery({
    queryKey: ["renewal-opportunities", contractId],
    queryFn: async () =>
      (
        await api.get<Renewal[]>(
          `/contracts/${contractId}/renewal-opportunities`,
        )
      ).data,
  });
  const employees = useQuery({
    queryKey: ["renewal-owners", contractId],
    queryFn: async () =>
      (await api.get<Employee[]>(`/contracts/${contractId}/renewal-owners`))
        .data,
    enabled: canManage,
  });
  const contracts = useQuery({
    queryKey: ["renewal-contract-options"],
    queryFn: async () => (await api.get<Contract[]>("/contracts")).data,
    enabled: canManage,
  });
  const refresh = async () => {
    await Promise.all(
      [
        "renewal-opportunities",
        "contract-lifecycle-board",
        "contracts",
        "contract-renewals",
        "renewal-contract-options",
      ].map((key) => queryClient.invalidateQueries({ queryKey: [key] })),
    );
  };
  const create = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(`/contracts/${contractId}/renewal-opportunities`, payload),
    onSuccess: async () => {
      setCreationKey(randomUuid());
      await refresh();
    },
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    create.mutate(
      {
        idempotency_key: creationKey,
        owner_user_id: Number(data.owner_user_id),
        target_close_date: data.target_close_date,
        reason: String(data.reason),
        lines: coverage
          .filter((row) => !row.retired_at)
          .map((row) => ({ coverage_id: row.id, outcome: "PENDING" })),
      },
      { onSuccess: () => form.reset() },
    );
  }
  return (
    <Stack spacing={2}>
      <Alert severity="info">{t("contractRenewals.notice")}</Alert>
      {(renewals.isError || contracts.isError || employees.isError) && (
        <Alert severity="error">
          {t("contractRenewals.editor.loadFailed")}
        </Alert>
      )}
      {create.isError && (
        <Alert severity="error">
          {apiErrorMessage(
            create.error,
            t("contractRenewals.editor.createFailed"),
          )}
        </Alert>
      )}
      {renewals.data?.map((item) => (
        <Paper key={item.id} variant="outlined" sx={{ p: 2 }}>
          <Stack direction="row" gap={1}>
            <Typography fontWeight={800} flex={1}>
              Renewal #{item.id} · {item.target_close_date}
            </Typography>
            <Chip label={item.stage} />
            {item.outcome && <Chip label={item.outcome} />}
          </Stack>
          {canManage && item.stage !== "CLOSED" ? (
            <RenewalEditor
              key={`${item.id}:${item.version}`}
              item={item}
              contractId={contractId}
              employees={employees.data || []}
              contracts={contracts.data || []}
              onSaved={refresh}
            />
          ) : (
            <>
              <Typography>{item.reason}</Typography>
              {item.lines.map((line) => (
                <Typography key={line.id}>
                  Coverage #{line.coverage_id}: {line.outcome}
                  {line.successor_coverage_id
                    ? ` → #${line.successor_coverage_id}`
                    : ""}
                </Typography>
              ))}
            </>
          )}
        </Paper>
      ))}
      {!renewals.isPending && !renewals.data?.length && (
        <Typography>{t("contractRenewals.empty")}</Typography>
      )}
      {canManage && (
        <Paper
          component="form"
          onSubmit={submit}
          variant="outlined"
          sx={{ p: 2 }}
        >
          <Typography fontWeight={800}>
            {t("contractRenewals.create")}
          </Typography>
          <TextField
            select
            required
            name="owner_user_id"
            label={t("contractRenewals.owner")}
            defaultValue=""
            fullWidth
            margin="normal"
          >
            <MenuItem value="" disabled>
              {t("contractRenewals.editor.owner")}
            </MenuItem>
            {employees.data?.map((item) => (
              <MenuItem key={item.id} value={item.id}>
                {item.full_name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            required
            type="date"
            name="target_close_date"
            label={t("contractRenewals.targetClose")}
            fullWidth
            margin="normal"
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <TextField
            required
            name="reason"
            label={t("contractRenewals.context")}
            fullWidth
            multiline
            rows={2}
            margin="normal"
            inputProps={{ minLength: 5, maxLength: 1000 }}
          />
          <Button type="submit" variant="contained" disabled={create.isPending}>
            {t("contractRenewals.createLines")}
          </Button>
        </Paper>
      )}
    </Stack>
  );
}
