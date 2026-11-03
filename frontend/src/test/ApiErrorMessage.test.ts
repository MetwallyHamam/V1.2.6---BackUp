import { AxiosError, AxiosHeaders } from "axios";
import { describe, expect, it } from "vitest";

import { apiErrorMessage } from "../api/client";

const headers = new AxiosHeaders({ "X-Correlation-ID": "test-reference" });

describe("API error guidance", () => {
  it("shows a short hint for a timed-out read", () => {
    const error = new AxiosError("timeout", "ECONNABORTED", {
      headers,
      method: "get",
      timeout: 30_000,
      url: "/tickets",
    });

    expect(apiErrorMessage(error)).toBe(
      "Tickets is taking too long. Please try again.",
    );
  });

  it("warns that a timed-out write may already have completed", () => {
    const error = new AxiosError("timeout", "ECONNABORTED", {
      headers,
      method: "post",
      timeout: 30_000,
      url: "/pre-tickets",
    });

    expect(apiErrorMessage(error)).toBe(
      "No response from the server. Check whether the action completed before retrying.",
    );
  });

  it("replaces raw gateway status wording with recovery guidance", () => {
    const error = new AxiosError(
      "Request failed with status code 502",
      "ERR_BAD_RESPONSE",
      { headers, method: "get", url: "/home/snapshot" },
      undefined,
      {
        data: "Bad Gateway",
        status: 502,
        statusText: "Bad Gateway",
        headers: {},
        config: { headers },
      },
    );

    expect(apiErrorMessage(error)).toBe(
      "Support Now is temporarily unavailable. Please try again shortly.",
    );
    expect(apiErrorMessage(error)).not.toContain(
      "Request failed with status code",
    );
  });

  it("shows a short hint when the server cannot be reached", () => {
    const error = new AxiosError("Network Error", "ERR_NETWORK", {
      headers,
      method: "get",
      url: "/tickets",
    });

    expect(apiErrorMessage(error)).toBe(
      "Connection lost. Check your network and try again.",
    );
    expect(apiErrorMessage(error)).not.toContain("test-reference");
  });
});
