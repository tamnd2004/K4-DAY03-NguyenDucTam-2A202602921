# Bàn giao bài nộp Day 03

**Học viên:** Nguyễn Đức Tâm · **Mã:** 2A202602921
**Đề tài:** 2.1 — Trợ lý nhân sự PeopleOps
**Model cấu hình:** gemini-3.5-flash-lite

Link repository để nộp:

https://github.com/tamnd2004/K4-DAY03-NguyenDucTam-2A202602921

## Artifacts theo rubric

| Tiêu chí | Bằng chứng |
| --- | --- |
| Agentic Fit & Tool Specs (25%) | docs/trace_eval.md, config/test_cases.json, src/tools.py |
| ReAct Loop & Native Tool Calling (35%) | src/app.py, src/providers.py, src/mcp_client.py, src/mcp_server.py, trace API thật |
| Waterfall Trace & Observation (25%) | docs/trace_waterfall.json và đoạn trích trong docs/trace_eval.md |
| Git Repository & Submission (15%) | Lịch sử commit, nhánh main trên GitHub và biên nhận nộp LMS |

## Xác minh Git

```powershell
git status --short
git log -1 --oneline
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

Working tree cần sạch, mã commit local và remote main cần giống nhau. `.env`, data runtime và thư mục test tạm không nằm trong bản nộp.

## Nộp trên VLearn

1. Đăng nhập LMS VLearn bằng tài khoản học viên.
2. Mở lớp K4 → bài nộp Day 03.
3. Dán link repository phía trên vào ô bài nộp và xác nhận nộp.
4. Kiểm tra trạng thái đã nộp/biên nhận và thời gian nộp.

**Trạng thái LMS:** học viên đã chọn tự nộp link GitHub. Chưa có biên nhận LMS; không xem việc push GitHub là đã hoàn thành nộp LMS và không khẳng định nộp đúng hạn khi chưa kiểm tra thời hạn/biên nhận.
