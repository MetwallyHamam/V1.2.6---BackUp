import { Close, Search, Tune } from "@mui/icons-material";
import {
  Badge,
  Box,
  IconButton,
  InputAdornment,
  MenuItem,
  Stack,
  TextField,
  Tooltip,
} from "@mui/material";
import type { ReactNode } from "react";

type Option = { value: string; label: string };

type DataListToolbarProps = {
  search: string;
  onSearchChange: (value: string) => void;
  searchLabel: string;
  filterValue?: string;
  onFilterChange?: (value: string) => void;
  filterLabel?: string;
  filterOptions?: Option[];
  activeFilterCount?: number;
  onClear?: () => void;
  clearLabel?: string;
  actions?: ReactNode;
};

/** A compact, responsive control row shared by record-list pages. */
export function DataListToolbar({
  search,
  onSearchChange,
  searchLabel,
  filterValue,
  onFilterChange,
  filterLabel,
  filterOptions = [],
  activeFilterCount = 0,
  onClear,
  clearLabel = "Clear filters",
  actions,
}: DataListToolbarProps) {
  return (
    <Stack direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ sm: "center" }} mb={2}>
      <TextField
        size="small"
        value={search}
        onChange={(event) => onSearchChange(event.target.value)}
        label={searchLabel}
        sx={{ flex: 1, minWidth: { sm: 240 } }}
        slotProps={{ input: { startAdornment: <InputAdornment position="start"><Search fontSize="small" /></InputAdornment> } }}
      />
      {onFilterChange && (
        <TextField
          select
          size="small"
          label={filterLabel}
          value={filterValue ?? ""}
          onChange={(event) => onFilterChange(event.target.value)}
          sx={{ minWidth: { sm: 160 } }}
          slotProps={{ input: { startAdornment: <InputAdornment position="start"><Badge color="primary" badgeContent={activeFilterCount}><Tune fontSize="small" /></Badge></InputAdornment> } }}
        >
          {filterOptions.map((option) => <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>)}
        </TextField>
      )}
      <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
        {activeFilterCount > 0 && onClear && <Tooltip title={clearLabel}><IconButton aria-label={clearLabel} onClick={onClear}><Close /></IconButton></Tooltip>}
        {actions}
      </Box>
    </Stack>
  );
}
