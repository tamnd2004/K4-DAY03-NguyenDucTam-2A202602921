"""Local FastAPI UI. No cloud HR writes, credentials stay server-side."""
import argparse
import asyncio
import json
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app import run_react_agent, load_test_cases, write_json
from providers import get_llm_provider, provider_config, ProviderError
from tools import HRStore, TOOLS_SCHEMA

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title="PeopleOps · HR Agent Lab",version="1.0.0")
app.mount("/static",StaticFiles(directory=ROOT/"ui"),name="static")
limit = asyncio.Semaphore(2)

class Message(BaseModel):
    role: Literal["user","assistant"]
    content: str = Field(min_length=1,max_length=12000)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1,max_length=3000)
    mode: Literal["live","mock"] = "live"
    baseline: bool = False
    history: list[Message] = Field(default_factory=list,max_length=12)

@app.middleware("http")
async def local_origin(request: Request, call_next):
    # Local demo only: prevent another website from issuing browser writes.
    if request.method == "POST" and request.headers.get("origin"):
        if request.headers["origin"] != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail":"Origin không hợp lệ."},status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

@app.get("/")
def index():
    return FileResponse(ROOT/"ui/index.html")

@app.get("/api/state")
def state():
    return {**HRStore().snapshot(),"llm":provider_config(),"tools":TOOLS_SCHEMA,"test_cases":load_test_cases()}

@app.get("/api/evaluation")
def evaluation():
    results = []
    for name in ["trace_waterfall.json","trace_waterfall_offline.json"]:
        path = ROOT/"docs"/name
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data,dict) and "evaluations" in data:
                results.append({k:data[k] for k in ("generated_at","mode","passed","total","evaluations")})
    return results

@app.post("/api/chat")
async def chat(body: ChatRequest):
    if not body.message.strip():
        raise HTTPException(422,"Vui lòng nhập câu hỏi.")
    try:
        provider = get_llm_provider(body.mode)
    except ProviderError as exc:
        raise HTTPException(400,str(exc)) from None
    async def stream():
        queue = asyncio.Queue()
        async def execute():
            async with limit:
                try:
                    result = await run_react_agent(body.message,provider,history=[m.model_dump() for m in body.history],baseline=body.baseline,emit=lambda e:queue.put_nowait({"type":"event","event":e}))
                    write_json(ROOT/"data/traces"/(result["run_id"]+".json"),result)
                    await queue.put({"type":"done","result":result})
                except Exception:
                    await queue.put({"type":"error","message":"Không thể hoàn tất phiên. Kiểm tra log máy chủ."})
                finally:
                    await queue.put(None)
        task = asyncio.create_task(execute())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield json.dumps(item,ensure_ascii=False)+"\n"
        finally:
            if not task.done():
                task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    return StreamingResponse(stream(),media_type="application/x-ndjson",headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--port",type=int,default=8000)
    args = parser.parse_args()
    uvicorn.run(app,host="127.0.0.1",port=args.port)
