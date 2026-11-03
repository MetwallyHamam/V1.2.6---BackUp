function localIsoDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function currentMonthToDate(reference = new Date()): {
  dateFrom: string;
  dateTo: string;
} {
  return {
    dateFrom: localIsoDate(new Date(reference.getFullYear(), reference.getMonth(), 1)),
    dateTo: localIsoDate(reference),
  };
}
