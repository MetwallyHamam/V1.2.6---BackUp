import { describe, expect, it } from "vitest";
import {
  clampAssistantWidth,
  isUnreceivedQueueTicket,
} from "../pages/SupportWorkspacePage";

describe("support assistant sizing", () => {
  it("keeps dragged requested widths inside usable limits", () => {
    expect(clampAssistantWidth(200, 1440)).toBe(360);
    expect(clampAssistantWidth(760, 1440)).toBe(760);
    expect(clampAssistantWidth(1400, 1440)).toBe(1200);
    expect(clampAssistantWidth(1080, 900)).toBe(876);
  });
});

describe("support assistant queue warning", () => {
  const now = Date.parse("2026-09-08T12:00:00Z");

  it("starts after an unassigned ticket has waited nine minutes", () => {
    expect(
      isUnreceivedQueueTicket(
        { assigned_user_id: undefined, created_at: "2026-09-08T11:51:00Z" },
        now,
      ),
    ).toBe(true);
  });

  it("does not warn before nine minutes or after assignment", () => {
    expect(
      isUnreceivedQueueTicket(
        { assigned_user_id: undefined, created_at: "2026-09-08T11:51:01Z" },
        now,
      ),
    ).toBe(false);
    expect(
      isUnreceivedQueueTicket(
        { assigned_user_id: 42, created_at: "2026-09-08T11:40:00Z" },
        now,
      ),
    ).toBe(false);
  });

  it("warns for a shared queue assignee when no dedicated engineer has claimed it", () => {
    expect(
      isUnreceivedQueueTicket(
        { assigned_user_id: 7, created_at: "2026-09-08T11:40:00Z" },
        now,
        true,
      ),
    ).toBe(true);
  });
});
