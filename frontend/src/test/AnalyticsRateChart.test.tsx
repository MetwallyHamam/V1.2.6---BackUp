import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { AnalyticsRateChart } from "../components/AnalyticsRateChart";

it("opens the selected metric's evidence and distinguishes zero from unavailable data", () => {
  const zero = { code: "ON_TIME", name: "On time", status: "READY", unit: "PERCENT", value: 0 };
  const unknown = { code: "ESTIMATE", name: "Estimate accuracy", status: "UNAVAILABLE", unit: "PERCENT", value: null };
  const hours = { code: "AGING", name: "Blocker aging", status: "READY", unit: "HOURS", value: 24 };
  const open = vi.fn();
  render(<AnalyticsRateChart title="Delivery performance" metrics={[zero, unknown, hours]} onOpen={open} />);
  fireEvent.click(screen.getByRole("button", { name: "On time, 0%, view evidence" }));
  expect(open).toHaveBeenCalledWith(zero);
  expect(screen.getByRole("button", { name: /Estimate accuracy, No eligible data/ })).toBeDisabled();
  expect(screen.queryByRole("button", { name: /Blocker aging/ })).not.toBeInTheDocument();
});
