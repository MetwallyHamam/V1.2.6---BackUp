import {
  Add,
  Assessment,
  Download,
  PlayArrow,
  Search,
  Settings,
} from "@mui/icons-material";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Checkbox,
  InputAdornment,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { serverDateInput } from "../utils/serverTime";

type Filter = {
  name: string;
  label: string;
  type: "text" | "date" | "number" | "select" | "boolean" | "lookup";
  required?: boolean;
  default?: string | number | boolean;
  options?: Array<{ value: string | number; label: string }>;
  lookup_source?: string;
  depends_on?: string;
};

type LookupOption = { value: string | number; label: string; code?: string };
const inferredLookups: Record<string, { source: string; dependsOn?: string }> = {
  client_id: { source: "clients" },
  engineer_id: { source: "users" },
  requested_by_user_id: { source: "users" },
  assigned_user_id: { source: "users" },
  product_id: { source: "products" },
  module_id: { source: "modules", dependsOn: "product_id" },
  product_module_id: { source: "modules", dependsOn: "product_id" },
  environment_id: { source: "environments" },
  service_id: { source: "services" },
  category_id: { source: "categories" },
  subcategory_id: { source: "subcategories", dependsOn: "category_id" },
  assigned_team: { source: "teams" },
  contract_id: { source: "contracts", dependsOn: "client_id" },
  ticket_type: { source: "ticket_types" },
  ticket_type_id: { source: "ticket_types" },
};

function lookupFor(filter: Filter) {
  if (filter.lookup_source)
    return { source: filter.lookup_source, dependsOn: filter.depends_on };
  return inferredLookups[filter.name];
}

function LookupFilter({
  filter,
  value,
  filters,
  onChange,
}: {
  filter: Filter;
  value: unknown;
  filters: Record<string, unknown>;
  onChange: (value: unknown) => void;
}) {
  const lookup = lookupFor(filter);
  const [search, setSearch] = useState("");
  const parentValue = lookup?.dependsOn ? filters[lookup.dependsOn] : undefined;
  const options = useQuery({
    queryKey: ["report-filter-options", lookup?.source, search, parentValue],
    queryFn: async () =>
      (
        await api.get<LookupOption[]>(`/reports-center/filter-options/${lookup?.source}`, {
          params: { q: search || undefined, parent_value: parentValue || undefined },
        })
      ).data,
    enabled: Boolean(lookup?.source),
    staleTime: 60_000,
  });
  const selected = options.data?.find(
    (option) => String(option.value) === String(value ?? ""),
  ) ?? (value === undefined || value === "" ? null : { value: value as string | number, label: String(value) });
  return (
    <Autocomplete
      options={options.data ?? []}
      value={selected}
      loading={options.isLoading}
      onInputChange={(_, next, reason) => reason === "input" && setSearch(next)}
      onChange={(_, next) => onChange(next?.value ?? "")}
      isOptionEqualToValue={(option, current) => String(option.value) === String(current.value)}
      getOptionLabel={(option) => option.code ? `${option.label} · ${option.code}` : option.label}
      renderInput={(params) => (
        <TextField
          {...params}
          label={filter.label}
          required={filter.required}
          placeholder={`Search ${filter.label.toLowerCase()}`}
        />
      )}
    />
  );
}
type Definition = {
  id: number;
  code: string;
  name: string;
  description?: string;
  category: string;
  stored_procedure: string;
  filters: Filter[];
  default_page_size: number;
  default_sort_column?: string;
  default_sort_direction: "ASC" | "DESC";
  is_active: boolean;
  is_system: boolean;
};
type Column = { field: string; label: string; type: string };
type Result = {
  definition: Definition;
  columns: Column[];
  rows: Array<Record<string, unknown>>;
  summary: Record<string, unknown>;
  pagination: {
    page: number;
    page_size: number;
    total_records: number;
    total_pages: number;
  };
};

const starterFilters = JSON.stringify(
  [
    {
      name: "date_from",
      label: "Date from",
      type: "date",
      required: true,
      options: [],
    },
    {
      name: "date_to",
      label: "Date to",
      type: "date",
      required: true,
      options: [],
    },
    {
      name: "client_id",
      label: "Client",
      type: "lookup",
      lookup_source: "clients",
      required: false,
      options: [],
    },
  ],
  null,
  2,
);

function defaultReportFilters(definition: Definition) {
  const today = new Date();
  const recent = new Date(today);
  recent.setDate(recent.getDate() - 30);
  return Object.fromEntries(
    definition.filters.flatMap((filter) => {
      if (filter.default !== undefined) return [[filter.name, filter.default]];
      if (filter.type !== "date") return [];
      const isBeginning = /from|start|begin/i.test(filter.name);
      return [[filter.name, serverDateInput(isBeginning ? recent : today)]];
    }),
  );
}

function reportFilterError(definition: Definition, filters: Record<string, unknown>) {
  const dateFilters = definition.filters.filter((filter) => filter.type === "date");
  const mandatoryDates = dateFilters.filter(
    (filter) => filter.required || filter.default !== "",
  );
  if (mandatoryDates.some((filter) => !filters[filter.name]))
    return "Select the complete date range before running this report.";
  for (const filter of dateFilters.filter((item) => item.name.endsWith("_from"))) {
    const prefix = filter.name.slice(0, -5);
    const paired = dateFilters.find((item) => item.name === `${prefix}_to`);
    if (!paired) continue;
    const from = String(filters[filter.name] ?? "");
    const to = String(filters[paired.name] ?? "");
    if (Boolean(from) !== Boolean(to))
      return `Select both ${filter.label.toLowerCase()} and ${paired.label.toLowerCase()}.`;
    if (from && to) {
      const days = (Date.parse(to) - Date.parse(from)) / 86_400_000;
      if (days < 0) return `${paired.label} cannot be before ${filter.label}.`;
      if (days > 366) return "Choose each report period as 366 days or less.";
    }
  }
  if (!dateFilters.length && !Object.values(filters).some((value) => value !== "" && value !== undefined && value !== false))
    return "Select at least one filter before running this report.";
  return null;
}

export function ReportsCenterPage() {
  const { hasPermission } = useAuth(),
    queryClient = useQueryClient(),
    [selectedCode, setSelectedCode] = useState(""),
    [filters, setFilters] = useState<Record<string, unknown>>({}),
    [appliedFilters, setAppliedFilters] = useState<Record<string, unknown> | null>(null),
    [page, setPage] = useState(0),
    [pageSize, setPageSize] = useState(25),
    [catalogSearch, setCatalogSearch] = useState(""),
    [manageOpen, setManageOpen] = useState(false),
    [createOpen, setCreateOpen] = useState(false);
  const catalog = useQuery({
    queryKey: ["reports-center-catalog"],
    queryFn: async () => (await api.get<Definition[]>("/reports-center")).data,
  });
  const definitions = useQuery({
    queryKey: ["reports-center-definitions"],
    queryFn: async () =>
      (await api.get<Definition[]>("/reports-center/definitions")).data,
    enabled: manageOpen && hasPermission("dashboard.manage_widgets"),
  });
  const selected = useMemo(
    () => catalog.data?.find((row) => row.code === selectedCode),
    [catalog.data, selectedCode],
  );
  const categorizedCatalog = useMemo(() => {
    const term = catalogSearch.trim().toLowerCase();
    const groups = new Map<string, Definition[]>();
    for (const item of catalog.data ?? []) {
      if (term && !`${item.name} ${item.description ?? ""} ${item.category}`.toLowerCase().includes(term)) continue;
      groups.set(item.category || "General", [...(groups.get(item.category || "General") ?? []), item]);
    }
    return [...groups.entries()].sort(([left], [right]) => left.localeCompare(right));
  }, [catalog.data, catalogSearch]);
  useEffect(() => {
    if (!selectedCode && catalog.data?.length)
      setSelectedCode(catalog.data[0].code);
  }, [catalog.data, selectedCode]);
  useEffect(() => {
    if (!selected) return;
    setPageSize(selected.default_page_size);
    setPage(0);
    setFilters(defaultReportFilters(selected));
    setAppliedFilters(null);
  }, [selected]);
  const report = useQuery({
    queryKey: ["dynamic-report", selectedCode, appliedFilters, page, pageSize],
    queryFn: async () =>
      (
        await api.post<Result>(`/reports-center/${selectedCode}/run`, {
          filters: appliedFilters,
          page: page + 1,
          page_size: pageSize,
          sort_by: selected?.default_sort_column ?? null,
          sort_direction: selected?.default_sort_direction ?? "DESC",
        })
      ).data,
    enabled: Boolean(selectedCode && appliedFilters),
  });
  const filterError = selected ? reportFilterError(selected, filters) : null;
  const create = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post("/reports-center/definitions", payload),
    onSuccess: async () => {
      setCreateOpen(false);
      await queryClient.invalidateQueries({
        queryKey: ["reports-center-catalog"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["reports-center-definitions"],
      });
    },
  });
  function changeFilter(name: string, value: unknown) {
    setFilters((current) => {
      const next = { ...current, [name]: value };
      for (const filter of selected?.filters ?? []) {
        const lookup = lookupFor(filter);
        if (lookup?.dependsOn === name) next[filter.name] = "";
      }
      return next;
    });
    setPage(0);
  }
  async function exportExcel() {
    if (!selectedCode || !appliedFilters) return;
    const response = await api.post(
      `/reports-center/${selectedCode}/export.xlsx`,
      {
        filters: appliedFilters,
        page: 1,
        page_size: pageSize,
        sort_by: selected?.default_sort_column ?? null,
        sort_direction: selected?.default_sort_direction ?? "DESC",
      },
      { responseType: "blob" },
    );
    const url = URL.createObjectURL(response.data),
      link = document.createElement("a");
    link.href = url;
    link.download = `${selectedCode}-${serverDateInput()}.xlsx`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function submitDefinition(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      const parsed = JSON.parse(String(data.get("filters")));
      create.mutate({
        code: String(data.get("code")).trim().toUpperCase(),
        name: data.get("name"),
        description: data.get("description") || null,
        category: data.get("category") || "General",
        stored_procedure: data.get("stored_procedure"),
        filters: parsed,
        default_page_size: Number(data.get("default_page_size") || 25),
        default_sort_column: data.get("default_sort_column") || null,
        default_sort_direction: data.get("default_sort_direction") || "DESC",
        is_active: data.get("is_active") === "on",
      });
    } catch {
      window.alert("Filter structure must be valid JSON.");
    }
  }
  return (
    <Stack spacing={2}>
      <Paper sx={{ p: 3 }}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          gap={2}
          alignItems={{ md: "center" }}
        >
          <Box flex={1}>
            <Typography variant="h4" fontWeight={900}>
              Reports Center
            </Typography>
            <Typography color="text.secondary">
              Filter, inspect, page, and export governed statistical reports.
            </Typography>
          </Box>
          {hasPermission("dashboard.manage_widgets") && (
            <Button
              startIcon={<Settings />}
              onClick={() => setManageOpen(true)}
            >
              Manage reports
            </Button>
          )}
          {hasPermission("report.export") && (
            <Button
              variant="contained"
              startIcon={<Download />}
              disabled={!report.data?.rows.length}
              onClick={exportExcel}
            >
              Export all to Excel
            </Button>
          )}
        </Stack>
      </Paper>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "280px minmax(0,1fr)" },
          gap: 2,
          alignItems: "start",
        }}
      >
        <Paper variant="outlined" sx={{ p: 1.5 }}>
          <Typography fontWeight={900} px={1} py={0.5}>
            Report catalog
          </Typography>
          <TextField
            size="small"
            fullWidth
            placeholder="Find a report"
            value={catalogSearch}
            onChange={(event) => setCatalogSearch(event.target.value)}
            sx={{ my: 1 }}
            slotProps={{ input: { startAdornment: <InputAdornment position="start"><Search fontSize="small" /></InputAdornment> } }}
          />
          <Stack spacing={1.5}>
            {categorizedCatalog.map(([category, items]) => (
              <Box key={category}>
                <Stack direction="row" alignItems="center" gap={1} px={1} py={0.5}>
                  <Typography variant="overline" fontWeight={900} color="text.secondary" flex={1}>{category}</Typography>
                  <Chip size="small" label={items.length} />
                </Stack>
                <Stack spacing={0.25}>
                  {items.map((item) => (
                    <Button
                      key={item.code}
                      startIcon={<Assessment />}
                      variant={selectedCode === item.code ? "contained" : "text"}
                      onClick={() => setSelectedCode(item.code)}
                      sx={{ justifyContent: "flex-start", textAlign: "start" }}
                    >
                      {item.name}
                    </Button>
                  ))}
                </Stack>
              </Box>
            ))}
            {!categorizedCatalog.length && <Alert severity="info">No reports match this search.</Alert>}
          </Stack>
        </Paper>
        <Stack spacing={2} minWidth={0}>
          {selected && (
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="h5" fontWeight={900}>
                {selected.name}
              </Typography>
              <Typography color="text.secondary">
                {selected.description}
              </Typography>
              <Chip size="small" label={selected.category} sx={{ my: 1 }} />
              <Alert severity="info" sx={{ mb: 1 }}>
                Reports do not load automatically. Choose the filters you need, then run the report.
              </Alert>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "1fr",
                    sm: "repeat(2,1fr)",
                    xl: "repeat(4,1fr)",
                  },
                  gap: 1.5,
                  mt: 1,
                }}
              >
                {selected.filters.map((filter) =>
                  lookupFor(filter) ? (
                    <LookupFilter
                      key={filter.name}
                      filter={filter}
                      value={filters[filter.name]}
                      filters={filters}
                      onChange={(value) => changeFilter(filter.name, value)}
                    />
                  ) : filter.type === "boolean" ? (
                    <FormControlLabel
                      key={filter.name}
                      control={
                        <Checkbox
                          checked={Boolean(filters[filter.name])}
                          onChange={(_, checked) =>
                            changeFilter(filter.name, checked)
                          }
                        />
                      }
                      label={filter.label}
                    />
                  ) : (
                    <TextField
                      key={filter.name}
                      select={filter.type === "select"}
                      type={
                        filter.type === "date"
                          ? "date"
                          : filter.type === "number"
                            ? "number"
                            : "text"
                      }
                      label={filter.label}
                      required={filter.required}
                      value={String(filters[filter.name] ?? "")}
                      onChange={(event) =>
                        changeFilter(filter.name, event.target.value)
                      }
                      slotProps={
                        filter.type === "date"
                          ? { inputLabel: { shrink: true } }
                          : undefined
                      }
                    >
                      <MenuItem value="">All</MenuItem>
                      {filter.options?.map((option) => (
                        <MenuItem key={option.value} value={option.value}>
                          {option.label}
                        </MenuItem>
                      ))}
                    </TextField>
                  ),
                )}
              </Box>
              <Stack direction="row" gap={1} mt={2}>
                <Button
                  startIcon={<PlayArrow />}
                  variant="contained"
                  disabled={Boolean(filterError)}
                  onClick={() => {
                    setPage(0);
                    setAppliedFilters({ ...filters });
                  }}
                >
                  Run report
                </Button>
                <Button
                  onClick={() => {
                    if (selected) setFilters(defaultReportFilters(selected));
                    setAppliedFilters(null);
                    setPage(0);
                  }}
                >
                  Reset
                </Button>
              </Stack>
              {filterError && <Alert severity="warning" sx={{ mt: 1.5 }}>{filterError}</Alert>}
            </Paper>
          )}
          {selected && !appliedFilters && !filterError && (
            <Alert severity="info">Set the filters and select Run report to load results.</Alert>
          )}
          {report.isError && (
            <Alert severity="error">
              The report could not be generated. Confirm that its stored
              procedure exists and follows the Reports Center contract.
            </Alert>
          )}
          {report.data && (
            <>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "repeat(2,1fr)",
                    md: "repeat(4,1fr)",
                  },
                  gap: 1.5,
                }}
              >
                <Paper sx={{ p: 2 }}>
                  <Typography color="text.secondary">
                    Matching records
                  </Typography>
                  <Typography variant="h4" fontWeight={900}>
                    {report.data.pagination.total_records}
                  </Typography>
                </Paper>
                {Object.entries(report.data.summary)
                  .slice(0, 3)
                  .map(([key, value]) => (
                    <Paper key={key} sx={{ p: 2 }}>
                      <Typography color="text.secondary">
                        {key.replaceAll("_", " ")}
                      </Typography>
                      <Typography variant="h4" fontWeight={900}>
                        {String(value ?? "—")}
                      </Typography>
                    </Paper>
                  ))}
              </Box>
              <Paper variant="outlined">
                <TableContainer sx={{ maxHeight: 620 }}>
                  <Table stickyHeader size="small">
                    <TableHead>
                      <TableRow>
                        {report.data.columns.map((column) => (
                          <TableCell
                            key={column.field}
                            sx={{ fontWeight: 900, whiteSpace: "nowrap" }}
                          >
                            {column.label}
                          </TableCell>
                        ))}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {report.data.rows.map((row, index) => (
                        <TableRow hover key={index}>
                          {report.data.columns.map((column) => (
                            <TableCell
                              key={column.field}
                              sx={{
                                whiteSpace: "nowrap",
                                maxWidth: 360,
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                              }}
                            >
                              {row[column.field] instanceof Date
                                ? new Date(
                                    String(row[column.field]),
                                  ).toLocaleString()
                                : String(row[column.field] ?? "")}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
                <TablePagination
                  component="div"
                  count={report.data.pagination.total_records}
                  page={page}
                  onPageChange={(_, value) => setPage(value)}
                  rowsPerPage={pageSize}
                  onRowsPerPageChange={(event) => {
                    setPageSize(Number(event.target.value));
                    setPage(0);
                  }}
                  rowsPerPageOptions={[25, 50, 100, 250]}
                />
              </Paper>
            </>
          )}
        </Stack>
      </Box>
      <Dialog
        open={manageOpen}
        onClose={() => setManageOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>Dynamic report definitions</DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            Only register reviewed stored procedures. Result columns are
            discovered automatically from the procedure output.
          </Alert>
          {definitions.data?.map((item) => (
            <Paper key={item.id} variant="outlined" sx={{ p: 1.5, mb: 1 }}>
              <Typography fontWeight={900}>
                {item.name} <Chip size="small" label={item.code} />
              </Typography>
              <Typography variant="body2">
                <span dir="ltr">{item.stored_procedure}</span> ·{" "}
                {item.filters.length} filters · {item.default_page_size} rows
              </Typography>
            </Paper>
          ))}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setManageOpen(false)}>Close</Button>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setCreateOpen(true)}
          >
            Register report
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <Box component="form" onSubmit={submitDefinition}>
          <DialogTitle>Register stored-procedure report</DialogTitle>
          <DialogContent>
            <Stack spacing={1.5} mt={1}>
              <TextField
                required
                name="code"
                label="Report code"
                helperText="Uppercase letters, numbers, and underscores"
              />
              <TextField required name="name" label="Report name" />
              <TextField
                name="description"
                label="Description"
                multiline
                rows={2}
              />
              <TextField
                name="category"
                label="Category"
                defaultValue="General"
              />
              <TextField
                required
                name="stored_procedure"
                label="Stored procedure"
                placeholder="dbo.usp_SupportHub_Report_Name"
              />
              <TextField
                required
                name="filters"
                label="Filter structure (JSON)"
                defaultValue={starterFilters}
                multiline
                minRows={10}
                helperText="Supported types: text, date, number, select, boolean, lookup. Lookup filters use lookup_source and optional depends_on."
              />
              <Stack direction="row" gap={1}>
                <TextField
                  select
                  name="default_page_size"
                  label="Default rows"
                  defaultValue="25"
                  fullWidth
                >
                  {[25, 50, 100, 250].map((value) => (
                    <MenuItem key={value} value={value}>
                      {value}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  name="default_sort_column"
                  label="Default sort column"
                  fullWidth
                />
                <TextField
                  select
                  name="default_sort_direction"
                  label="Direction"
                  defaultValue="DESC"
                  fullWidth
                >
                  <MenuItem value="ASC">Ascending</MenuItem>
                  <MenuItem value="DESC">Descending</MenuItem>
                </TextField>
              </Stack>
              <FormControlLabel
                control={<Checkbox name="is_active" defaultChecked />}
                label="Active"
              />
              {create.isError && (
                <Alert severity="error">
                  The definition could not be saved. Check that its code and
                  procedure name are unique.
                </Alert>
              )}
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button
              type="submit"
              variant="contained"
              disabled={create.isPending}
            >
              Register report
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}
