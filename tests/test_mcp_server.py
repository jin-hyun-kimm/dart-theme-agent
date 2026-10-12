"""MCP 서버를 stdio 로 띄워 실제 클라이언트로 도구 목록·호출을 확인한다."""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_TOOLS = {
    "search_companies",
    "get_financials",
    "list_filings",
    "get_report_section",
    "search_report_text",
    "get_prices",
    "get_etf_holdings",
    "search_news",
}


async def _run():
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "dta.mcp_server.server"], cwd=str(ROOT)
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            r = await session.call_tool("search_companies", {"query": ""})
            r2 = await session.call_tool(
                "get_financials", {"stock_code": "005930", "fiscal_year": 2024, "fs_div": "XXX"}
            )
            return names, r, r2


def test_server_lists_tools_and_returns_structured_errors():
    names, r, r2 = asyncio.run(_run())
    assert REQUIRED_TOOLS <= names, REQUIRED_TOOLS - names
    assert not r.isError
    body = json.loads(r2.content[0].text)
    assert "error" in body and "next" in body  # 설계: 실패는 next 를 가진 오류 객체
