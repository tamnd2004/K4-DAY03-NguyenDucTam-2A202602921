import asyncio
import json
from types import SimpleNamespace
from app import run_react_agent, evaluate_case, load_test_cases
from providers import MockOfflineProvider, ProviderError, GeminiProvider, OpenAIProvider
from tools import HRStore

def test_requested_gemini_model_is_not_substituted(monkeypatch):
    from providers import provider_config, normalize_gemini_model_name
    monkeypatch.setenv("LLM_PROVIDER","gemini")
    monkeypatch.setenv("LLM_MODEL","gemini-3.5-flash-lite")
    assert provider_config()["model"]=="gemini-3.5-flash-lite"
    assert normalize_gemini_model_name("gemini-3.8-flash")=="gemini-3.8-flash"

def test_agent_executes_real_mcp_and_observes_results(db_path):
    case=load_test_cases()[2]
    result=asyncio.run(run_react_agent(case["question"],MockOfflineProvider(),db_path=db_path))
    assert evaluate_case(case,result,HRStore(db_path).snapshot())["passed"]
    assert result["live"] is False
    assert result["tool_calls"]==3
    assert sum(e["action_type"]=="THOUGHT" for e in result["trace"])==4
    assert all(e["latency_ms"]>=0 for e in result["trace"])

def test_baseline_cannot_write(db_path):
    result=asyncio.run(run_react_agent(load_test_cases()[2]["question"],MockOfflineProvider(),baseline=True))
    assert result["tool_calls"]==0
    assert HRStore(db_path).snapshot()["requests"]==[]

def test_live_failure_is_error_not_mock(db_path):
    class Failing(MockOfflineProvider):
        name="gemini"
        live=True
        def next(self,*args): raise ProviderError("API không sẵn sàng")
    result=asyncio.run(run_react_agent("Xin chào",Failing(),baseline=True))
    assert result["status"]=="error"
    assert result["live"] is True
    assert not any(e["action_type"]=="FINAL_ANSWER" for e in result["trace"])

def test_iteration_budget_stops_loop(db_path):
    class Loop(MockOfflineProvider):
        def next(self,*args):
            return {"calls":[{"id":"call","name":"hr_query","arguments":{"employee_id":"NV001"}}],"text":""}
    class Client:
        schemas=[]
        async def call_tool(self,*args): return {"status":"SUCCESS"}
    result=asyncio.run(run_react_agent("loop",Loop(),Client()))
    assert result["status"]=="error"
    assert result["tool_calls"]==8

def test_mcp_task_group_keeps_useful_provider_error(db_path):
    class Failing(MockOfflineProvider):
        name="gemini"
        live=True
        def next(self,*args):raise ProviderError("API từ chối yêu cầu (404).")
    result=asyncio.run(run_react_agent("tra NV001",Failing(),db_path=db_path))
    assert result["status"]=="error"
    assert "404" in result["answer"]

def test_gemini_preserves_signature_and_native_observation():
    from google.genai import types
    provider=object.__new__(GeminiProvider)
    provider.types=types;provider.model_name="gemini-2.5-flash"
    content=types.Content(role="model",parts=[types.Part(function_call=types.FunctionCall(name="hr_query",args={"employee_id":"NV001"}),thought_signature=b"signature")])
    fake_response=SimpleNamespace(candidates=[SimpleNamespace(content=content)],usage_metadata=None)
    provider.client=SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kwargs:fake_response))
    provider.start("Tra NV001",[])
    response=provider.next([],"system")
    assert provider.history[-1] is content
    assert provider.history[-1].parts[0].thought_signature==b"signature"
    provider.observe([(response["calls"][0],{"status":"SUCCESS"})])
    assert provider.history[-1].parts[0].function_response.name=="hr_query"

def test_openai_matches_tool_call_ids():
    provider=object.__new__(OpenAIProvider)
    provider.start("test",[])
    provider.observe([({"id":"abc","name":"hr_query"},{"status":"SUCCESS"}),({"id":"def","name":"calculate_leave_days"},{"days":3})])
    assert [m["tool_call_id"] for m in provider.history[1:]]==["abc","def"]
    assert json.loads(provider.history[-1]["content"])["days"]==3
