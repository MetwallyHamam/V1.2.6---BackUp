import { afterEach, describe, expect, it, vi } from "vitest";
import { copyText } from "../utils/clipboard";

describe("copyText", () => {
  afterEach(() => vi.restoreAllMocks());

  it("uses the secure Clipboard API when available", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    await expect(copyText("rating link")).resolves.toBe(true);
    expect(writeText).toHaveBeenCalledWith("rating link");
  });

  it("falls back to document copy when Clipboard API is blocked", async () => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: vi.fn().mockRejectedValue(new Error("insecure origin")),
      },
    });
    const execCommand = vi.fn().mockReturnValue(true);
    Object.defineProperty(document, "execCommand", {
      configurable: true,
      value: execCommand,
    });

    await expect(copyText("live tracking link")).resolves.toBe(true);
    expect(execCommand).toHaveBeenCalledWith("copy");
  });
});
