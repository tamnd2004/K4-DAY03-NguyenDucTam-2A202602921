"""PeopleOps tools: fictional HR policies, real transactional SQLite persistence."""
from __future__ import annotations
import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
DEMO_TODAY = date(2026, 9, 13)
POLICIES = {
    "source": "PeopleOps · Sổ tay nhân sự DEMO v1.0",
    "disclaimer": "Dữ liệu giả lập cho bài lab, không phải chính sách chính thức của VinFast.",
    "annual_leave": "Hạn mức theo hồ sơ nhân viên. Ngày phép tính từ thứ Hai đến thứ Sáu; trừ ngày đóng cửa trong lịch demo. Đơn chờ duyệt giữ chỗ quỹ phép, chưa phải đã được duyệt.",
    "approval": "Quản lý trực tiếp xét duyệt. Agent chỉ tạo đơn PENDING, không phê duyệt hoặc gửi email.",
    "insurance": "Nhân viên chính thức trong bộ dữ liệu demo có gói sức khỏe nội bộ Care Plus; liên hệ hr@peopleops.example để nhận biểu mẫu quyền lợi.",
    "calendar": "Ngày tham chiếu lab: 13/09/2026. Chỉ nhận đơn trong năm phép 2026, tối đa 30 ngày lịch/đơn. Lịch đóng cửa demo: 01/01, 30/04, 01/05, 02/09; không đại diện lịch nghỉ lễ pháp định đầy đủ.",
}
HOLIDAYS = {"2026-01-01", "2026-04-30", "2026-05-01", "2026-09-02"}
EMPLOYEES = [
    ("NV001", "Nguyễn Đức Tâm", "Engineering", "AI Engineer", "Trần Minh Anh", 18, 6),
    ("NV002", "Lê Thu Hà", "People & Culture", "HR Specialist", "Phạm Hoàng Nam", 16, 8),
    ("NV003", "Trần Quốc Bảo", "Operations", "Operations Executive", "Phạm Hoàng Nam", 12, 11),
]

class HRStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.getenv("HR_DB_PATH", ROOT / "data" / "peopleops.db")).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS employees (
                    employee_id TEXT PRIMARY KEY, full_name TEXT, department TEXT,
                    position TEXT, manager TEXT, allowance INTEGER, used INTEGER);
                CREATE TABLE IF NOT EXISTS leave_requests (
                    request_id TEXT PRIMARY KEY, employee_id TEXT NOT NULL REFERENCES employees(employee_id),
                    start_date TEXT NOT NULL, end_date TEXT NOT NULL, days INTEGER NOT NULL CHECK(days>0),
                    reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING', created_at TEXT NOT NULL,
                    UNIQUE(employee_id,start_date,end_date));
            """)
            db.executemany("INSERT OR IGNORE INTO employees VALUES (?,?,?,?,?,?,?)", EMPLOYEES)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def employee(db, employee_id):
        row = db.execute("SELECT * FROM employees WHERE employee_id=?", (employee_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["pending_days"] = db.execute("SELECT COALESCE(SUM(days),0) FROM leave_requests WHERE employee_id=? AND status='PENDING'", (employee_id,)).fetchone()[0]
        result["available_days"] = result["allowance"] - result["used"] - result["pending_days"]
        return result

    def snapshot(self):
        with self.connection() as db:
            employees = [self.employee(db, e[0]) for e in EMPLOYEES]
            requests = [dict(r) for r in db.execute("SELECT * FROM leave_requests ORDER BY created_at DESC")]
        return {"employees": employees, "requests": requests, "policies": POLICIES, "demo_date": DEMO_TODAY.isoformat()}

def hr_query(employee_id: str, topic: Literal["balance", "profile", "policy"] = "balance") -> dict:
    """Tra cứu hồ sơ, quỹ phép khả dụng hoặc chính sách demo. Luôn dùng trước khi tạo đơn. employee_id ví dụ NV001."""
    with HRStore().connection() as db:
        employee = HRStore.employee(db, employee_id.strip().upper())
    if not employee:
        return {"status": "NOT_FOUND", "message": "Không tìm thấy mã nhân viên. Vui lòng kiểm tra lại mã."}
    return {"status": "SUCCESS", "employee": employee, "policies": POLICIES if topic == "policy" else None, "source": "SQLite · dữ liệu nhân sự demo"}

def calculate_leave_days(start_date: str, end_date: str) -> dict:
    """Tính ngày làm việc trong lịch DEMO 2026, loại cuối tuần và ngày đóng cửa. Input ISO YYYY-MM-DD; tối đa 30 ngày lịch. Dùng trước khi tạo đơn."""
    try:
        if not all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) for v in (start_date, end_date)):
            raise ValueError
        start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    except (ValueError, TypeError):
        return {"status": "INVALID_DATE", "message": "Ngày phải hợp lệ, định dạng YYYY-MM-DD."}
    if start > end or start.year != 2026 or end.year != 2026 or (end-start).days >= 30:
        return {"status": "INVALID_DATE_RANGE", "message": "Chọn khoảng tăng dần trong năm 2026, tối đa 30 ngày lịch."}
    calendar = [start + timedelta(days=i) for i in range((end-start).days+1)]
    workdays = [d.isoformat() for d in calendar if d.weekday()<5 and d.isoformat() not in HOLIDAYS]
    return {"status": "SUCCESS" if workdays else "NO_WORKDAYS", "start_date": start_date,
            "end_date": end_date, "days": len(workdays), "workdays": workdays,
            "excluded_days": len(calendar)-len(workdays), "calendar": "Lịch demo 2026"}

def create_leave_request(employee_id: str, start_date: str, end_date: str, reason: str) -> dict:
    """TẠO đơn nghỉ PENDING khi người dùng yêu cầu rõ ràng và cung cấp đủ ngày, lý do. Phải tra hr_query và calculate_leave_days trước. Tự kiểm tra số dư, ngày quá khứ, trùng/chéo đơn. Không duyệt, không gửi email."""
    employee_id = employee_id.strip().upper()
    if not isinstance(reason, str) or not 3 <= len(reason.strip()) <= 500:
        return {"status": "INVALID_REASON", "message": "Cần lý do từ 3 đến 500 ký tự do người dùng cung cấp."}
    period = calculate_leave_days(start_date, end_date)
    if period["status"] != "SUCCESS":
        return period
    if date.fromisoformat(start_date) < DEMO_TODAY:
        return {"status": "PAST_DATE", "message": "Ngày bắt đầu phải từ 13/09/2026 (ngày tham chiếu lab)."}
    with HRStore().connection() as db:
        db.execute("BEGIN IMMEDIATE")
        employee = HRStore.employee(db, employee_id)
        if not employee:
            return {"status": "NOT_FOUND", "message": "Không tìm thấy mã nhân viên; chưa tạo đơn."}
        existing = db.execute("SELECT * FROM leave_requests WHERE employee_id=? AND start_date=? AND end_date=?", (employee_id,start_date,end_date)).fetchone()
        if existing:
            return {"status": "ALREADY_EXISTS", "request": dict(existing), "message": "Đơn cho khoảng ngày này đã tồn tại; không tạo thêm."}
        overlap = db.execute("SELECT request_id FROM leave_requests WHERE employee_id=? AND status IN ('PENDING','APPROVED') AND start_date<=? AND end_date>=?", (employee_id,end_date,start_date)).fetchone()
        if overlap:
            return {"status": "OVERLAP", "request_id": overlap[0], "message": "Khoảng nghỉ trùng với đơn hiện có; chưa tạo đơn mới."}
        if period["days"] > employee["available_days"]:
            return {"status": "INSUFFICIENT_BALANCE", "requested_days": period["days"], "available_days": employee["available_days"], "message": "Không đủ quỹ phép khả dụng; chưa tạo đơn."}
        request = {"request_id": "LV-"+uuid.uuid4().hex[:8].upper(), "employee_id": employee_id,
                   "start_date": start_date, "end_date": end_date, "days": period["days"], "reason": reason.strip(),
                   "status": "PENDING", "created_at": datetime.now(timezone.utc).isoformat()}
        db.execute("INSERT INTO leave_requests VALUES (:request_id,:employee_id,:start_date,:end_date,:days,:reason,:status,:created_at)", request)
        return {"status": "SUCCESS", "request": request, "manager": employee["manager"], "available_days": employee["available_days"]-period["days"], "message": "Đã tạo đơn chờ quản lý duyệt và giữ chỗ quỹ phép. Chưa được phê duyệt."}

def list_leave_requests(employee_id: str) -> dict:
    """Tra cứu danh sách và trạng thái đơn nghỉ phép của nhân viên, bao gồm mã đơn và ngày nghỉ."""
    employee_id = employee_id.strip().upper()
    with HRStore().connection() as db:
        if not HRStore.employee(db, employee_id):
            return {"status": "NOT_FOUND", "message": "Không tìm thấy mã nhân viên."}
        rows = db.execute("SELECT * FROM leave_requests WHERE employee_id=? ORDER BY created_at DESC", (employee_id,))
        return {"status": "SUCCESS", "employee_id": employee_id, "requests": [dict(r) for r in rows]}

TOOL_ROUTER = {f.__name__: f for f in (hr_query,calculate_leave_days,create_leave_request,list_leave_requests)}

def tool_schemas():
    from pydantic import TypeAdapter
    result = []
    for name, function in TOOL_ROUTER.items():
        schema = TypeAdapter(function).json_schema()
        schema["additionalProperties"] = False
        result.append({"name": name, "description": function.__doc__, "parameters": schema})
    return result

TOOLS_SCHEMA = tool_schemas()

def dispatch_tool_call(tool_name: str, arguments: dict) -> str:
    from pydantic import ValidationError, validate_call
    if tool_name not in TOOL_ROUTER:
        result = {"status": "UNKNOWN_TOOL", "message": "Công cụ không tồn tại."}
    else:
        try:
            result = validate_call(TOOL_ROUTER[tool_name], config={"extra":"forbid", "strict":True})(**arguments)
        except (ValidationError,TypeError,ValueError):
            result = {"status": "INVALID_ARGUMENTS", "message": "Tham số không đúng schema; kiểm tra tên và kiểu dữ liệu."}
    return json.dumps(result, ensure_ascii=False)
