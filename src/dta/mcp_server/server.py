"""kr-finance-mcp — 한국 공시·시세·뉴스를 LLM 도구로. 실행: python -m dta.mcp_server.server [--http]

Claude Code 에 붙이기: claude mcp add kr-finance -- /path/.venv/bin/python -m dta.mcp_server.server
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from dta.mcp_server import tools as T

INSTRUCTIONS = (
    "한국 상장사(코스피200) 사업보고서·재무·시세·ETF 구성종목·뉴스 도구. "
    "숫자 도구의 출력에는 단위(unit)·연결/별도(fs_div)·사업연도(fiscal_year)·출처(source)가 붙는다. "
    "오류 응답의 next 필드는 다음에 할 일을 말한다. 종목코드는 6자리 문자열이다."
)

mcp = FastMCP("kr-finance", instructions=INSTRUCTIONS)


@mcp.tool()
def search_companies(query: str) -> list[dict]:
    """회사명(일부) 또는 종목코드로 코스피200 기업을 찾는다. 반환: stock_code, corp_code, corp_name."""
    return T.search_companies(query)


@mcp.tool()
def get_financials(stock_code: str, fiscal_year: int, fs_div: str = "CFS") -> dict:
    """사업보고서 기준 연간 재무 6항목(매출액·영업이익·당기순이익·자산·자본·부채). fs_div: CFS=연결, OFS=별도.
    값은 억원(value_eok)과 원(value_won) 둘 다. 지주사·금융사는 연결이 없을 수 있으니 오류의 next 를 따른다."""
    return T.get_financials(stock_code, fiscal_year, fs_div)


@mcp.tool()
def list_filings(stock_code: str, fiscal_year: int | None = None) -> dict:
    """수집된 사업보고서 접수번호·접수일·파싱 상태를 돌려준다."""
    return T.list_filings(stock_code, fiscal_year)


@mcp.tool()
def get_report_section(
    stock_code: str, fiscal_year: int, sub_section: str | None = None, max_chars: int = 4000
) -> dict:
    """사업보고서 'II. 사업의 내용' 원문. sub_section 으로 '사업의 개요'·'주요 제품' 같은 소제목을 고를 수 있다. 출처(접수번호·URL) 포함."""
    return T.get_report_section(stock_code, fiscal_year, sub_section, max_chars)


@mcp.tool()
def search_report_text(query: str, k: int = 10, fiscal_year: int | None = None, mode: str = "hybrid") -> dict:
    """사업보고서 '사업의 내용' 전문 검색(의미+키워드). 반환: 청크 텍스트, 기업, 연도, 접수번호, 섹션 경로."""
    return T.search_report_text(query, k, fiscal_year, mode)


@mcp.tool()
def get_prices(stock_code: str, start: str, end: str) -> dict:
    """일봉 시세(원). 날짜는 YYYYMMDD."""
    return T.get_prices(stock_code, start, end)


@mcp.tool()
def get_etf_holdings(etf_ticker: str, date: str = "20261008") -> dict:
    """ETF 구성종목과 비중(%). 날짜 YYYYMMDD."""
    return T.get_etf_holdings(etf_ticker, date)


@mcp.tool()
def search_news(query: str, display: int = 10) -> dict:
    """네이버 뉴스 검색(최신순). 제목·요약·날짜·링크."""
    return T.search_news(query, display)


def main() -> None:
    if "--http" in sys.argv:
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
