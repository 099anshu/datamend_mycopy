"""MCP server exposing SkyGuard tools. Run: python mcp_server/server.py  (stdio transport)
Claude Desktop config:  {"mcpServers":{"skyguard":{"command":"/ABS/PATH/.venv/bin/python","args":["/ABS/PATH/SkyGuard-AI/mcp_server/server.py"]}}}"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT); os.chdir(ROOT)
from mcp.server.fastmcp import FastMCP
from skyguard.pipeline import Pipeline, TOOLS
mcp, S = FastMCP("skyguard"), {"p": Pipeline("demo")}

@mcp.tool()
def load_weather_data(source: str = "demo") -> dict:
    """Load a dataset: demo | uscrn | imd_tmax | imd_rain."""
    S["p"] = Pipeline(source); return S["p"].load_weather_data()

def _make(name):
    def f() -> dict:
        return getattr(S["p"], name)()
    f.__name__ = name; f.__doc__ = f"SkyGuard pipeline step: {name}. Call steps in order after load_weather_data."; return f
for n in TOOLS[1:]: mcp.tool(name=n)(_make(n))
if __name__ == "__main__": mcp.run()
