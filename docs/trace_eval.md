# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Nguyễn Đức Tâm  
> **Mã Sinh Viên / Mã Học viên:** 2A202602921  
> **Chủ đề Lựa chọn:** 2.1 — Trợ lý Nhân sự PeopleOps (HR & Operations)

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá           | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm                                                                                          |
| :-------------------------- | :------------: | :--------------------------------------------------------------------------------------------------------------------------- |
| **1. Multi-step Reasoning** |     5 / 5      | Tra hồ sơ → tính ngày làm việc → so sánh quỹ phép → tạo đơn → xác nhận mã đơn; cần nhiều bước nối tiếp.                      |
| **2. Tool Interaction**     |     5 / 5      | Cần đọc và ghi dữ liệu nhân sự trong SQLite qua MCP; LLM không tự biết số dư hoặc tạo được đơn chỉ bằng văn bản.             |
| **3. Dynamic Decision**     |     5 / 5      | Agent đổi nhánh theo Observation: thiếu phép, sai mã, trùng đơn hoặc thiếu thông tin thì dừng tạo đơn và giải thích/hỏi lại. |
| **4. Long Horizon Goal**    |     2 / 5      | Giữ mục tiêu trong một phiên nhiều lượt; chưa có tự theo dõi duyệt đơn, nhắc việc hoặc mục tiêu dài hạn.                     |
| **TỔNG ĐIỂM AGENTIC FIT**   |  **17 / 20**   | _Tổng điểm > 12/20: Bài toán phù hợp triển khai ReAct Agent._                                                                |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Đoạn trích thực tế từ `docs/trace_waterfall.json`: **TC04**, model **`gemini-3.5-flash-lite`**, `live=true`, run_id **`a4984ca9db6f425c9a0d42f06ab063b9`**. Các trường bên dưới giữ nguyên giá trị trong log; Thought là tóm tắt hành động quan sát được.

```json
[
  {
    "step": 2,
    "action_type": "THOUGHT",
    "latency_ms": 15039.3,
    "summary": "Đề xuất: create_leave_request"
  },
  {
    "step": 2,
    "action_type": "ACTION",
    "latency_ms": 0,
    "tool_name": "create_leave_request",
    "arguments": {
      "end_date": "2026-09-22",
      "start_date": "2026-09-18",
      "reason": "du lịch cùng gia đình",
      "employee_id": "NV002"
    }
  },
  {
    "step": 2,
    "action_type": "OBSERVATION",
    "latency_ms": 22.16,
    "tool_name": "create_leave_request",
    "observation": {
      "status": "SUCCESS",
      "request": {
        "request_id": "LV-22591506",
        "employee_id": "NV002",
        "start_date": "2026-09-18",
        "end_date": "2026-09-22",
        "days": 3,
        "reason": "du lịch cùng gia đình",
        "status": "PENDING",
        "created_at": "2026-09-13T13:27:18.529934+00:00"
      },
      "manager": "Phạm Hoàng Nam",
      "available_days": 5,
      "message": "Đã tạo đơn chờ quản lý duyệt và giữ chỗ quỹ phép. Chưa được phê duyệt."
    }
  },
  {
    "step": 3,
    "action_type": "FINAL_ANSWER",
    "latency_ms": 0,
    "output": "Quỹ phép của bạn hiện còn 8 ngày. Sau khi tính toán, thời gian từ 18/09/2026 đến 22/09/2026 gồm 3 ngày làm việc (trừ cuối tuần). \n\nĐơn nghỉ phép của bạn đã được tạo thành công:\n- **Mã đơn:** LV-22591506\n- **Khoảng thời gian:** 18/09/2026 – 22/09/2026 (3 ngày)\n- **Lý do:** Du lịch cùng gia đình\n- **Trạng thái:** PENDING (Chờ quản lý trực tiếp là **Phạm Hoàng Nam** duyệt)\n- **Quỹ phép tạm tính sau khi giữ chỗ:** 5 ngày"
  }
]
```

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (Gemini/OpenAI).
- **Tổng số Test Cases đã chạy thành công:** **5 / 5** test cases chính (TC01–TC05); **3 / 3** case mở rộng. Tổng: **8 / 8**.
- **Số lượt gọi Tool qua MCP Server chính xác:** **8 lượt** cho TC01–TC05; **12 lượt** cho toàn bộ 8 case.
- **Kết quả đẩy Repo nộp bài:** [x] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn: [K4-DAY03-NguyenDucTam-2A202602921](https://github.com/tamnd2004/K4-DAY03-NguyenDucTam-2A202602921) và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
