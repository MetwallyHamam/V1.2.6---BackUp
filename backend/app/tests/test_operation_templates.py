from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.iam.models import Department, User


def test_operation_template_crud_and_month_application(client:TestClient,admin_headers:dict[str,str],database:Session)->None:
    department=Department(code="OPS_TEMPLATE",name="Operation Template Department",is_active=True)
    actor=database.scalar(select(User).where(User.username=="admin"));actor.department=department.name
    database.add(department);database.commit()
    created=client.post("/api/v1/internal-operations/templates",headers=admin_headers,json={"name":"Weekly support meeting","operation_type":"MEETING","department_id":department.id,"start_time":"09:00:00","end_time":"10:00:00","default_week_numbers":[1,2,3,4],"default_weekdays":[6],"week_start_day":6,"location":"Teams"})
    assert created.status_code==201,created.text
    assert created.json()["code"]=="WEEKLY-SUPPORT-MEETING-001"
    assert created.json()["default_weekdays"]==[6]
    edited=client.patch(f"/api/v1/internal-operations/templates/{created.json()['id']}",headers=admin_headers,json={"name":"Weekly support meeting","operation_type":"MEETING","department_id":department.id,"start_time":"10:00:00","end_time":"11:00:00","default_week_numbers":[1,3],"default_weekdays":[6],"week_start_day":6,"location":"Teams"})
    assert edited.status_code==200 and edited.json()["default_week_numbers"]==[1,3]
    applied=client.post(f"/api/v1/internal-operations/templates/{created.json()['id']}/apply-month",headers=admin_headers,json={"month":"2026-09-01","user_ids":[actor.id]})
    assert applied.status_code==200,applied.text
    assert applied.json()["dates"]==["2026-09-06","2026-09-20"] and applied.json()["created"]==2
    rows=client.get("/api/v1/internal-operations?date_from=2026-09-01&date_to=2026-09-30",headers=admin_headers)
    assert rows.status_code==200 and len(rows.json())==2
    assert client.delete(f"/api/v1/internal-operations/templates/{created.json()['id']}",headers=admin_headers).status_code==204


def test_outdoor_visit_template_is_available_but_requires_governed_client_application(client:TestClient,admin_headers:dict[str,str])->None:
    response=client.post("/api/v1/internal-operations/templates",headers=admin_headers,json={"name":"Governed outdoor schedule","operation_type":"OUTDOOR_VISIT","start_time":"09:00:00","end_time":"10:00:00"})
    assert response.status_code==201,response.text
    engineer=client.get("/api/v1/internal-operations/engineers",headers=admin_headers).json()[0]
    applied=client.post(f"/api/v1/internal-operations/templates/{response.json()['id']}/apply-month",headers=admin_headers,json={"month":"2026-09-01","user_ids":[engineer["id"]]})
    assert applied.status_code==409
    assert applied.json()["error"]["code"]=="INTERNAL_OPERATION_CLIENT_REQUIRED"


def test_date_range_application_honors_week_and_weekday_filters(client:TestClient,admin_headers:dict[str,str])->None:
    template=client.post("/api/v1/internal-operations/templates",headers=admin_headers,json={"name":"Filtered date range","operation_type":"MEETING","start_time":"09:00:00","end_time":"10:00:00","default_week_numbers":[1,2,3,4],"default_weekdays":[0],"week_start_day":6})
    assert template.status_code==201,template.text
    engineer=client.get("/api/v1/internal-operations/engineers",headers=admin_headers).json()[0]
    applied=client.post(f"/api/v1/internal-operations/templates/{template.json()['id']}/apply-month",headers=admin_headers,json={"selection_mode":"DATE_RANGE","date_from":"2026-09-01","date_to":"2026-09-30","week_numbers":[2,4],"weekdays":[0],"week_start_day":6,"user_ids":[engineer["id"]]})
    assert applied.status_code==200,applied.text
    assert applied.json()["dates"]==["2026-09-07","2026-09-21"]


def test_operation_types_can_be_edited_and_only_unused_types_deleted(client:TestClient,admin_headers:dict[str,str])->None:
    created=client.post("/api/v1/internal-operations/types",headers=admin_headers,json={"name":"Training session","description":"Internal training","color":"#336699","supports_client":False})
    assert created.status_code==201,created.text
    assert created.json()["code"]=="TRAINING_SESSION"
    edited=client.patch(f"/api/v1/internal-operations/types/{created.json()['id']}",headers=admin_headers,json={"name":"Technical training","description":"Updated name","color":"#336699","supports_client":False})
    assert edited.status_code==200 and edited.json()["code"]=="TRAINING_SESSION" and edited.json()["name"]=="Technical training"
    assert client.delete(f"/api/v1/internal-operations/types/{created.json()['id']}",headers=admin_headers).status_code==204


def test_operation_lifecycle_and_schedule_use_optimistic_concurrency(client:TestClient,admin_headers:dict[str,str])->None:
    engineer=client.get("/api/v1/internal-operations/engineers",headers=admin_headers).json()[0]
    created=client.post("/api/v1/internal-operations",headers=admin_headers,json={"title":"Lifecycle governed operation","operation_type":"MEETING","status":"PLANNED","starts_at":"2026-10-01T09:00:00+00:00","ends_at":"2026-10-01T10:00:00+00:00","timezone":"Africa/Cairo","assignee_user_ids":[engineer["id"]]})
    assert created.status_code==201,created.text
    assert created.json()["status"]=="PLANNED" and created.json()["version"]==1
    invalid=client.post(f"/api/v1/internal-operations/{created.json()['id']}/transition",headers=admin_headers,json={"to_status":"COMPLETED","expected_version":1,"reason":"Cannot skip the governed lifecycle."})
    assert invalid.status_code==409
    scheduled=client.post(f"/api/v1/internal-operations/{created.json()['id']}/transition",headers=admin_headers,json={"to_status":"SCHEDULED","expected_version":1,"reason":"Planning is complete and accepted."})
    assert scheduled.status_code==200 and scheduled.json()["version"]==2
    stale=client.patch(f"/api/v1/internal-operations/{created.json()['id']}/schedule",headers=admin_headers,json={"starts_at":"2026-10-01T11:00:00+00:00","ends_at":"2026-10-01T12:00:00+00:00","timezone":"Africa/Cairo","expected_version":1,"reason":"Attempt with stale calendar data."})
    assert stale.status_code==409
    moved=client.patch(f"/api/v1/internal-operations/{created.json()['id']}/schedule",headers=admin_headers,json={"starts_at":"2026-10-01T11:00:00+00:00","ends_at":"2026-10-01T12:00:00+00:00","timezone":"Africa/Cairo","expected_version":2,"reason":"Move to the agreed calendar slot."})
    assert moved.status_code==200 and moved.json()["version"]==3


def test_smart_operation_generator_previews_recurrence_and_applies_a_durable_batch(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    payload = {
        "title": "Generated weekly meeting",
        "operation_type": "MEETING",
        "start_time": "09:00:00",
        "end_time": "10:30:00",
        "recurrence": {
            "frequency": "WEEKLY",
            "date_from": "2032-03-01",
            "date_to": "2032-03-15",
            "weekdays": [0],
        },
        "timezone": "Africa/Cairo",
        "required_headcount": 1,
        "assignment_strategy": "AUTO_BALANCE",
        "status": "PLANNED",
    }
    preview = client.post("/api/v1/internal-operations/generator/preview", headers=admin_headers, json=payload)
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["slot_count"] == 3
    assert body["required_positions"] == 3
    assert body["assigned_positions"] == 3
    assert body["entitlement_issue_count"] == 0
    assert all(row["entitlement_status"] == "NOT_REQUIRED" for row in body["slots"])

    applied = client.post(
        "/api/v1/internal-operations/generator/apply",
        headers=admin_headers,
        json={"request": payload, "preview_hash": body["preview_hash"]},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["created_operations"] == 3
    assert applied.json()["created_visit_occurrences"] == 0
    rows = client.get(
        "/api/v1/internal-operations?date_from=2032-03-01&date_to=2032-03-15",
        headers=admin_headers,
    )
    assert rows.status_code == 200
    assert len([row for row in rows.json() if row["title"] == payload["title"]]) == 3


def test_smart_operation_generator_rejects_a_stale_preview(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    engineer = client.get("/api/v1/internal-operations/engineers", headers=admin_headers).json()[0]
    payload = {
        "title": "Stale preview meeting",
        "operation_type": "MEETING",
        "start_time": "09:00:00",
        "end_time": "10:00:00",
        "recurrence": {"frequency": "ONCE", "date_from": "2033-04-04", "date_to": "2033-04-04"},
        "timezone": "UTC",
        "required_headcount": 1,
        "assignment_strategy": "FIXED",
        "fixed_user_ids": [engineer["id"]],
    }
    preview = client.post("/api/v1/internal-operations/generator/preview", headers=admin_headers, json=payload)
    assert preview.status_code == 200, preview.text
    competing = client.post(
        "/api/v1/internal-operations",
        headers=admin_headers,
        json={
            "title": "Competing operation",
            "operation_type": "MEETING",
            "starts_at": "2033-04-04T09:00:00+00:00",
            "ends_at": "2033-04-04T10:00:00+00:00",
            "assignee_user_ids": [engineer["id"]],
        },
    )
    assert competing.status_code == 201, competing.text
    applied = client.post(
        "/api/v1/internal-operations/generator/apply",
        headers=admin_headers,
        json={"request": payload, "preview_hash": preview.json()["preview_hash"]},
    )
    assert applied.status_code == 409
    assert applied.json()["error"]["code"] == "SCHEDULE_PREVIEW_CHANGED"
