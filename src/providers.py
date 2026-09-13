"""Native tool conversation adapters. Live failures NEVER fall back to mock."""
from __future__ import annotations
import json
import logging
import os
import re
import threading
import time
import uuid
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

_request_lock = threading.Lock()
_last_request = 0.0
_request_interval = 0.0

def set_request_interval(seconds):
    """Evaluation pacing, shared across the per-test provider instances."""
    global _request_interval
    _request_interval = max(0,float(seconds))

def pace_request():
    global _last_request
    with _request_lock:
        delay = _request_interval - (time.monotonic()-_last_request)
        if delay>0:
            time.sleep(delay)
        _last_request = time.monotonic()

class ProviderError(RuntimeError):
    pass

def public_error(exc):
    code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    logging.getLogger(__name__).warning("LLM request failed: category=%s status=%s",type(exc).__name__,code)
    if code == 429:
        return "API hết quota hoặc bị giới hạn tốc độ (429). Thử lại sau hoặc chọn Demo offline."
    if code in (400,401,403,404):
        return f"API từ chối yêu cầu ({code}). Kiểm tra API key, model và quyền truy cập trong .env."
    if code in (500,502,503,504):
        return f"Dịch vụ mô hình tạm thời không sẵn sàng ({code}); đã thử lại có giới hạn. Vui lòng thử sau."
    return "Không nhận được phản hồi API. Kiểm tra kết nối, quota và cấu hình .env; có thể chọn Demo offline."

def normalize_gemini_model_name(model: str | None) -> str:
    """Normalize formatting only; never silently substitute a different model."""
    return (model or "gemini-3.5-flash-lite").strip().lower()


def provider_config():
    name = os.getenv("LLM_PROVIDER", "gemini").lower()
    raw_model = os.getenv("LLM_MODEL")
    if name == "openai":
        model = raw_model or "gpt-4o-mini"
    else:
        model = normalize_gemini_model_name(raw_model or "gemini-3.5-flash-lite")
    key = os.getenv("OPENAI_API_KEY" if name == "openai" else "GEMINI_API_KEY", "")
    return {"provider":name,"model":model,"configured":name in {"gemini","openai"} and bool(key and not key.startswith("your_"))}

class GeminiProvider:
    name = "gemini"
    live = True
    def __init__(self, model=None):
        from google import genai
        from google.genai import types
        self.types = types
        self.model_name = normalize_gemini_model_name(model or provider_config()["model"])
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=types.HttpOptions(
            timeout=45000,retry_options=types.HttpRetryOptions(attempts=3,initial_delay=15,max_delay=45,http_status_codes=[429,500,502,503,504])))
        self.history = []

    def start(self, query, history):
        t = self.types
        self.history = [t.Content(role="model" if x["role"] == "assistant" else "user", parts=[t.Part(text=x["content"])]) for x in history]
        self.history.append(t.Content(role="user", parts=[t.Part(text=query)]))

    def next(self, schemas, system_prompt):
        t = self.types
        config = t.GenerateContentConfig(
            system_instruction=system_prompt, temperature=0.1,
            tools=[t.Tool(function_declarations=[t.FunctionDeclaration(name=s["name"], description=s["description"], parameters_json_schema=s["parameters"]) for s in schemas])] if schemas else None,
            automatic_function_calling=t.AutomaticFunctionCallingConfig(disable=True),
            thinking_config=t.ThinkingConfig(thinking_budget=0) if "2.5-flash" in self.model_name else None,
        )
        try:
            pace_request()
            response = self.client.models.generate_content(model=self.model_name, contents=self.history, config=config)
            if not response.candidates:
                raise ProviderError("API trả kết quả rỗng hoặc bị chặn; chưa có câu trả lời.")
            content = response.candidates[0].content
            if not content or not content.parts:
                raise ProviderError("API trả kết quả rỗng hoặc bị chặn; chưa có câu trả lời.")
            self.history.append(content)  # Preserve native function calls AND thought signatures.
            calls = [{"id":uuid.uuid4().hex,"name":p.function_call.name,"arguments":dict(p.function_call.args or {})} for p in content.parts if p.function_call]
            answer = "\n".join(p.text for p in content.parts if p.text and not p.thought)
            usage = response.usage_metadata
            return {"calls":calls,"text":answer,"tokens":getattr(usage,"total_token_count",0) or 0}
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(public_error(exc)) from None

    def observe(self, results):
        self.history.append(self.types.Content(role="user", parts=[self.types.Part.from_function_response(name=c["name"], response=result) for c,result in results]))

    def close(self):
        self.client.close()

class OpenAIProvider:
    name = "openai"
    live = True
    def __init__(self, model=None):
        from openai import OpenAI
        self.model_name = model or provider_config()["model"]
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=45, max_retries=1)
        self.history = []

    def start(self, query, history):
        self.history = list(history) + [{"role":"user","content":query}]

    def next(self, schemas, system_prompt):
        try:
            pace_request()
            kwargs = {"tools":[{"type":"function","function":s} for s in schemas],"tool_choice":"auto"} if schemas else {}
            response = self.client.chat.completions.create(model=self.model_name, messages=[{"role":"system","content":system_prompt}]+self.history, **kwargs)
            message = response.choices[0].message
            self.history.append(message.model_dump(exclude_none=True))
            calls = [{"id":c.id,"name":c.function.name,"arguments":json.loads(c.function.arguments)} for c in message.tool_calls or []]
            return {"calls":calls,"text":message.content or "","tokens":response.usage.total_tokens if response.usage else 0}
        except Exception as exc:
            raise ProviderError(public_error(exc)) from None

    def observe(self, results):
        for call,result in results:
            self.history.append({"role":"tool","tool_call_id":call["id"],"content":json.dumps(result,ensure_ascii=False)})

    def close(self):
        self.client.close()

class MockOfflineProvider:
    """Deterministic demo scenarios; explicitly not a language model."""
    name = "mock"
    live = False
    model_name = "Demo kịch bản · không dùng LLM"
    def start(self, query, history):
        self.query, self.results = query, []

    def next(self, schemas, system_prompt):
        q = self.query.lower()
        def answer(text):
            return {"calls":[],"text":text,"tokens":0}
        def call(name, **args):
            return {"calls":[{"id":uuid.uuid4().hex,"name":name,"arguments":args}],"text":"","tokens":0}
        if not schemas:
            return answer("Mình là chatbot HR, có thể giải thích quy trình chung. Mình không có quyền tra cứu quỹ phép hoặc tạo đơn; cần kết nối công cụ để thực hiện yêu cầu này.")
        match = re.search(r"\bnv\d+\b", q)
        emp = match.group().upper() if match else None
        wants_create = any(w in q for w in ("tạo đơn","xin nghỉ","đăng ký nghỉ"))
        if not emp:
            if any(w in q for w in ("phép","chính sách","bảo hiểm","đơn","hồ sơ")):
                return answer("Bạn cung cấp mã nhân viên (ví dụ NV001) giúp mình nhé. Demo offline hỗ trợ các câu mẫu với ngày cụ thể.")
            return answer("Chào bạn! Mình là PeopleOps. Mình có thể tra cứu quỹ phép, chính sách nhân sự và tạo đơn nghỉ phép chờ quản lý duyệt. Bạn muốn bắt đầu với việc gì?")
        if not self.results:
            if "danh sách" in q or "đơn của" in q:
                return call("list_leave_requests", employee_id=emp)
            return call("hr_query",employee_id=emp,topic="policy" if "chính sách" in q or "bảo hiểm" in q else "balance")
        previous, obs = self.results[-1]
        if obs.get("status") not in {"SUCCESS","ALREADY_EXISTS"}:
            return answer(obs.get("message", "Khoảng ngày không có ngày làm việc hoặc không hợp lệ. Vui lòng chọn lại; chưa tạo đơn."))
        if previous["name"] == "create_leave_request":
            r = obs["request"]
            return answer(f"{obs['message']}\n\nMã đơn: {r['request_id']} · {r['employee_id']}\nNgày nghỉ: {r['start_date']} → {r['end_date']} ({r['days']} ngày làm việc).\nLý do: {r['reason']}.\nTrạng thái: Chờ duyệt (PENDING)." + (f"\nQuản lý: {obs['manager']}. Quỹ phép khả dụng còn {obs['available_days']} ngày." if "manager" in obs else ""))
        if previous["name"] == "list_leave_requests":
            return answer("Chưa có đơn nghỉ phép." if not obs["requests"] else "\n".join(f"{r['request_id']}: {r['start_date']} → {r['end_date']}, {r['days']} ngày, {r['status']}" for r in obs["requests"]))
        employee = self.results[0][1]["employee"]
        if not wants_create:
            if obs.get("policies"):
                return answer("Chính sách DEMO\n\n"+"\n\n".join(obs["policies"][k] for k in ("annual_leave","approval","insurance","calendar")))
            return answer(f"{employee['full_name']} ({emp}) có {employee['available_days']} ngày phép khả dụng.\n\nHạn mức: {employee['allowance']} ngày · Đã dùng: {employee['used']} · Đang chờ duyệt: {employee['pending_days']} ngày.\nQuản lý trực tiếp: {employee['manager']}.")
        dates = re.findall(r"\d{4}-\d{2}-\d{2}",q)
        if not dates:
            dates = [f"{y}-{int(m):02d}-{int(d):02d}" for d,m,y in re.findall(r"(\d{1,2})/(\d{1,2})/(\d{4})",q)]
        reason = re.search(r"lý do\s*[:：]?\s*(.+?)[.!]?$", self.query, re.I)
        if not dates or not reason:
            return answer("Bạn cung cấp ngày bắt đầu, ngày kết thúc (DD/MM/YYYY) và lý do nghỉ giúp mình nhé. Ví dụ: tạo đơn cho NV001 từ 21/09/2026 đến 23/09/2026, lý do: việc gia đình.")
        args = {"start_date":dates[0],"end_date":dates[-1]}
        if previous["name"] == "hr_query":
            return call("calculate_leave_days",**args)
        if obs["days"] > employee["available_days"]:
            return answer(f"Không đủ quỹ phép: cần {obs['days']} ngày nhưng {emp} chỉ còn {employee['available_days']} ngày. Chưa tạo đơn. Bạn có thể chọn khoảng nghỉ ngắn hơn.")
        return call("create_leave_request",employee_id=emp,reason=reason.group(1).strip(),**args)

    def observe(self, results):
        self.results.extend(results)

    def close(self):
        pass

def get_llm_provider(mode="live"):
    if mode == "mock":
        return MockOfflineProvider()
    config = provider_config()
    if not config["configured"]:
        raise ProviderError("Chưa cấu hình API thật. Điền GEMINI_API_KEY/OPENAI_API_KEY trong .env hoặc chọn Demo offline.")
    return OpenAIProvider() if config["provider"] == "openai" else GeminiProvider()
