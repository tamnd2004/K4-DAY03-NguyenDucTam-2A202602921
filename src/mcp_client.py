"""MCP initialization, schema discovery and tool calls through a child process."""
import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class HRMCPClient:
    def __init__(self, session, schemas):
        self.session, self.schemas = session, schemas

    async def call_tool(self, name, arguments):
        result = await self.session.call_tool(name, arguments)
        texts = [p.text for p in result.content if p.type == "text"]
        try:
            return json.loads("\n".join(texts))
        except (ValueError,TypeError):
            return {"status":"TOOL_ERROR", "message":"\n".join(texts)[:1000]}

@asynccontextmanager
async def connect_mcp(db_path=None):
    env = {k:v for k,v in os.environ.items() if k.upper() in {"PATH","SYSTEMROOT","WINDIR","TEMP","TMP","COMSPEC","PATHEXT","USERPROFILE"}}
    env["PYTHONIOENCODING"] = "utf-8"
    if db_path or os.getenv("HR_DB_PATH"):
        env["HR_DB_PATH"] = str(db_path or os.environ["HR_DB_PATH"])
    params = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).with_name("mcp_server.py")),"--stdio"], env=env)
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=30)) as session:
            await session.initialize()
            discovery = await session.list_tools()
            schemas = [{"name":t.name,"description":t.description,"parameters":t.inputSchema} for t in discovery.tools]
            yield HRMCPClient(session,schemas)
