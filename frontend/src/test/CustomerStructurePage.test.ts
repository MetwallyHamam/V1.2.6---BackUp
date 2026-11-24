import { describe, expect, it } from "vitest";
import {
  buildDepartmentPolicyPayload,
  clientsForOrganization,
} from "../pages/CustomerStructurePage";

describe("customer structure workspace", () => {
  it("keeps clients isolated to the selected organization", () => {
    const clients = [
      { id: 1, code: "C1", name: "Luxor", organization_id: 10, is_active: true },
      { id: 2, code: "C2", name: "Cairo", organization_id: 11, is_active: true },
      { id: 3, code: "C3", name: "Unassigned", organization_id: null, is_active: true },
    ];

    expect(clientsForOrganization(clients, 10).map((item) => item.id)).toEqual([1]);
    expect(clientsForOrganization(clients, null).map((item) => item.id)).toEqual([3]);
  });

  it("serializes only direct policy editor assignments", () => {
    const payload = buildDepartmentPolicyPayload("OVERRIDE", "Implementation phase", [
      {
        department_id: "7",
        relationship: "TEMPORARY_OPERATOR",
        access_profile: "IMPLEMENTATION_OPERATOR",
        effective_from: "2026-11-23T09:00",
        effective_until: "2027-02-28T18:00",
        reason: "Delivery and stabilization",
      },
    ]);

    expect(payload).toEqual({
      mode: "OVERRIDE",
      change_reason: "Implementation phase",
      assignments: [
        {
          department_id: 7,
          relationship: "TEMPORARY_OPERATOR",
          access_profile: "IMPLEMENTATION_OPERATOR",
          effective_from: "2026-11-23T09:00",
          effective_until: "2027-02-28T18:00",
          reason: "Delivery and stabilization",
        },
      ],
    });
  });
});
