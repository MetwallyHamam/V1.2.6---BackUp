import { describe, expect, it } from "vitest";
import { permissionRegistry } from "../auth/permissionRegistry";

describe("Company operations setup", () => {
  it("registers the dedicated collaboration master-data capability", () => {
    expect(permissionRegistry["/company-operations-setup"]).toMatchObject({
      permission: "customer_structure.policy.view",
      module: "Company operations",
    });
  });
});
