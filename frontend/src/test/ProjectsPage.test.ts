import { describe, expect, it } from "vitest";
import { projectMatches } from "../pages/ProjectsPage";

const project = { id:1, project_number:"PRJ-001", name:"UHIA rollout", status:"ACTIVE", health:"ON_TRACK", priority:"NORMAL", progress_percent:35, account_id:1, organization_id:2, client_id:3, owning_department_id:4, project_manager_user_id:5, planned_start_date:null, planned_end_date:null };

describe("project portfolio filtering", () => {
  it("matches number and name without case sensitivity", () => {
    expect(projectMatches(project, "prj-001", "")).toBe(true);
    expect(projectMatches(project, "uhia", "")).toBe(true);
  });
  it("enforces an optional status filter", () => {
    expect(projectMatches(project, "", "ACTIVE")).toBe(true);
    expect(projectMatches(project, "", "PLANNING")).toBe(false);
  });
});
