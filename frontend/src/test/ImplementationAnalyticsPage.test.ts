import { describe, expect, it } from "vitest";
import { implementationAnalyticsParams } from "../pages/ImplementationAnalyticsPage";

describe("Implementation Analytics scoping",()=>{
  it("sends active hierarchy, team and engineer filters",()=>{
    expect(implementationAnalyticsParams({period_start:"2026-11-01",period_end:"2026-11-30",account_id:"",organization_id:"2",client_id:"8",department_id:"4",team_id:"11",user_id:"23"})).toEqual({period_start:"2026-11-01",period_end:"2026-11-30",organization_id:"2",client_id:"8",department_id:"4",team_id:"11",user_id:"23"});
  });
});
