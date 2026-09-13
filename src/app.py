"""ReAct execution shared by CLI, evaluation and the streaming web demo."""
from __future__ import annotations
import argparse
import asyncio
import json
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from mcp_client import connect_mcp
from prompts import CHATBOT_BASELINE_PROMPT, REACT_AGENT_SYSTEM_PROMPT, MAX_ITERATIONS, MAX_TOOL_CALLS
from providers import ProviderError, get_llm_provider, set_request_interval
from tools import HRStore

ROOT = Path(__file__).resolve().parents[1]

async def run_react_agent(user_query, provider, mcp_client=None, *, history=None, emit=None, baseline=False, db_path=None):
    started = time.perf_counter()
    run_id = uuid.uuid4().hex
    trace, tokens, call_count = [], 0, 0
    def event(kind, step=0, latency_ms=0, **data):
        item = {"run_id":run_id,"step":step,"query":user_query,"action_type":kind,
                "timestamp":datetime.now(timezone.utc).isoformat(), "offset_ms":round((time.perf_counter()-started)*1000,2),
                "latency_ms":round(latency_ms,2), **data}
        trace.append(item)
        if emit:
            emit(item)
    provider.start(user_query, history or [])
    event("RUN_START",provider=provider.name,model=provider.model_name,live=provider.live,mode="baseline" if baseline else "agent")
    answer, status = "", "completed"
    async def execute(client):
        nonlocal tokens, call_count, answer, status
        schemas = [] if baseline else client.schemas
        prompt = CHATBOT_BASELINE_PROMPT if baseline else REACT_AGENT_SYSTEM_PROMPT
        for step in range(1,MAX_ITERATIONS+1):
            event("LLM_START",step,summary="Đang chờ phản hồi mô hình" if provider.live else "Đang chạy kịch bản offline")
            tick = time.perf_counter()
            response = await asyncio.to_thread(provider.next,schemas,prompt)
            tokens += response.get("tokens",0)
            calls = response["calls"]
            event("THOUGHT",step,(time.perf_counter()-tick)*1000,summary=("Đề xuất: "+", ".join(c["name"] for c in calls)) if calls else "Đã có phản hồi cuối",note="Tóm tắt hành động quan sát được, không phải suy nghĩ nội bộ.")
            if not calls:
                answer = response["text"].strip()
                if not answer:
                    raise ProviderError("Mô hình trả lời rỗng. Hãy thử lại yêu cầu.")
                event("FINAL_ANSWER",step,output=answer)
                return
            results = []
            for call in calls:
                call_count += 1
                if baseline or call_count > MAX_TOOL_CALLS:
                    raise ProviderError("Đã đạt giới hạn gọi tool; dừng phiên để tránh lặp vô hạn.")
                event("ACTION",step,tool_name=call["name"],arguments=call["arguments"],call_id=call["id"])
                tick = time.perf_counter()
                obs = await client.call_tool(call["name"],call["arguments"])
                event("OBSERVATION",step,(time.perf_counter()-tick)*1000,tool_name=call["name"],call_id=call["id"],observation=obs)
                results.append((call,obs))
            provider.observe(results)  # Feed native tool outputs into the NEXT LLM turn.
        raise ProviderError("Đã đạt giới hạn 8 vòng lặp. Hãy xem trace và chia nhỏ yêu cầu; các đơn đã tạo vẫn được giữ.")
    try:
        if baseline:
            await execute(None)
        elif mcp_client:
            await execute(mcp_client)
        else:
            tick = time.perf_counter()
            async with connect_mcp(db_path) as client:
                event("MCP_READY",latency_ms=(time.perf_counter()-tick)*1000,tools=[s["name"] for s in client.schemas],transport="stdio · JSON-RPC 2.0")
                await execute(client)
    except ProviderError as exc:
        status, answer = "error", str(exc)
        event("ERROR",output=answer)
    except Exception as exc:
        # anyio's MCP task groups can wrap a provider failure in ExceptionGroup.
        def provider_failure(error):
            if isinstance(error,ProviderError):
                return str(error)
            for child in getattr(error,"exceptions",[]):
                found=provider_failure(child)
                if found:
                    return found
            return None
        status, answer = "error", provider_failure(exc) or "Không thể hoàn tất kết nối MCP hoặc thực thi công cụ. Kiểm tra môi trường Python và chạy kiểm thử MCP."
        event("ERROR",output=answer)
    finally:
        provider.close()
    result = {"run_id":run_id,"status":status,"answer":answer,"provider":provider.name,"model":provider.model_name,
              "live":provider.live,"mode":"baseline" if baseline else "agent","tool_calls":call_count,"tokens":tokens,
              "duration_ms":round((time.perf_counter()-started)*1000,2),"trace":trace}
    return result

def load_test_cases():
    return json.loads((ROOT/"config/test_cases.json").read_text(encoding="utf-8"))

def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")

def evaluate_case(case, result, snapshot):
    actions = [e for e in result["trace"] if e["action_type"] == "ACTION"]
    observations = [e for e in result["trace"] if e["action_type"] == "OBSERVATION"]
    names = [e["tool_name"] for e in actions]
    checks = {"completed":result["status"] == "completed", "answer_present":bool(result["answer"])}
    expect = case["assertions"]
    checks["required_tools"] = all(n in names for n in expect.get("required_tools",[]))
    checks["forbidden_tools"] = not any(n in names for n in expect.get("forbidden_tools",[]))
    checks["writes"] = len(snapshot["requests"]) == expect.get("requests",0)
    if expect.get("no_tools"):
        checks["no_tools"] = not actions
    if "observation_status" in expect:
        checks["observation_status"] = any(e["observation"].get("status") == expect["observation_status"] for e in observations)
    if "observation_fields" in expect:
        spec=expect["observation_fields"]
        def field_value(data,path):
            for key in path.split('.'):
                data=data.get(key) if isinstance(data,dict) else None
            return data
        checks["observation_fields"] = any(e["tool_name"]==spec["tool"] and all(field_value(e["observation"],k)==v for k,v in spec["fields"].items()) for e in observations)
    if expect.get("requests"):
        request = snapshot["requests"][0] if snapshot["requests"] else {}
        checks["pending"] = request.get("status") == "PENDING"
        checks["days"] = request.get("days") == expect["days"]
        checks["request_fields"] = all(request.get(k) == v for k,v in expect.get("request_fields",{}).items())
        checks["grounded_id"] = bool(request.get("request_id")) and request["request_id"] in result["answer"]
        create_index = names.index("create_leave_request") if "create_leave_request" in names else 0
        checks["read_before_write"] = all(n in names[:create_index] for n in ["hr_query","calculate_leave_days"])
    return {"id":case["id"],"passed":all(checks.values()),"checks":checks,"tool_calls":len(actions),"run_id":result["run_id"],"live":result["live"]}

async def run_suite(mode, output=None, pace_seconds=15):
    if mode=="live":
        set_request_interval(pace_seconds)
    runs, evaluations = [], []
    for case in load_test_cases():
        with tempfile.TemporaryDirectory(prefix="peopleops-eval-") as temp:
            db = Path(temp)/"hr.db"
            result = await run_react_agent(case["question"],get_llm_provider(mode),db_path=db)
            evaluation = evaluate_case(case,result,HRStore(db).snapshot())
        runs.append({"test_case":case["id"],**result})
        evaluations.append(evaluation)
        print(f"{case['id']} {'PASS' if evaluation['passed'] else 'FAIL'} | {result['tool_calls']} tools | {result['duration_ms']/1000:.1f}s",flush=True)
        if not evaluation["passed"]:
            print(json.dumps(evaluation["checks"],ensure_ascii=False),flush=True)
            print(result["answer"],flush=True)
    suffix = "" if mode == "live" else "_offline"
    artifact = {"generated_at":datetime.now(timezone.utc).isoformat(),"mode":mode,"data":"fictional_hr_demo","transport":"MCP stdio",
                "passed":sum(e["passed"] for e in evaluations),"total":len(evaluations),"evaluations":evaluations,"runs":runs}
    write_json(output or ROOT/f"docs/trace_waterfall{suffix}.json",artifact)
    print(f"Result: {artifact['passed']}/{artifact['total']} ({mode})",flush=True)
    return artifact

async def main(args):
    mode = "mock" if args.offline else "live"
    if args.all:
        result = await run_suite(mode,args.output,args.pace)
        return 0 if result["passed"] == result["total"] else 1
    history = []
    while True:
        query = input("Bạn: ").strip() if args.interactive else args.query or load_test_cases()[1]["question"]
        if query.lower() in {"exit","quit"} or not query:
            return 0
        result = await run_react_agent(query,get_llm_provider(mode),history=history,baseline=args.baseline)
        print(result["answer"])
        write_json(args.output or ROOT/"data/last_cli_trace.json",result)
        if result["status"] == "completed":
            history.extend([{"role":"user","content":query},{"role":"assistant","content":result["answer"]}])
            history = history[-12:]
        if not args.interactive:
            return 0 if result["status"] == "completed" else 1

if __name__ == "__main__":
    if hasattr(sys.stdout,"reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="PeopleOps · Day 03 HR ReAct Agent")
    parser.add_argument("--all",action="store_true")
    parser.add_argument("--interactive",action="store_true")
    parser.add_argument("--offline",action="store_true")
    parser.add_argument("--baseline",action="store_true")
    parser.add_argument("--query")
    parser.add_argument("--output")
    parser.add_argument("--pace",type=float,default=15,help="Minimum seconds between LLM requests in --all (default 15 to avoid free-tier bursts)")
    try:
        sys.exit(asyncio.run(main(parser.parse_args())))
    except (KeyboardInterrupt,EOFError):
        pass
    except ProviderError as exc:
        print(str(exc))
        sys.exit(1)
