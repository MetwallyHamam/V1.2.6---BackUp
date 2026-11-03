export function selectTopSupportAgents<
  T extends { department?: string | null; assigned: number },
>(rows: T[], limit = 3): T[] {
  return rows
    .filter(
      (row) =>
        row.department?.trim().toLowerCase() === "support" && row.assigned > 0,
    )
    .slice(0, limit);
}
