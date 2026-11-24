import {describe,expect,it} from "vitest";
import {executiveOperationsParams} from "../components/UnifiedOperationsExecutivePanel";

describe("Unified executive operations filters",()=>{it("uses the dashboard period and active hierarchy scope",()=>{expect(executiveOperationsParams("2026-11-01","2026-11-30","2","")).toEqual({period_start:"2026-11-01",period_end:"2026-11-30",account_id:"2"});});});
