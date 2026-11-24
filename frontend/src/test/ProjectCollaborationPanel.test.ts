import {describe,expect,it} from "vitest";
import {sharedEventCount} from "../components/ProjectCollaborationPanel";
describe("collaboration visibility",()=>{it("counts only explicit Support-shared events",()=>{const events=[{id:1,title:"Private",summary:"x",visibility:"PROJECT_PRIVATE",created_at:""},{id:2,title:"Shared",summary:"y",visibility:"SUPPORT_SHARED",created_at:""}];expect(sharedEventCount(events)).toBe(1)})});
