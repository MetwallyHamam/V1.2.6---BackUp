import {describe,expect,it} from "vitest";
import {supportReadinessParams} from "../pages/SupportReadinessAnalyticsPage";

describe("Support readiness filters",()=>{it("omits inactive scope filters",()=>{expect(supportReadinessParams({period_start:"2026-11-01",period_end:"2026-11-30",account_id:"",organization_id:"3",client_id:"9",department_id:"2"})).toEqual({period_start:"2026-11-01",period_end:"2026-11-30",organization_id:"3",client_id:"9",department_id:"2"});});});
