/*
  Support Hub Reports Center catalog expansion (SQL Server)
  Requires database revision 0230 or later. Safe to run repeatedly.
  Each procedure follows the Reports Center paging/security parameter contract.
*/
SET NOCOUNT ON;
GO

CREATE OR ALTER VIEW dbo.vw_SupportHub_Report_TicketBase AS
SELECT t.id, t.ticket_number, t.subject, t.priority, t.impact, t.urgency,
       t.source_channel, t.assigned_team, t.entitlement_status,
       t.patient_safety_flag, t.security_incident_flag,
       t.created_at, t.resolved_at, t.closed_at, t.due_at,
       ts.code status_code, ts.name status_name, tt.name ticket_type,
       c.id client_id, c.name client_name, u.id engineer_id, u.full_name engineer_name,
       p.id product_id, p.name product_name, pm.id module_id, pm.name module_name,
       e.id environment_id, e.name environment_name, sc.id service_id, sc.name service_name,
       tc.id category_id, COALESCE(tc.name,t.category) category_name,
       tsc.id subcategory_id, COALESCE(tsc.name,t.subcategory) subcategory_name
FROM tickets t
JOIN ticket_statuses ts ON ts.id=t.status_id
JOIN ticket_types tt ON tt.id=t.ticket_type_id
JOIN clients c ON c.id=t.client_id
LEFT JOIN users u ON u.id=t.assigned_user_id
LEFT JOIN products p ON p.id=t.product_id
LEFT JOIN product_modules pm ON pm.id=t.product_module_id
LEFT JOIN environments e ON e.id=t.environment_id
LEFT JOIN service_catalog_items sc ON sc.id=t.service_id
LEFT JOIN ticket_categories tc ON tc.id=t.category_id
LEFT JOIN ticket_subcategories tsc ON tsc.id=t.subcategory_id;
GO

CREATE OR ALTER PROCEDURE dbo.usp_SupportHub_Report_TicketOperations
 @date_from date=NULL,@date_to date=NULL,@status_code nvarchar(50)=NULL,@priority nvarchar(10)=NULL,
 @client_id bigint=NULL,@engineer_id bigint=NULL,@product_id bigint=NULL,@environment_id bigint=NULL,
 @assigned_team nvarchar(150)=NULL,@source_channel nvarchar(30)=NULL,@search nvarchar(1000)=NULL,
 @page int=1,@page_size int=25,@sort_by nvarchar(120)=NULL,@sort_direction nvarchar(4)='DESC',@requesting_user_id bigint
AS BEGIN SET NOCOUNT ON; SET @page=IIF(@page<1,1,@page); SET @page_size=IIF(@page_size<1 OR @page_size>10000,25,@page_size);
 SELECT COUNT_BIG(1) OVER() __total_count,COUNT_BIG(1) OVER() __summary_total_tickets,
  ticket_number,subject,status_name [status],priority,client_name client,engineer_name assigned_to,
  assigned_team,product_name product,module_name module,environment_name environment,source_channel,created_at,due_at
 FROM dbo.vw_SupportHub_Report_TicketBase
 WHERE (@date_from IS NULL OR created_at>=@date_from) AND (@date_to IS NULL OR created_at<DATEADD(day,1,@date_to))
  AND (@status_code IS NULL OR status_code=@status_code) AND (@priority IS NULL OR priority=@priority)
  AND (@client_id IS NULL OR client_id=@client_id) AND (@engineer_id IS NULL OR engineer_id=@engineer_id)
  AND (@product_id IS NULL OR product_id=@product_id) AND (@environment_id IS NULL OR environment_id=@environment_id)
  AND (@assigned_team IS NULL OR assigned_team=@assigned_team) AND (@source_channel IS NULL OR source_channel=@source_channel)
  AND (@search IS NULL OR ticket_number LIKE '%'+@search+'%' OR subject LIKE '%'+@search+'%' OR client_name LIKE '%'+@search+'%')
 ORDER BY created_at DESC,id DESC OFFSET (@page-1)*@page_size ROWS FETCH NEXT @page_size ROWS ONLY;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_SupportHub_Report_SlaPerformance
 @date_from date=NULL,@date_to date=NULL,@clock_type nvarchar(30)=NULL,@state nvarchar(30)=NULL,@priority nvarchar(10)=NULL,
 @client_id bigint=NULL,@engineer_id bigint=NULL,@breached bit=NULL,
 @page int=1,@page_size int=25,@sort_by nvarchar(120)=NULL,@sort_direction nvarchar(4)='DESC',@requesting_user_id bigint
AS BEGIN SET NOCOUNT ON; SET @page=IIF(@page<1,1,@page); SET @page_size=IIF(@page_size<1 OR @page_size>10000,25,@page_size);
 SELECT COUNT_BIG(1) OVER() __total_count,SUM(IIF(s.breached_at IS NOT NULL,1,0)) OVER() __summary_breached,
  b.ticket_number,b.subject,b.client_name client,b.priority,b.engineer_name engineer,s.clock_type,s.state,s.target_minutes,
  s.accountable_minutes,s.customer_pending_minutes,s.millensys_pending_minutes,s.saved_minutes,s.overrun_minutes,s.due_at,s.completed_at
 FROM ticket_sla_clocks s JOIN dbo.vw_SupportHub_Report_TicketBase b ON b.id=s.ticket_id
 WHERE (@date_from IS NULL OR b.created_at>=@date_from) AND (@date_to IS NULL OR b.created_at<DATEADD(day,1,@date_to))
  AND (@clock_type IS NULL OR s.clock_type=@clock_type) AND (@state IS NULL OR s.state=@state) AND (@priority IS NULL OR b.priority=@priority)
  AND (@client_id IS NULL OR b.client_id=@client_id) AND (@engineer_id IS NULL OR b.engineer_id=@engineer_id)
  AND (@breached IS NULL OR IIF(s.breached_at IS NULL,0,1)=@breached)
 ORDER BY s.due_at DESC,s.id DESC OFFSET (@page-1)*@page_size ROWS FETCH NEXT @page_size ROWS ONLY;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_SupportHub_Report_TicketTurnaround
 @date_from date=NULL,@date_to date=NULL,@status_code nvarchar(50)=NULL,@ticket_type nvarchar(150)=NULL,
 @priority nvarchar(10)=NULL,@client_id bigint=NULL,@engineer_id bigint=NULL,@product_id bigint=NULL,
 @assigned_team nvarchar(150)=NULL,@completed_only bit=NULL,@sla_result nvarchar(20)=NULL,
 @minimum_minutes int=NULL,@maximum_minutes int=NULL,@search nvarchar(1000)=NULL,
 @page int=1,@page_size int=25,@sort_by nvarchar(120)=NULL,@sort_direction nvarchar(4)='DESC',@requesting_user_id bigint
AS BEGIN
 SET NOCOUNT ON;
 SET @page=IIF(@page<1,1,@page);
 SET @page_size=IIF(@page_size<1 OR @page_size>10000,25,@page_size);
 WITH x AS (
  SELECT b.*,
   COALESCE(b.resolved_at,b.closed_at) completed_at,
   DATEDIFF(minute,b.created_at,COALESCE(b.resolved_at,b.closed_at,SYSUTCDATETIME())) turnaround_minutes,
   CASE WHEN b.closed_at IS NULL THEN NULL ELSE DATEDIFF(minute,b.created_at,b.closed_at) END closure_minutes,
   sla.target_minutes,sla.accountable_minutes,sla.customer_pending_minutes,sla.millensys_pending_minutes,
   CASE WHEN sla.id IS NULL THEN 'Not measured'
        WHEN sla.breached_at IS NOT NULL OR sla.overrun_minutes>0 THEN 'Breached'
        WHEN sla.completed_at IS NOT NULL THEN 'Met'
        ELSE 'In progress' END sla_result
  FROM dbo.vw_SupportHub_Report_TicketBase b
  OUTER APPLY (
   SELECT TOP (1) s.id,s.target_minutes,s.accountable_minutes,s.customer_pending_minutes,
    s.millensys_pending_minutes,s.overrun_minutes,s.breached_at,s.completed_at
   FROM ticket_sla_clocks s WHERE s.ticket_id=b.id AND s.clock_type='RESOLUTION'
   ORDER BY s.id DESC
  ) sla
 )
 SELECT COUNT_BIG(1) OVER() __total_count,
  AVG(CAST(turnaround_minutes AS decimal(18,2))) OVER() __summary_avg_turnaround_minutes,
  SUM(IIF(sla_result='Breached',1,0)) OVER() __summary_sla_breached,
  ticket_number,subject,ticket_type,status_name [status],priority,client_name client,
  engineer_name engineer,assigned_team,product_name product,module_name module,environment_name environment,
  created_at,resolved_at,closed_at,completed_at,turnaround_minutes,
  CAST(turnaround_minutes/60.0 AS decimal(18,2)) turnaround_hours,closure_minutes,
  accountable_minutes sla_accountable_minutes,customer_pending_minutes,millensys_pending_minutes,
  target_minutes sla_target_minutes,sla_result
 FROM x
 WHERE (@date_from IS NULL OR created_at>=@date_from) AND (@date_to IS NULL OR created_at<DATEADD(day,1,@date_to))
  AND (@status_code IS NULL OR status_code=@status_code) AND (@ticket_type IS NULL OR ticket_type=@ticket_type)
  AND (@priority IS NULL OR priority=@priority) AND (@client_id IS NULL OR client_id=@client_id)
  AND (@engineer_id IS NULL OR engineer_id=@engineer_id) AND (@product_id IS NULL OR product_id=@product_id)
  AND (@assigned_team IS NULL OR assigned_team=@assigned_team)
  AND (@completed_only IS NULL OR @completed_only=0 OR completed_at IS NOT NULL)
  AND (@sla_result IS NULL OR sla_result=@sla_result)
  AND (@minimum_minutes IS NULL OR turnaround_minutes>=@minimum_minutes)
  AND (@maximum_minutes IS NULL OR turnaround_minutes<=@maximum_minutes)
  AND (@search IS NULL OR ticket_number LIKE '%'+@search+'%' OR subject LIKE '%'+@search+'%' OR client_name LIKE '%'+@search+'%')
 ORDER BY turnaround_minutes DESC,created_at DESC,id DESC
 OFFSET (@page-1)*@page_size ROWS FETCH NEXT @page_size ROWS ONLY;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_SupportHub_Report_EngineerWorkload
 @date_from date=NULL,@date_to date=NULL,@engineer_id bigint=NULL,@assigned_team nvarchar(150)=NULL,@include_unassigned bit=NULL,
 @page int=1,@page_size int=25,@sort_by nvarchar(120)=NULL,@sort_direction nvarchar(4)='DESC',@requesting_user_id bigint
AS BEGIN SET NOCOUNT ON; SET @page=IIF(@page<1,1,@page); SET @page_size=IIF(@page_size<1 OR @page_size>10000,25,@page_size);
 WITH x AS (SELECT engineer_id,COALESCE(engineer_name,'Unassigned') engineer,COALESCE(assigned_team,'Unassigned') team,
  COUNT_BIG(*) total_tickets,SUM(IIF(status_code='CLOSED',1,0)) closed_tickets,SUM(IIF(status_code<>'CLOSED',1,0)) open_tickets,
  SUM(IIF(priority='P1',1,0)) p1_tickets,AVG(CAST(DATEDIFF(minute,created_at,COALESCE(resolved_at,SYSUTCDATETIME())) AS decimal(18,2))) avg_age_minutes
 FROM dbo.vw_SupportHub_Report_TicketBase WHERE (@date_from IS NULL OR created_at>=@date_from) AND (@date_to IS NULL OR created_at<DATEADD(day,1,@date_to))
 AND (@engineer_id IS NULL OR engineer_id=@engineer_id) AND (@assigned_team IS NULL OR assigned_team=@assigned_team)
 AND (@include_unassigned IS NULL OR @include_unassigned=1 OR engineer_id IS NOT NULL) GROUP BY engineer_id,engineer_name,assigned_team)
 SELECT COUNT_BIG(1) OVER() __total_count,SUM(total_tickets) OVER() __summary_total_tickets,* FROM x
 ORDER BY total_tickets DESC,engineer OFFSET (@page-1)*@page_size ROWS FETCH NEXT @page_size ROWS ONLY;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_SupportHub_Report_ClientService
 @date_from date=NULL,@date_to date=NULL,@client_id bigint=NULL,@priority nvarchar(10)=NULL,@product_id bigint=NULL,@only_open bit=NULL,
 @page int=1,@page_size int=25,@sort_by nvarchar(120)=NULL,@sort_direction nvarchar(4)='DESC',@requesting_user_id bigint
AS BEGIN SET NOCOUNT ON; SET @page=IIF(@page<1,1,@page); SET @page_size=IIF(@page_size<1 OR @page_size>10000,25,@page_size);
 WITH x AS (SELECT client_id,client_name client,COUNT_BIG(*) total_tickets,SUM(IIF(status_code='CLOSED',1,0)) closed_tickets,
  SUM(IIF(status_code<>'CLOSED',1,0)) open_tickets,SUM(IIF(priority IN('P1','P2'),1,0)) high_priority,
  AVG(CAST(DATEDIFF(minute,created_at,COALESCE(resolved_at,SYSUTCDATETIME())) AS decimal(18,2))) avg_resolution_minutes
 FROM dbo.vw_SupportHub_Report_TicketBase WHERE (@date_from IS NULL OR created_at>=@date_from) AND (@date_to IS NULL OR created_at<DATEADD(day,1,@date_to))
 AND (@client_id IS NULL OR client_id=@client_id) AND (@priority IS NULL OR priority=@priority) AND (@product_id IS NULL OR product_id=@product_id)
 AND (@only_open IS NULL OR @only_open=0 OR status_code<>'CLOSED') GROUP BY client_id,client_name)
 SELECT COUNT_BIG(1) OVER() __total_count,SUM(total_tickets) OVER() __summary_total_tickets,* FROM x
 ORDER BY total_tickets DESC,client OFFSET (@page-1)*@page_size ROWS FETCH NEXT @page_size ROWS ONLY;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_SupportHub_Report_ProductQuality
 @date_from date=NULL,@date_to date=NULL,@product_id bigint=NULL,@module_id bigint=NULL,@environment_id bigint=NULL,@priority nvarchar(10)=NULL,@safety_only bit=NULL,@security_only bit=NULL,
 @page int=1,@page_size int=25,@sort_by nvarchar(120)=NULL,@sort_direction nvarchar(4)='DESC',@requesting_user_id bigint
AS BEGIN SET NOCOUNT ON; SET @page=IIF(@page<1,1,@page); SET @page_size=IIF(@page_size<1 OR @page_size>10000,25,@page_size);
 WITH x AS (SELECT COALESCE(product_name,'Unclassified') product,COALESCE(module_name,'Unclassified') module,COALESCE(environment_name,'Unspecified') environment,
  COUNT_BIG(*) total_tickets,SUM(IIF(priority='P1',1,0)) p1_tickets,SUM(IIF(patient_safety_flag=1,1,0)) safety_tickets,SUM(IIF(security_incident_flag=1,1,0)) security_tickets
 FROM dbo.vw_SupportHub_Report_TicketBase WHERE (@date_from IS NULL OR created_at>=@date_from) AND (@date_to IS NULL OR created_at<DATEADD(day,1,@date_to))
 AND (@product_id IS NULL OR product_id=@product_id) AND (@module_id IS NULL OR module_id=@module_id) AND (@environment_id IS NULL OR environment_id=@environment_id)
 AND (@priority IS NULL OR priority=@priority) AND (@safety_only IS NULL OR @safety_only=0 OR patient_safety_flag=1) AND (@security_only IS NULL OR @security_only=0 OR security_incident_flag=1)
 GROUP BY product_name,module_name,environment_name)
 SELECT COUNT_BIG(1) OVER() __total_count,SUM(total_tickets) OVER() __summary_total_tickets,* FROM x
 ORDER BY total_tickets DESC,product,module OFFSET (@page-1)*@page_size ROWS FETCH NEXT @page_size ROWS ONLY;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_SupportHub_Report_WorklogEffort
 @date_from date=NULL,@date_to date=NULL,@engineer_id bigint=NULL,@client_id bigint=NULL,@status nvarchar(20)=NULL,@minimum_minutes int=NULL,@search nvarchar(1000)=NULL,
 @page int=1,@page_size int=25,@sort_by nvarchar(120)=NULL,@sort_direction nvarchar(4)='DESC',@requesting_user_id bigint
AS BEGIN SET NOCOUNT ON; SET @page=IIF(@page<1,1,@page); SET @page_size=IIF(@page_size<1 OR @page_size>10000,25,@page_size);
 SELECT COUNT_BIG(1) OVER() __total_count,SUM(w.duration_minutes) OVER() __summary_total_minutes,b.ticket_number,b.subject,b.client_name client,
  u.full_name engineer,w.started_at,w.ended_at,w.duration_minutes,w.status,w.notes
 FROM ticket_worklogs w JOIN dbo.vw_SupportHub_Report_TicketBase b ON b.id=w.ticket_id JOIN users u ON u.id=w.user_id
 WHERE (@date_from IS NULL OR w.started_at>=@date_from) AND (@date_to IS NULL OR w.started_at<DATEADD(day,1,@date_to))
 AND (@engineer_id IS NULL OR w.user_id=@engineer_id) AND (@client_id IS NULL OR b.client_id=@client_id) AND (@status IS NULL OR w.status=@status)
 AND (@minimum_minutes IS NULL OR w.duration_minutes>=@minimum_minutes) AND (@search IS NULL OR b.ticket_number LIKE '%'+@search+'%' OR w.notes LIKE '%'+@search+'%')
 ORDER BY w.started_at DESC,w.id DESC OFFSET (@page-1)*@page_size ROWS FETCH NEXT @page_size ROWS ONLY;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_SupportHub_Report_Satisfaction
 @date_from date=NULL,@date_to date=NULL,@client_id bigint=NULL,@engineer_id bigint=NULL,@minimum_rating int=NULL,@submitted_only bit=NULL,@feedback_source nvarchar(30)=NULL,
 @page int=1,@page_size int=25,@sort_by nvarchar(120)=NULL,@sort_direction nvarchar(4)='DESC',@requesting_user_id bigint
AS BEGIN SET NOCOUNT ON; SET @page=IIF(@page<1,1,@page); SET @page_size=IIF(@page_size<1 OR @page_size>10000,25,@page_size);
 SELECT COUNT_BIG(1) OVER() __total_count,AVG(CAST(s.service_rating AS decimal(10,2))) OVER() __summary_avg_service_rating,
  b.ticket_number,b.subject,b.client_name client,u.full_name engineer,s.service_rating,s.engineer_rating,s.comments,s.feedback_source,s.submitted_at,s.invitation_sent_at
 FROM ticket_satisfaction s JOIN dbo.vw_SupportHub_Report_TicketBase b ON b.id=s.ticket_id LEFT JOIN users u ON u.id=s.engineer_user_id
 WHERE (@date_from IS NULL OR s.created_at>=@date_from) AND (@date_to IS NULL OR s.created_at<DATEADD(day,1,@date_to))
 AND (@client_id IS NULL OR b.client_id=@client_id) AND (@engineer_id IS NULL OR s.engineer_user_id=@engineer_id)
 AND (@minimum_rating IS NULL OR s.service_rating>=@minimum_rating) AND (@submitted_only IS NULL OR @submitted_only=0 OR s.submitted_at IS NOT NULL)
 AND (@feedback_source IS NULL OR s.feedback_source=@feedback_source)
 ORDER BY s.created_at DESC,s.id DESC OFFSET (@page-1)*@page_size ROWS FETCH NEXT @page_size ROWS ONLY;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_SupportHub_Report_EntitlementApprovals
 @date_from date=NULL,@date_to date=NULL,@status nvarchar(30)=NULL,@reason_code nvarchar(60)=NULL,@client_id bigint=NULL,@requested_by_user_id bigint=NULL,@overdue_only bit=NULL,
 @page int=1,@page_size int=25,@sort_by nvarchar(120)=NULL,@sort_direction nvarchar(4)='DESC',@requesting_user_id bigint
AS BEGIN SET NOCOUNT ON; SET @page=IIF(@page<1,1,@page); SET @page_size=IIF(@page_size<1 OR @page_size>10000,25,@page_size);
 SELECT COUNT_BIG(1) OVER() __total_count,SUM(IIF(a.status='PENDING',1,0)) OVER() __summary_pending,
  a.id approval_id,a.status,a.reason_code,a.requested_action,c.name client,t.ticket_number,g.name approval_group,
  ru.full_name requested_by,du.full_name decided_by,a.approval_deadline,a.created_at,a.decided_at,a.decision_comment
 FROM entitlement_approvals a JOIN clients c ON c.id=a.client_id LEFT JOIN tickets t ON t.id=a.ticket_id
 LEFT JOIN approval_groups g ON g.id=a.approval_group_id JOIN users ru ON ru.id=a.requested_by_user_id LEFT JOIN users du ON du.id=a.decided_by_user_id
 WHERE (@date_from IS NULL OR a.created_at>=@date_from) AND (@date_to IS NULL OR a.created_at<DATEADD(day,1,@date_to))
 AND (@status IS NULL OR a.status=@status) AND (@reason_code IS NULL OR a.reason_code=@reason_code) AND (@client_id IS NULL OR a.client_id=@client_id)
 AND (@requested_by_user_id IS NULL OR a.requested_by_user_id=@requested_by_user_id)
 AND (@overdue_only IS NULL OR @overdue_only=0 OR (a.status='PENDING' AND a.approval_deadline<SYSUTCDATETIME()))
 ORDER BY a.created_at DESC,a.id DESC OFFSET (@page-1)*@page_size ROWS FETCH NEXT @page_size ROWS ONLY;
END;
GO

/* Register or refresh the nine catalog entries. Numeric ID filters accept IDs from the relevant master-data screens. */
DECLARE @now datetimeoffset=SYSDATETIMEOFFSET();
DECLARE @defs TABLE(code nvarchar(80),name nvarchar(200),description nvarchar(1000),category nvarchar(80),procname nvarchar(200),filters nvarchar(max),sortcol nvarchar(120));
INSERT @defs VALUES
('TICKET_OPERATIONS','Ticket operations detail','Detailed operational ticket register with client, assignment, product and source filters.','Support','dbo.usp_SupportHub_Report_TicketOperations',
N'[{"name":"date_from","label":"Created from","type":"date","required":false,"options":[]},{"name":"date_to","label":"Created to","type":"date","required":false,"options":[]},{"name":"status_code","label":"Ticket status","type":"select","required":false,"options":[{"value":"NEW","label":"New"},{"value":"ASSIGNED","label":"Assigned"},{"value":"IN_PROGRESS","label":"In progress"},{"value":"PENDING","label":"Pending"},{"value":"RESOLVED","label":"Resolved"},{"value":"CLOSED","label":"Closed"},{"value":"CANCELLED","label":"Cancelled"}]},{"name":"priority","label":"Priority","type":"select","required":false,"options":[{"value":"P1","label":"P1 Critical"},{"value":"P2","label":"P2 High"},{"value":"P3","label":"P3 Medium"},{"value":"P4","label":"P4 Low"}]},{"name":"client_id","label":"Client ID","type":"number","required":false,"options":[]},{"name":"engineer_id","label":"Engineer ID","type":"number","required":false,"options":[]},{"name":"product_id","label":"Product ID","type":"number","required":false,"options":[]},{"name":"environment_id","label":"Environment ID","type":"number","required":false,"options":[]},{"name":"assigned_team","label":"Assigned team","type":"text","required":false,"options":[]},{"name":"source_channel","label":"Source","type":"select","required":false,"options":[{"value":"WEB","label":"Internal web"},{"value":"PORTAL","label":"Client portal"},{"value":"EMAIL","label":"Email"},{"value":"PHONE","label":"Phone"},{"value":"API","label":"API"}]},{"name":"search","label":"Ticket, subject or client","type":"text","required":false,"options":[]}]','created_at'),
('SLA_PERFORMANCE','SLA performance','Response and resolution clocks, pending time, saved time and breach outcomes.','SLA','dbo.usp_SupportHub_Report_SlaPerformance',
N'[{"name":"date_from","label":"Created from","type":"date","required":false,"options":[]},{"name":"date_to","label":"Created to","type":"date","required":false,"options":[]},{"name":"clock_type","label":"SLA measure","type":"select","required":false,"options":[{"value":"FIRST_RESPONSE","label":"First response"},{"value":"RESOLUTION","label":"Resolution"}]},{"name":"state","label":"SLA state","type":"select","required":false,"options":[{"value":"RUNNING","label":"Running"},{"value":"PAUSED","label":"Paused"},{"value":"COMPLETED","label":"Completed"},{"value":"BREACHED","label":"Breached"}]},{"name":"priority","label":"Priority","type":"select","required":false,"options":[{"value":"P1","label":"P1 Critical"},{"value":"P2","label":"P2 High"},{"value":"P3","label":"P3 Medium"},{"value":"P4","label":"P4 Low"}]},{"name":"client_id","label":"Client ID","type":"number","required":false,"options":[]},{"name":"engineer_id","label":"Engineer ID","type":"number","required":false,"options":[]},{"name":"breached","label":"Breached only","type":"boolean","required":false,"options":[]}]','due_at'),
('TICKET_TURNAROUND','Ticket turnaround time per ticket','One row per ticket with elapsed turnaround, closure duration, resolution SLA time and outcome.','SLA','dbo.usp_SupportHub_Report_TicketTurnaround',
N'[{"name":"date_from","label":"Created from","type":"date","required":false,"options":[]},{"name":"date_to","label":"Created to","type":"date","required":false,"options":[]},{"name":"status_code","label":"Ticket status","type":"select","required":false,"options":[{"value":"NEW","label":"New"},{"value":"ASSIGNED","label":"Assigned"},{"value":"IN_PROGRESS","label":"In progress"},{"value":"PENDING","label":"Pending"},{"value":"RESOLVED","label":"Resolved"},{"value":"CLOSED","label":"Closed"},{"value":"CANCELLED","label":"Cancelled"}]},{"name":"ticket_type","label":"Ticket type","type":"select","required":false,"options":[{"value":"Incident","label":"Incident"},{"value":"Service Request","label":"Service Request"}]},{"name":"priority","label":"Priority","type":"select","required":false,"options":[{"value":"P1","label":"P1 Critical"},{"value":"P2","label":"P2 High"},{"value":"P3","label":"P3 Medium"},{"value":"P4","label":"P4 Low"}]},{"name":"client_id","label":"Client ID","type":"number","required":false,"options":[]},{"name":"engineer_id","label":"Engineer ID","type":"number","required":false,"options":[]},{"name":"product_id","label":"Product ID","type":"number","required":false,"options":[]},{"name":"assigned_team","label":"Assigned team","type":"text","required":false,"options":[]},{"name":"completed_only","label":"Completed tickets only","type":"boolean","required":false,"options":[]},{"name":"sla_result","label":"Resolution SLA result","type":"select","required":false,"options":[{"value":"Met","label":"Met"},{"value":"Breached","label":"Breached"},{"value":"In progress","label":"In progress"},{"value":"Not measured","label":"Not measured"}]},{"name":"minimum_minutes","label":"Minimum turnaround (minutes)","type":"number","required":false,"options":[]},{"name":"maximum_minutes","label":"Maximum turnaround (minutes)","type":"number","required":false,"options":[]},{"name":"search","label":"Ticket, subject or client","type":"text","required":false,"options":[]}]','turnaround_minutes'),
('ENGINEER_WORKLOAD','Engineer workload','Ticket volume, open/closed mix, P1 load and average age by engineer.','Workforce','dbo.usp_SupportHub_Report_EngineerWorkload',
N'[{"name":"date_from","label":"Created from","type":"date","required":false,"options":[]},{"name":"date_to","label":"Created to","type":"date","required":false,"options":[]},{"name":"engineer_id","label":"Engineer ID","type":"number","required":false,"options":[]},{"name":"assigned_team","label":"Assigned team","type":"text","required":false,"options":[]},{"name":"include_unassigned","label":"Include unassigned","type":"boolean","required":false,"default":true,"options":[]}]','total_tickets'),
('CLIENT_SERVICE','Client service analysis','Ticket demand, high-priority volume and average resolution time by client.','Clients','dbo.usp_SupportHub_Report_ClientService',
N'[{"name":"date_from","label":"Created from","type":"date","required":false,"options":[]},{"name":"date_to","label":"Created to","type":"date","required":false,"options":[]},{"name":"client_id","label":"Client ID","type":"number","required":false,"options":[]},{"name":"priority","label":"Priority","type":"select","required":false,"options":[{"value":"P1","label":"P1 Critical"},{"value":"P2","label":"P2 High"},{"value":"P3","label":"P3 Medium"},{"value":"P4","label":"P4 Low"}]},{"name":"product_id","label":"Product ID","type":"number","required":false,"options":[]},{"name":"only_open","label":"Open tickets only","type":"boolean","required":false,"options":[]}]','total_tickets'),
('PRODUCT_QUALITY','Product quality and incidents','Ticket, safety and security volumes by product, module and environment.','Quality','dbo.usp_SupportHub_Report_ProductQuality',
N'[{"name":"date_from","label":"Created from","type":"date","required":false,"options":[]},{"name":"date_to","label":"Created to","type":"date","required":false,"options":[]},{"name":"product_id","label":"Product ID","type":"number","required":false,"options":[]},{"name":"module_id","label":"Module ID","type":"number","required":false,"options":[]},{"name":"environment_id","label":"Environment ID","type":"number","required":false,"options":[]},{"name":"priority","label":"Priority","type":"select","required":false,"options":[{"value":"P1","label":"P1 Critical"},{"value":"P2","label":"P2 High"},{"value":"P3","label":"P3 Medium"},{"value":"P4","label":"P4 Low"}]},{"name":"safety_only","label":"Patient-safety cases only","type":"boolean","required":false,"options":[]},{"name":"security_only","label":"Security cases only","type":"boolean","required":false,"options":[]}]','total_tickets'),
('WORKLOG_EFFORT','Worklog effort detail','Approved and draft effort by ticket, client and engineer.','Workforce','dbo.usp_SupportHub_Report_WorklogEffort',
N'[{"name":"date_from","label":"Work started from","type":"date","required":false,"options":[]},{"name":"date_to","label":"Work started to","type":"date","required":false,"options":[]},{"name":"engineer_id","label":"Engineer ID","type":"number","required":false,"options":[]},{"name":"client_id","label":"Client ID","type":"number","required":false,"options":[]},{"name":"status","label":"Worklog status","type":"select","required":false,"options":[{"value":"DRAFT","label":"Draft"},{"value":"SUBMITTED","label":"Submitted"},{"value":"APPROVED","label":"Approved"},{"value":"REJECTED","label":"Rejected"}]},{"name":"minimum_minutes","label":"Minimum minutes","type":"number","required":false,"options":[]},{"name":"search","label":"Ticket or work description","type":"text","required":false,"options":[]}]','started_at'),
('SATISFACTION_RESULTS','Customer satisfaction results','Service and engineer ratings with comments and response status.','Customer Success','dbo.usp_SupportHub_Report_Satisfaction',
N'[{"name":"date_from","label":"Invitation from","type":"date","required":false,"options":[]},{"name":"date_to","label":"Invitation to","type":"date","required":false,"options":[]},{"name":"client_id","label":"Client ID","type":"number","required":false,"options":[]},{"name":"engineer_id","label":"Engineer ID","type":"number","required":false,"options":[]},{"name":"minimum_rating","label":"Minimum rating","type":"select","required":false,"options":[{"value":1,"label":"1 or higher"},{"value":2,"label":"2 or higher"},{"value":3,"label":"3 or higher"},{"value":4,"label":"4 or higher"},{"value":5,"label":"5 only"}]},{"name":"submitted_only","label":"Submitted responses only","type":"boolean","required":false,"options":[]},{"name":"feedback_source","label":"Feedback source","type":"select","required":false,"options":[{"value":"CUSTOMER","label":"Customer"},{"value":"MANUAL","label":"Manual entry"}]}]','submitted_at'),
('ENTITLEMENT_APPROVALS','Entitlement approval audit','Pending, decided and overdue entitlement approvals with requester and decision context.','Approvals','dbo.usp_SupportHub_Report_EntitlementApprovals',
N'[{"name":"date_from","label":"Requested from","type":"date","required":false,"options":[]},{"name":"date_to","label":"Requested to","type":"date","required":false,"options":[]},{"name":"status","label":"Approval status","type":"select","required":false,"options":[{"value":"PENDING","label":"Pending"},{"value":"APPROVED","label":"Approved"},{"value":"REJECTED","label":"Rejected"},{"value":"EXPIRED","label":"Expired"},{"value":"REVOKED","label":"Revoked"},{"value":"CONSUMED","label":"Consumed"}]},{"name":"reason_code","label":"Reason code","type":"text","required":false,"options":[]},{"name":"client_id","label":"Client ID","type":"number","required":false,"options":[]},{"name":"requested_by_user_id","label":"Requester user ID","type":"number","required":false,"options":[]},{"name":"overdue_only","label":"Overdue pending only","type":"boolean","required":false,"options":[]}]','created_at');

MERGE dynamic_report_definitions AS target USING @defs AS src ON target.code=src.code
WHEN MATCHED THEN UPDATE SET name=src.name,description=src.description,category=src.category,stored_procedure=src.procname,
 filters_json=src.filters,default_page_size=50,default_sort_column=src.sortcol,default_sort_direction='DESC',is_active=1,updated_at=@now
WHEN NOT MATCHED THEN INSERT(code,name,description,category,stored_procedure,filters_json,default_page_size,default_sort_column,default_sort_direction,is_active,is_system,created_at,updated_at)
 VALUES(src.code,src.name,src.description,src.category,src.procname,src.filters,50,src.sortcol,'DESC',1,1,@now,@now);
GO

SELECT code,name,category,stored_procedure,filters_json FROM dynamic_report_definitions
WHERE code IN ('TICKET_OPERATIONS','SLA_PERFORMANCE','TICKET_TURNAROUND','ENGINEER_WORKLOAD','CLIENT_SERVICE','PRODUCT_QUALITY','WORKLOG_EFFORT','SATISFACTION_RESULTS','ENTITLEMENT_APPROVALS')
ORDER BY category,name;
GO
