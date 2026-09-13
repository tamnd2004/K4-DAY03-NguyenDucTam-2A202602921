import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from tools import HRStore, calculate_leave_days, create_leave_request, dispatch_tool_call, hr_query, TOOLS_SCHEMA

def test_balance_and_unknown_employee(db_path):
    assert hr_query(" nv001 ")["employee"]["available_days"]==12
    assert hr_query("NV999")["status"]=="NOT_FOUND"

@pytest.mark.parametrize("start,end,status,days",[
    ("2026-09-18","2026-09-22","SUCCESS",3),
    ("2026-09-19","2026-09-20","NO_WORKDAYS",0),
    ("2026-09-02","2026-09-02","NO_WORKDAYS",0),
    ("2026-02-30","2026-03-01","INVALID_DATE",None),
    ("2026-09-22","2026-09-21","INVALID_DATE_RANGE",None),
    ("2027-01-01","2027-01-03","INVALID_DATE_RANGE",None),
    ("2026-09-01","2026-10-01","INVALID_DATE_RANGE",None),
])
def test_calendar(start,end,status,days):
    result=calculate_leave_days(start,end)
    assert result["status"]==status
    if days is not None: assert result["days"]==days

def test_reservation_duplicate_overlap_and_persistence(db_path):
    first=create_leave_request("NV001","2026-09-21","2026-09-23","việc gia đình")
    assert first["status"]=="SUCCESS"
    assert first["request"]["status"]=="PENDING"
    assert hr_query("NV001")["employee"]["available_days"]==9
    repeated=create_leave_request("NV001","2026-09-21","2026-09-23","lý do khác")
    assert repeated["status"]=="ALREADY_EXISTS"
    assert repeated["request"]["request_id"]==first["request"]["request_id"]
    assert create_leave_request("NV001","2026-09-23","2026-09-24","việc gia đình")["status"]=="OVERLAP"
    assert len(HRStore(db_path).snapshot()["requests"])==1

@pytest.mark.parametrize("employee,start,end,reason,status",[
    ("NV003","2026-09-21","2026-09-25","du lịch","INSUFFICIENT_BALANCE"),
    ("NV999","2026-09-21","2026-09-21","du lịch","NOT_FOUND"),
    ("NV001","2026-09-10","2026-09-11","du lịch","PAST_DATE"),
    ("NV001","2026-09-21","2026-09-21"," ","INVALID_REASON"),
])
def test_invalid_writes_do_not_mutate(db_path,employee,start,end,reason,status):
    assert create_leave_request(employee,start,end,reason)["status"]==status
    assert HRStore(db_path).snapshot()["requests"]==[]

def test_concurrent_writes_cannot_overspend(db_path):
    HRStore(db_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda d:create_leave_request("NV003",d,d,"việc gia đình"),["2026-09-21","2026-09-22"]))
    assert sorted(r["status"] for r in results)==["INSUFFICIENT_BALANCE","SUCCESS"]
    assert hr_query("NV003")["employee"]["available_days"]==0

def test_strict_schema_and_unknown_tool(db_path):
    assert json.loads(dispatch_tool_call("unknown",{}))["status"]=="UNKNOWN_TOOL"
    for args in ({},{"employee_id":7},{"employee_id":"NV001","extra":True},{"employee_id":"NV001","topic":"password"}):
        assert json.loads(dispatch_tool_call("hr_query",args))["status"]=="INVALID_ARGUMENTS"
    assert all(s["parameters"]["additionalProperties"] is False for s in TOOLS_SCHEMA)

def test_real_mcp_initialize_discover_and_call(db_path):
    from mcp_client import connect_mcp
    async def run():
        async with connect_mcp(db_path) as client:
            assert {s["name"] for s in client.schemas}=={s["name"] for s in TOOLS_SCHEMA}
            assert (await client.call_tool("hr_query",{"employee_id":"NV001"}))["employee"]["available_days"]==12
            assert (await client.call_tool("hr_query",{"employee_id":"NV999"}))["status"]=="NOT_FOUND"
            assert (await client.call_tool("hr_query",{}))["status"] in {"TOOL_ERROR","INVALID_ARGUMENTS"}
    asyncio.run(run())
