"""Idempotent, non-production dataset for LocalUAT dashboard and workflow testing."""
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.clients.models import (
    Branch,
    Client,
    ClientStatus,
    Contact,
    Product,
    ProductModule,
    ServiceCatalogItem,
    SupportTeam,
    SupportTeamMember,
    TicketCategory,
)
from app.modules.contracts.models import (
    BusinessCalendar,
    Contract,
    ContractCoverage,
    ContractType,
    SlaPolicy,
    SlaTarget,
    TicketSlaClock,
)
from app.modules.iam.models import Profile, User, UserProfile
from app.modules.iam.security import hash_password
from app.modules.internal_operations.models import InternalOperation, InternalOperationAssignee
from app.modules.project_handovers.models import HandoverProduct, HandoverRecipient, ProjectHandover
from app.modules.shifts.models import Shift, ShiftType
from app.modules.tickets.models import (
    RootCause,
    Ticket,
    TicketAssignmentHistory,
    TicketRootCause,
    TicketSatisfaction,
    TicketStatus,
    TicketType,
)

NOW=datetime.now(UTC); PASSWORD="LocalUAT!2026"

def one(db, model, **lookup): return db.scalar(select(model).filter_by(**lookup))
def ensure(db, model, lookup, **values):
    item=one(db,model,**lookup)
    if not item: item=model(**lookup,**values); db.add(item); db.flush()
    return item

def main():
  with SessionLocal() as db:
    admin=one(db,User,username_normalized="uatadmin")
    active=one(db,ClientStatus,code="ACTIVE")
    profiles={code:one(db,Profile,code=code) for code in ("L1_SUPPORT","L2_SUPPORT","L3_SUPPORT","SUPPORT_MANAGER","TOP_MANAGEMENT")}
    users=[]
    for i,(code,name,department) in enumerate((("l1.demo","Omar L1","Support"),("l2.demo","Sara L2","Applications"),("l3.demo","Mina L3","Engineering"),("manager.demo","Nadia Support Manager","Support"),("executive.demo","Khaled Executive","Management")),1):
      user=ensure(db,User,{"username_normalized":code},full_name=name,username=code,email=f"{code}@local.test",email_normalized=f"{code}@local.test",employee_code=f"UAT{i:03}",department=department,job_title=profiles[list(profiles)[i-1]].name,user_type="EMPLOYEE",password_hash=hash_password(PASSWORD),is_active=True,require_password_change=False,last_seen_at=NOW)
      if not one(db,UserProfile,user_id=user.id,profile_id=profiles[list(profiles)[i-1]].id): db.add(UserProfile(user_id=user.id,profile_id=profiles[list(profiles)[i-1]].id,is_primary=True,is_active=True,assigned_by_user_id=admin.id,assignment_reason="Local UAT demo"))
      users.append(user)
    team=ensure(db,SupportTeam,{"code":"UAT_SUPPORT"},name="UAT Support Team",description="Demo support team",leader_user_id=users[3].id,is_active=True)
    for user in users[:4]:
      if not one(db,SupportTeamMember,team_id=team.id,user_id=user.id): db.add(SupportTeamMember(team_id=team.id,user_id=user.id))
    clients=[]
    for code,name,country,zone in (("ALFA_UAT","Alfascan Demo","Egypt","Cairo"),("NILE_UAT","Nile Healthcare Demo","Egypt","Alexandria"),("GULF_UAT","Gulf Medical Demo","Saudi Arabia","Riyadh")):
      client=ensure(db,Client,{"code":code},name=name,status_id=active.id,timezone="Africa/Cairo",country=country,zone=zone,email=f"support@{code.lower()}.test",address=f"{zone}, {country}",is_active=True)
      branch=ensure(db,Branch,{"client_id":client.id,"code":"HQ"},name=f"{name} HQ",timezone="Africa/Cairo",country=country,zone=zone,address=f"HQ, {zone}",is_active=True)
      ensure(db,Contact,{"client_id":client.id,"email":f"requester@{code.lower()}.test"},branch_id=branch.id,full_name=f"{name} Requester",is_primary=True,is_active=True)
      clients.append((client,branch))
    products=[]
    for code,name,modules in (("HIS_UAT","HIS Demo",("Radiology","Laboratory")),("ERP_UAT","ERP Demo",("AP","HR"))):
      product=ensure(db,Product,{"code":code},name=name,is_active=True); mod=[]
      for module in modules: mod.append(ensure(db,ProductModule,{"product_id":product.id,"code":module.upper()},name=module,is_active=True))
      products.append((product,mod))
    services=[ensure(db,ServiceCatalogItem,{"code":code},name=name,is_active=True) for code,name in (("SUPPORT_UAT","Support Activity"),("BUG_UAT","Bug Fix"),("MOD_UAT","Modification"))]
    category=ensure(db,TicketCategory,{"code":"SOFTWARE_UAT"},name="Software UAT",is_active=True)
    roots=[ensure(db,RootCause,{"code":code},name=name,is_active=True) for code,name in (("CONFIG_UAT","Configuration error"),("DATA_UAT","Data quality"),("DEFECT_UAT","Software defect"))]
    calendar=one(db,BusinessCalendar,code="24X7") or db.scalar(select(BusinessCalendar).limit(1)); ctype=one(db,ContractType,code="SUPPORT"); ticket_type=db.scalar(select(TicketType).where(TicketType.is_active.in_([True]))); statuses={x.code:x for x in db.scalars(select(TicketStatus))}
    contracts=[]
    for index,(client,branch) in enumerate(clients):
      ensure(db,Contract,{"contract_number":f"UAT-{index+1}-2025"},client_id=client.id,contract_type_id=ctype.id,name=f"{client.name} Support 2025",status="EXPIRED",start_date=date(2025,1,1),end_date=date(2025,12,31),timezone="Africa/Cairo",calendar_id=calendar.id,has_sla=True,is_active=False)
      contract=ensure(db,Contract,{"contract_number":f"UAT-{index+1}-2026"},client_id=client.id,contract_type_id=ctype.id,name=f"{client.name} Support 2026",status="ACTIVE",start_date=date(2026,1,1),end_date=date(2026,12,31),renewal_notice_date=date(2026,11,1),timezone="Africa/Cairo",calendar_id=calendar.id,has_sla=True,is_active=True)
      policy=ensure(db,SlaPolicy,{"code":f"UAT-SLA-{index+1}"},name=f"{client.name} SLA",contract_id=contract.id,calendar_id=calendar.id,is_active=True)
      contract.sla_policy_id=policy.id
      for pidx,(product,modules) in enumerate(products):
        service=services[(index+pidx)%len(services)]; ensure(db,ContractCoverage,{"contract_id":contract.id,"product_id":product.id,"product_module_id":modules[0].id,"branch_id":branch.id,"service_id":service.id,"ticket_type_id":ticket_type.id},is_covered=True)
        for priority,response,resolution in (("P1",15,60),("P2",30,120),("P3",45,240),("P4",60,480)):
          ensure(db,SlaTarget,{"policy_id":policy.id,"context_key":f"P{product.id}:M{modules[0].id}:S{service.id}:PR{priority}"},product_id=product.id,product_module_id=modules[0].id,service_id=service.id,priority=priority,is_fallback=False,first_response_minutes=response,resolution_minutes=resolution,warning_percent=75)
      contracts.append((contract,policy))
    for i in range(30):
      client,branch=clients[i%3]; product,modules=products[i%2]; service=services[(i%3)]; contract,policy=contracts[i%3]; engineer=users[i%3]
      created=NOW-timedelta(days=(i*7)%330,hours=i%9); state=("CLOSED" if i<18 else "RESOLVED" if i<22 else "IN_PROGRESS" if i<27 else "NEW"); completed=created+timedelta(minutes=30+(i%6)*35) if state in {"CLOSED","RESOLVED"} else None
      ticket=ensure(db,Ticket,{"ticket_number":f"UAT-{i+1:05}"},ticket_type_id=ticket_type.id,client_id=client.id,branch_id=branch.id,requester_contact_id=one(db,Contact,client_id=client.id).id,created_by_user_id=admin.id,status_id=statuses[state].id,contract_id=contract.id,entitlement_status="COVERED",assigned_user_id=engineer.id,assigned_team=team.name,product_id=product.id,product_module_id=modules[0].id,service_id=service.id,category_id=category.id,category=category.name,source_channel="WEB",impact="CRITICAL" if i%9==0 else "MEDIUM",urgency="HIGH" if i%5==0 else "MEDIUM",priority=("P1","P2","P3","P4")[i%4],subject=f"UAT demo issue {i+1}",description="Generated LocalUAT ticket for analytics and workflow testing.",progress_started_at=created+timedelta(minutes=10),resolved_at=completed,closed_at=completed if state=="CLOSED" else None,resolution_summary="Resolved in UAT" if completed else None,last_activity_at=completed or created,created_at=created)
      ensure(db,TicketAssignmentHistory,{"ticket_id":ticket.id,"assigned_user_id":engineer.id,"created_at":created+timedelta(minutes=5)},assigned_team=team.name,assigned_by_user_id=admin.id,reason="UAT assignment")
      root=roots[i%len(roots)]
      if completed and not one(db,TicketRootCause,ticket_id=ticket.id,root_cause_id=root.id): db.add(TicketRootCause(ticket_id=ticket.id,root_cause_id=root.id,created_by_user_id=engineer.id,created_at=completed))
      target=one(db,SlaTarget,policy_id=policy.id,product_id=product.id,service_id=service.id,priority=ticket.priority)
      if target: ensure(db,TicketSlaClock,{"ticket_id":ticket.id,"clock_type":"RESOLUTION"},contract_id=contract.id,policy_id=policy.id,target_id=target.id,calendar_id=calendar.id,policy_version=1,match_reason="SERVICE_PRIORITY",target_minutes=target.resolution_minutes,warning_percent=75,started_at=created+timedelta(minutes=5),due_at=created+timedelta(minutes=target.resolution_minutes),state="COMPLETED" if completed else "RUNNING",completed_at=completed,calculation_version="2.0")
      if state=="CLOSED" and i<6: ensure(db,TicketSatisfaction,{"ticket_id":ticket.id},engineer_user_id=engineer.id,recipient_email=one(db,Contact,client_id=client.id).email,token_hash=f"{i+1:064x}",expires_at=NOW+timedelta(days=30),service_rating=3+i%3,engineer_rating=4+i%2,comments="Local UAT feedback",submitted_at=completed,invitation_sent_at=completed)
    for i in range(8):
      client,_=clients[i%3]; handover=ensure(db,ProjectHandover,{"project_number":f"UAT-PROJ-{i+1:03}"},project_name=f"Demo delivery project {i+1}",client_id=client.id,delivered_by_user_id=users[2].id,project_manager_user_id=users[3].id,warranty_months=12,warranty_start_date=date.today()-timedelta(days=i*20),acceptance_date=date.today()-timedelta(days=i*20),current_status="DELIVERED" if i<6 else "IN_PROGRESS",created_at=NOW-timedelta(days=i*25))
      if not one(db,HandoverRecipient,handover_id=handover.id,user_id=users[0].id): db.add(HandoverRecipient(handover_id=handover.id,user_id=users[0].id,accepted=i<6))
      if not one(db,HandoverProduct,handover_id=handover.id,product_id=products[i%2][0].id): db.add(HandoverProduct(handover_id=handover.id,product_id=products[i%2][0].id,product_module_id=products[i%2][1][0].id,delivery_status="DELIVERED" if i<6 else "IN_PROGRESS",delivery_percent=100 if i<6 else 65))
    shift_type=one(db,ShiftType,code="ON_CALL") or ensure(db,ShiftType,{"code":"UAT_ON_CALL"},name="UAT On Call",color="#7c3aed",is_on_call=True,is_active=True)
    for i,user in enumerate(users[:4]): ensure(db,Shift,{"user_id":user.id,"starts_at":NOW+timedelta(days=i)},shift_type_id=shift_type.id,team=team.name,on_call_role=f"L{i+1}",work_location="OFFICE",ends_at=NOW+timedelta(days=i,hours=8),status="PUBLISHED",created_by_user_id=admin.id)
    for i in range(6):
      client,_=clients[i%3]; op=ensure(db,InternalOperation,{"title":f"UAT client field visit {i+1}","starts_at":NOW-timedelta(days=i*12)},operation_type="FIELD_VISIT",status="COMPLETED",ends_at=NOW-timedelta(days=i*12)+timedelta(hours=4),location=client.zone,client_id=client.id,client_name=client.name,created_by_user_id=admin.id)
      if not one(db,InternalOperationAssignee,operation_id=op.id,user_id=users[i%3].id): db.add(InternalOperationAssignee(operation_id=op.id,user_id=users[i%3].id))
    db.commit(); print("LocalUAT demo data ready: 3 clients, 5 users, 30 tickets, 8 projects, contracts/SLA/shifts/visits/ratings.")

if __name__ == "__main__": main()
