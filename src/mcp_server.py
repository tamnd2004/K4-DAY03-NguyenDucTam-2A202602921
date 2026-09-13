"""Real MCP over stdio. stdout is reserved for JSON-RPC messages."""
import argparse
import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool
from tools import TOOLS_SCHEMA, dispatch_tool_call

server = Server("peopleops-hr-mcp", version="1.0.0")

@server.list_tools()
async def list_tools():
    return [Tool(name=t["name"], description=t["description"], inputSchema=t["parameters"]) for t in TOOLS_SCHEMA]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    result = await asyncio.to_thread(dispatch_tool_call, name, arguments)
    return CallToolResult(content=[TextContent(type="text", text=result)], isError=json.loads(result).get("status") not in {"SUCCESS","ALREADY_EXISTS"})

async def serve():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true")
    if parser.parse_args().stdio:
        asyncio.run(serve())
    else:
        print("MCP Server: peopleops-hr-mcp v1.0.0 | Transport: stdio | 4 tools")
        print(json.dumps(TOOLS_SCHEMA, ensure_ascii=True, indent=2))
        print("Run: python src/mcp_server.py --stdio (or src/app.py / src/web.py)")
