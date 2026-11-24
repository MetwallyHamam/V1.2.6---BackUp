import {describe,expect,it} from "vitest";
import {groupExecutionTasks} from "../pages/ProjectExecutionPage";

const task=(id:number,status:string)=>({id,task_number:`T-${id}`,title:"Task",classification:"PLANNED",status,priority:"NORMAL",owner_user_id:1,approval_status:"NOT_REQUIRED",progress_percent:0,estimate_minutes:60,actual_minutes:0,planned_end_date:null,unplanned_cause:null,impact_summary:null,assignees:[]});
describe("project execution lanes",()=>{it("groups each task into its governed lifecycle lane",()=>{const grouped=groupExecutionTasks([task(1,"READY"),task(2,"BLOCKED"),task(3,"READY")]);expect(grouped.READY.map(x=>x.id)).toEqual([1,3]);expect(grouped.BLOCKED[0].id).toBe(2);expect(grouped.DONE).toEqual([])})});
