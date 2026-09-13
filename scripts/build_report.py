"""Build the submission report from recorded evidence; never invent results."""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read_json(name):
    path=ROOT/name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}

def main():
    live=read_json('docs/trace_waterfall.json')
    offline=read_json('docs/trace_waterfall_offline.json')
    browser=read_json('docs/browser-results.json')
    cases=read_json('config/test_cases.json')
    xml=ROOT/'docs/test-results.xml'
    unit=ET.parse(xml).getroot().find('testsuite') if xml.exists() else None
    unit_total=int(unit.get('tests','0')) if unit is not None else 0
    unit_fail=int(unit.get('failures','0'))+int(unit.get('errors','0')) if unit is not None else 0
    by_case={r['test_case']:r for r in live.get('runs',[])}
    by_eval={e['id']:e for e in live.get('evaluations',[])}
    model=', '.join(sorted({r['model'] for r in live.get('runs',[])})) or 'Chưa có bằng chứng API'
    successful=[r for r in live.get('runs',[]) if r['status']=='completed']
    example=next((r for r in successful if r['test_case']=='TC04'),next(iter(successful),None))
    excerpt=[]
    if example:
        fields={'step','action_type','summary','tool_name','arguments','observation','output','latency_ms'}
        excerpt=[{k:v for k,v in e.items() if k in fields} for e in example['trace'] if e['action_type'] in {'THOUGHT','ACTION','OBSERVATION','FINAL_ANSWER'}]
    rows=[]
    for case in cases:
        run=by_case.get(case['id'],{})
        evaluation=by_eval.get(case['id'],{})
        tools=' → '.join(e['tool_name'] for e in run.get('trace',[]) if e['action_type']=='ACTION') or 'Không gọi tool'
        rows.append(f"| {case['id']} | {case['type']} | {'PASS' if evaluation.get('passed') else 'CHƯA ĐẠT'} | {tools} |")
    all_live=live.get('passed',0)==len(cases) and all(r.get('live') and r.get('status')=='completed' for r in live.get('runs',[]))
    tool_count=sum(r.get('tool_calls',0) for r in live.get('runs',[]))
    report=f"""# Báo cáo nghiệm thu Day 03 — PeopleOps HR Assistant

**Học viên:** Nguyễn Đức Tâm · **Mã học viên:** 2A202602921
**Chủ đề:** 2.1 — Trợ lý nhân sự (HR & Operations)
**Repository:** https://github.com/tamnd2004/K4-DAY03-NguyenDucTam-2A202602921

## 1. Agentic Fit & Tool Specs — 25%

Nhân viên muốn nghỉ phép phải tra số dư, tính ngày làm việc, kiểm tra điều kiện rồi tạo đơn. Chatbot chỉ trả văn bản không thể biết số dư hiện tại hoặc ghi đơn. PeopleOps dùng ReAct để nối các bước đọc/ghi và đổi nhánh theo dữ liệu nhận được. Hồ sơ và chính sách trong bài là dữ liệu hư cấu, không phải chính sách chính thức của VinFast.

| Tiêu chí | Điểm | Giải trình |
| --- | ---: | --- |
| Multi-step Reasoning | 5/5 | Tra hồ sơ → tính ngày → so sánh quỹ phép → tạo đơn → xác nhận mã đơn. |
| Tool Interaction | 5/5 | Cần đọc và ghi SQLite qua MCP; LLM không có dữ liệu này trong kiến thức sẵn có. |
| Dynamic Decision | 5/5 | Thiếu phép, sai mã, trùng đơn hoặc thiếu thông tin dẫn tới nhánh xử lý khác nhau. |
| Long Horizon Goal | 2/5 | Mục tiêu ngắn trong phiên; chưa tự theo dõi duyệt đơn hoặc nhắc việc dài hạn. |
| **Tổng** | **17/20** | Phù hợp ReAct; chưa cần Autonomous Agent dài hạn. |

Schema được sinh từ type hints bằng Pydantic, có `type`, `properties`, `required`, `additionalProperties=false`. MCP công bố schema qua `tools/list`; provider dùng chính schema discovery từ server. Router kiểm tra kiểu dữ liệu trước khi gọi hàm.

| Công cụ | Input chính | Tác dụng |
| --- | --- | --- |
| `hr_query` | employee_id, topic (balance/profile/policy) | Tra hồ sơ, quỹ phép, chính sách demo. |
| `calculate_leave_days` | start_date, end_date (YYYY-MM-DD) | Tính ngày làm việc, loại cuối tuần/ngày đóng cửa demo. |
| `create_leave_request` | employee_id, start_date, end_date, reason | Kiểm tra lại điều kiện, ghi đơn PENDING và giữ chỗ phép. |
| `list_leave_requests` | employee_id | Đọc danh sách và trạng thái đơn đã lưu. |

Bằng chứng: [tools.py](../src/tools.py), [8 test cases và assertions](../config/test_cases.json).

## 2. ReAct Loop & Native Tool Calling — 35%

```mermaid
flowchart LR
    U[UI / CLI] --> A[ReAct Loop]
    A <--> L[Gemini native tool calling]
    A --> C[MCP Client]
    C <-->|stdio · JSON-RPC 2.0| M[MCP Server tiến trình riêng]
    M --> T[HR Tools + validation]
    T <--> D[(SQLite)]
    M --> O[Observation]
    O --> A
    A --> F[Final Answer + Waterfall Trace]
```

Agent gọi LLM nhiều lượt, giữ model content/signatures và trả function response theo định dạng native. Mỗi lượt xử lý đầy đủ tool calls, đưa Observation vào lượt LLM kế tiếp. Chỉ kết thúc khi có Final Answer hoặc lỗi/giới hạn (8 vòng, 12 tool calls). Lỗi API không tự chuyển sang offline.

`create_leave_request` tự kiểm tra ngày, nhân viên, số dư, trùng/chéo đơn; transaction `BEGIN IMMEDIATE` giữ thao tác kiểm tra và trừ phép khả dụng nhất quán khi có yêu cầu đồng thời. PENDING chỉ là chờ duyệt, không phê duyệt hay gửi email.

**Model trong bằng chứng:** `{model}`.
**Lần chạy ghi nhận:** `{live.get('generated_at','chưa chạy')}` (UTC).
**Kết quả API thật:** **{live.get('passed',0)}/{live.get('total',0)}**; **{tool_count} tool calls**.

| Case | Tình huống | Kết quả | Chuỗi công cụ |
| --- | --- | --- | --- |
{chr(10).join(rows)}

TC01–TC05 là năm case chính theo lab; TC06–TC08 mở rộng thiếu phép, thiếu thông tin và chính sách. Mỗi case chạy trên SQLite tạm riêng; kiểm tra trạng thái database, tham số, thứ tự đọc trước ghi, mã đơn xuất hiện trong câu trả lời và các Observation bắt buộc.

## 3. Waterfall Trace & Observation — 25%

Artifact: [trace_waterfall.json](trace_waterfall.json). File chứa model/provider, cờ `live`, run_id, timestamp, step, action_type, tham số, Observation, Final Answer, token usage và thời gian đo bằng `perf_counter`. Không gán latency giả. Thời gian lượt LLM trong chế độ nghiệm thu có thể bao gồm khoảng chờ `--pace` để hạn chế burst request.

**Thought** là tóm tắt hành động quan sát được (tool được đề xuất hoặc đã có phản hồi), không phải suy nghĩ nội bộ. Các trường `THOUGHT → ACTION → OBSERVATION → FINAL_ANSWER` có thể kiểm tra trực tiếp trong JSON và UI.

Trích các trường liên quan từ **{example['test_case'] if example else 'chưa có case thành công'}**, run_id **{example['run_id'] if example else 'chưa có'}** (giữ nguyên dữ liệu và thời gian đã ghi):

```json
{json.dumps(excerpt,ensure_ascii=False,indent=2)}
```

### Kiểm chứng bổ sung

- Kiểm thử tự động: **{unit_total-unit_fail}/{unit_total}** đạt; [JUnit XML](test-results.xml).
- Bộ nghiệm thu offline: **{offline.get('passed',0)}/{offline.get('total',0)}**; [trace offline](trace_waterfall_offline.json). Không dùng kết quả này thay cho API thật.
- UI trình duyệt: **{browser.get('status','chưa có kết quả')}**, {len(browser.get('checks',[]))} mục kiểm tra; [browser-results.json](browser-results.json). Gồm tra cứu, tạo đơn, số dư cập nhật, tải trace, bộ lọc, baseline, lỗi mạng và mobile.
- UI có bốn màn hình: Trợ lý AI, Đơn nghỉ phép, Chính sách, Góc trình bày; có in/lưu PDF và tải JSON trace.

## 4. Git Repository & Submission — 15%

Repository cá nhân: **https://github.com/tamnd2004/K4-DAY03-NguyenDucTam-2A202602921**.

`.env`, database runtime, cache và thư mục tạm được ignore. Không đưa API key vào báo cáo hoặc trình duyệt. Bản nộp gồm code, cấu hình mẫu, test cases, UI, báo cáo và trace.

Kiểm tra bản đã đẩy bằng `git status --short`, `git log -1 --oneline` và đối chiếu `git rev-parse HEAD` với `git ls-remote origin refs/heads/main`. Chi tiết bàn giao ở [SUBMISSION.md](SUBMISSION.md).

- [x] Đã chọn chủ đề và hoàn thiện 4 tiêu chí Agentic Fit.
- [x] Đã có JSON Schema, ReAct Loop, native tool calling và MCP stdio thực.
- [{'x' if all_live else ' '}] Tất cả test nghiệm thu API thật đã đạt.
- [x] Đã ghi trace và đưa đoạn trích thực tế vào báo cáo.
- [ ] Nộp đường dẫn repository vào bài Day 03 trên LMS VLearn; chưa có biên nhận nộp LMS.

## 5. Cách chạy và giới hạn

```powershell
.\\.venv\\Scripts\\python.exe src\\web.py
# Mở http://127.0.0.1:8000
.\\.venv\\Scripts\\python.exe src\\app.py --all
.\\.venv\\Scripts\\python.exe src\\app.py --all --offline
.\\.venv\\Scripts\\python.exe -m pytest -q
```

Ngày tham chiếu của dữ liệu demo là 13/09/2026, năm phép 2026. Chưa có đăng nhập/phân quyền, phê duyệt/hủy đơn hoặc tích hợp HRIS. Lịch đóng cửa giả lập không phải lịch nghỉ lễ pháp định đầy đủ. API thật vẫn phụ thuộc mạng/quota; offline được ghi nhãn riêng. Hướng dẫn demo: [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

Nguồn kỹ thuật: [Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling), [MCP Python SDK v1](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x).
"""
    (ROOT/'docs/trace_eval.md').write_text('\n'.join(line.rstrip() for line in report.splitlines())+'\n',encoding='utf-8')
    print(f'Report generated: live {live.get("passed",0)}/{live.get("total",0)}, unit {unit_total-unit_fail}/{unit_total}')

if __name__=='__main__':main()
