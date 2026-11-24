import {describe,expect,it} from "vitest";
import {readinessTone} from "../components/ProjectSupportHandoverPanel";
describe("handover readiness tone",()=>{it("distinguishes blocked, warning, and complete readiness",()=>{expect(readinessTone(40)).toBe("error");expect(readinessTone(80)).toBe("warning");expect(readinessTone(100)).toBe("success")})});
