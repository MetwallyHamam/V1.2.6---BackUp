import { describe, expect, it } from "vitest";
import { shiftTimeState } from "../components/HomeOperations";

describe("Support Now shift time state", () => {
  const startsAt = "2026-10-08T09:00:00Z";
  const endsAt = "2026-10-08T17:00:00Z";

  it("distinguishes upcoming, active, and ended shifts", () => {
    expect(shiftTimeState(startsAt, endsAt, Date.parse("2026-10-08T08:59:59Z"))).toBe("UPCOMING");
    expect(shiftTimeState(startsAt, endsAt, Date.parse("2026-10-08T12:00:00Z"))).toBe("ACTIVE");
    expect(shiftTimeState(startsAt, endsAt, Date.parse("2026-10-08T17:00:01Z"))).toBe("ENDED");
  });
});
