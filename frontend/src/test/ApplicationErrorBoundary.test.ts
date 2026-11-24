import { describe, expect, it } from "vitest";

import { isStaleApplicationChunkError } from "../components/ApplicationErrorBoundary";

describe("stale application chunk detection", () => {
  it("detects a missing dynamically imported deployment asset", () => {
    expect(
      isStaleApplicationChunkError(
        new Error(
          "Failed to fetch dynamically imported module: http://localhost/SupportHub/assets/NotificationsPage-old.js",
        ),
      ),
    ).toBe(true);
  });

  it("does not reload for an ordinary rendering error", () => {
    expect(isStaleApplicationChunkError(new Error("Invalid ticket data"))).toBe(
      false,
    );
  });
});
