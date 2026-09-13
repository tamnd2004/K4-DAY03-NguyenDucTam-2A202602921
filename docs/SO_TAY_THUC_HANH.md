# Sổ tay thực hành — PeopleOps Day 03

**Nguyễn Đức Tâm · 2A202602921 · Chủ đề 2.1 — Trợ lý nhân sự**

## Checklist nghiệm thu

- [x] Chọn chủ đề Nhân sự & Vận hành; triển khai HR Assistant.
- [x] Điền Agentic Fit: Multi-step 5/5, Tool Interaction 5/5, Dynamic Decision 5/5, Long Horizon 2/5; tổng 17/20.
- [x] Khai báo bốn tool với JSON Schema và validation.
- [x] Hoàn thiện 5 test chính và 3 test mở rộng, có assertions.
- [x] MCP stdio thực: initialize, tools/list, tools/call.
- [x] ReAct Loop nhiều lượt với native function calls và Observation quay về LLM.
- [x] Dùng đúng gemini-3.5-flash-lite, không đổi ngầm sang model khác.
- [x] Bộ nghiệm thu API thật đạt 8/8; trace tại docs/trace_waterfall.json.
- [x] Bộ offline đạt 8/8, được ghi nhãn riêng.
- [x] 26 kiểm thử tự động đạt; có JUnit XML.
- [x] UI có chat, trace, đơn nghỉ, chính sách và góc trình bày.
- [x] Điền báo cáo và trích trace thực vào docs/trace_eval.md.
- [x] Có repository cá nhân trên GitHub; xem hướng dẫn xác minh bản nộp ở docs/SUBMISSION.md.
- [ ] Học viên tự nộp link GitHub lên LMS VLearn và kiểm tra biên nhận.

## Chạy UI

```powershell
cd D:\Tamnd\AI_thuc_chien\K4-DAY03-NguyenDucTam-2A202602921
.\.venv\Scripts\python.exe src\web.py
```

Mở http://127.0.0.1:8000. Dừng/khởi động lại server sau khi đổi model trong .env.

## Demo trong lớp

1. Mở Góc trình bày để giải thích đề tài, 4 điểm Agentic Fit, kiến trúc và tools.
2. So sánh Chatbot thường/ReAct Agent với câu “Hãy tra cứu quỹ phép còn lại của NV001.”
3. Tạo đơn từ 21/09/2026 đến 23/09/2026, lý do việc gia đình.
4. Mở trace Action/Observation, kiểm tra Đơn nghỉ phép và tải JSON.
5. Thử NV003 xin 5 ngày khi chỉ còn 1 ngày để thấy nhánh dừng.

Xem [kịch bản đầy đủ](DEMO_SCRIPT.md), [báo cáo](trace_eval.md), [bàn giao nộp bài](SUBMISSION.md).
