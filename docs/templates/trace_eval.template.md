# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Nguyễn Đức Tâm  
> **Mã Sinh Viên / Mã Học viên:** 2A202602921  
> **Chủ đề Lựa chọn:** 2.1 — Trợ lý Nhân sự PeopleOps (HR & Operations)  

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 5 / 5 | Tra hồ sơ → tính ngày làm việc → so sánh quỹ phép → tạo đơn → xác nhận mã đơn; cần nhiều bước nối tiếp. |
| **2. Tool Interaction** | 5 / 5 | Cần đọc và ghi dữ liệu nhân sự trong SQLite qua MCP; LLM không tự biết số dư hoặc tạo được đơn chỉ bằng văn bản. |
| **3. Dynamic Decision** | 5 / 5 | Agent đổi nhánh theo Observation: thiếu phép, sai mã, trùng đơn hoặc thiếu thông tin thì dừng tạo đơn và giải thích/hỏi lại. |
| **4. Long Horizon Goal** | 2 / 5 | Giữ mục tiêu trong một phiên nhiều lượt; chưa có tự theo dõi duyệt đơn, nhắc việc hoặc mục tiêu dài hạn. |
| **TỔNG ĐIỂM AGENTIC FIT** | **17 / 20** | *Tổng điểm > 12/20: Bài toán phù hợp triển khai ReAct Agent.* |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Đoạn trích thực tế từ `docs/trace_waterfall.json`: **{{CASE_ID}}**, model **`{{MODEL}}`**, `live=true`, run_id **`{{RUN_ID}}`**. Các trường bên dưới giữ nguyên giá trị trong log; Thought là tóm tắt hành động quan sát được.

```json
{{TRACE_EXCERPT}}
```

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [{{LIVE_CHECK}}] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (Gemini/OpenAI).
- **Tổng số Test Cases đã chạy thành công:** **{{CORE_PASSED}} / 5** test cases chính (TC01–TC05); **{{EXTRA_PASSED}} / {{EXTRA_TOTAL}}** case mở rộng. Tổng: **{{TOTAL_PASSED}} / {{TOTAL}}**.
- **Số lượt gọi Tool qua MCP Server chính xác:** **{{CORE_TOOLS}} lượt** cho TC01–TC05; **{{TOTAL_TOOLS}} lượt** cho toàn bộ {{TOTAL}} case.
- **Kết quả đẩy Repo nộp bài:** [{{GIT_CHECK}}] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn: [K4-DAY03-NguyenDucTam-2A202602921](https://github.com/tamnd2004/K4-DAY03-NguyenDucTam-2A202602921) và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!

> **Trạng thái LMS:** Học viên tự nộp link GitHub; chưa có biên nhận xác nhận đã nộp.
