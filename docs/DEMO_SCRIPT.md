# Kịch bản demo PeopleOps — Nguyễn Đức Tâm · 2A202602921

## 1. Chạy ứng dụng

```powershell
cd D:\Tamnd\AI_thuc_chien\K4-DAY03-NguyenDucTam-2A202602921
.\.venv\Scripts\python.exe src\web.py
```

Mở http://127.0.0.1:8000. Model hiện tại: `gemini-3.5-flash-lite`. Sau khi đổi `.env`, dừng server bằng Ctrl+C và khởi động lại. Khi mất mạng/quota có thể chọn Demo offline; cần nói rõ đó là kịch bản dự phòng.

## 2. Trình bày năm ý trên bảng

1. **Chủ đề 2.1 — Trợ lý nhân sự:** gom tra cứu quỹ phép, chính sách và tạo đơn trong một cuộc trò chuyện. Dữ liệu giả lập, không phải hệ thống VinFast.
2. **Agentic Fit 17/20:** Multi-step 5, Tool Interaction 5, Dynamic Decision 5, Long Horizon 2. Tác vụ cần nhiều bước và đổi nhánh, nhưng không có mục tiêu tự theo dõi dài hạn.
3. **Kiến trúc:** mở Góc trình bày; UI/CLI → ReAct Loop ↔ Gemini → MCP Client ↔ MCP Server → tools ↔ SQLite. Observation quay lại lượt LLM tiếp theo.
4. **Tools:** hr_query đọc hồ sơ/chính sách; calculate_leave_days tính ngày; create_leave_request ghi đơn PENDING; list_leave_requests đọc danh sách đơn.
5. **Demo hai câu** và mở Action/Observation, sau đó tải trace JSON.

## 3. Hai câu demo

**So sánh chatbot và agent:**

> Hãy tra cứu quỹ phép còn lại của NV001.

Chạy với Chatbot thường, rồi chuyển ReAct Agent và hỏi lại. Chatbot không đọc được dữ liệu; agent gọi hr_query. Trên database mới, NV001 còn 12 ngày.

**Tạo đơn nhiều bước:**

> Tạo đơn nghỉ phép cho NV001 từ 21/09/2026 đến 23/09/2026, lý do: việc gia đình.

Chỉ trace tra hồ sơ → tính 3 ngày → tạo đơn → Final Answer. Mở Đơn nghỉ phép, xác nhận mã đơn và trạng thái chờ duyệt. Số dư khả dụng còn 9 ngày. Gửi lại cùng khoảng ngày sẽ không tạo/trừ phép lần hai.

**Mở rộng để thấy Dynamic Decision:**

> Nếu đủ phép, tạo đơn cho NV003 từ 21/09/2026 đến 25/09/2026, lý do: du lịch.

NV003 chỉ còn 1 ngày, yêu cầu cần 5 ngày; agent phải dừng trước khi tạo đơn.

## 4. Kiểm tra bằng chứng

- Góc trình bày hiển thị kết quả từ artifact nghiệm thu đã lưu.
- `docs/trace_eval.md`: chấm Agentic Fit, kiến trúc, báo cáo và đoạn trace thực.
- `docs/trace_waterfall.json`: bằng chứng API thật, kiểm tra trường model/live/status.
- `docs/trace_waterfall_offline.json`: kết quả offline, không thay thế bằng chứng API thật.
- `docs/SUBMISSION.md`: hướng dẫn nộp link repository vào LMS.
