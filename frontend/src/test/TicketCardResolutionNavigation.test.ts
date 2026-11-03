import { describe, expect, it } from "vitest";
import {
  ticketCardDropMode,
  ticketCardAllowsResolutionAttachments,
  ticketCardAllowsKnowledgeResolution,
  ticketCardNeedsStatusMove,
  ticketCardRequestStatus,
  ticketCardRequiresResolution,
  ticketCardTransitionMode,
  ticketNeedsApprovalAttention,
} from "../pages/TicketsPage";

describe("ticket board assignment lane", () => {
  it("self-assigns an unassigned or shared ticket", () => {
    expect(
      ticketCardDropMode("ASSIGNED", {
        assigned_user_id: undefined,
        is_shared_assignment: true,
      }),
    ).toBe("self-assignment");
  });

  it("uses a direct transition when a dedicated engineer already exists", () => {
    expect(
      ticketCardDropMode("ASSIGNED", {
        assigned_user_id: 42,
        is_shared_assignment: false,
      }),
    ).toBe("direct");
  });

  it("reassigns a shared Support ticket even when its stored status is already assigned", () => {
    expect(
      ticketCardNeedsStatusMove("ASSIGNED", 2, {
        status_id: 2,
        is_shared_assignment: true,
      }),
    ).toBe(true);
    expect(
      ticketCardNeedsStatusMove("ASSIGNED", 2, {
        status_id: 2,
        is_shared_assignment: false,
      }),
    ).toBe(false);
  });
});

describe("ticket board approval handling", () => {
  it("opens approval attention for a ticket awaiting approval", () => {
    expect(
      ticketNeedsApprovalAttention({ entitlement_status: "PENDING_APPROVAL" }),
    ).toBe(true);
    expect(
      ticketNeedsApprovalAttention({ entitlement_status: "APPROVED" }),
    ).toBe(false);
  });
});

describe("ticket card resolution navigation", () => {
  it("keeps resolution inside the card-view status dialog", () => {
    expect(ticketCardTransitionMode("RESOLVED")).toBe("status-dialog");
  });

  it("keeps pending and close transitions in a card-view status dialog", () => {
    expect(ticketCardTransitionMode("PENDING_INTERNAL")).toBe("status-dialog");
    expect(ticketCardTransitionMode("PENDING_CLIENT")).toBe("status-dialog");
    expect(ticketCardTransitionMode("CLOSED")).toBe("status-dialog");
    expect(ticketCardTransitionMode("IN_PROGRESS")).toBe("direct");
  });

  it("offers resolution attachments for both resolve and close", () => {
    expect(ticketCardAllowsResolutionAttachments("RESOLVED")).toBe(true);
    expect(ticketCardAllowsResolutionAttachments("CLOSED")).toBe(true);
    expect(ticketCardAllowsResolutionAttachments("IN_PROGRESS")).toBe(false);
  });

  it("offers Knowledge Base resolution search only to authorized resolvers", () => {
    expect(ticketCardAllowsKnowledgeResolution("RESOLVED", true)).toBe(true);
    expect(ticketCardAllowsKnowledgeResolution("CLOSED", true)).toBe(true);
    expect(ticketCardAllowsKnowledgeResolution("RESOLVED", false)).toBe(false);
    expect(ticketCardAllowsKnowledgeResolution("IN_PROGRESS", true)).toBe(false);
  });

  it("resolves and closes an active ticket dropped into the closed lane", () => {
    expect(ticketCardRequiresResolution("CLOSED", "IN_PROGRESS")).toBe(true);
    expect(ticketCardRequestStatus("CLOSED", "IN_PROGRESS")).toBe("RESOLVED");
  });

  it("closes an already resolved ticket without resolving it again", () => {
    expect(ticketCardRequiresResolution("CLOSED", "RESOLVED")).toBe(false);
    expect(ticketCardRequestStatus("CLOSED", "RESOLVED")).toBe("CLOSED");
  });

  it("moves resolution requirements from resolve to close in deferred mode", () => {
    expect(ticketCardRequiresResolution("RESOLVED", "IN_PROGRESS", true)).toBe(
      false,
    );
    expect(ticketCardRequiresResolution("CLOSED", "RESOLVED", true)).toBe(true);
    expect(
      ticketCardDropMode(
        "RESOLVED",
        { assigned_user_id: 42, is_shared_assignment: false },
        true,
      ),
    ).toBe("direct");
  });
});
