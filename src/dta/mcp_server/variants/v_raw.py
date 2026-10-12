"""② 실험 변형 A: '날것' 서버 — DART 응답을 그대로 돌려준다. 도구 2개, 영문 키, 원 단위 문자열, 설명 최소.

실행: python -m dta.mcp_server.variants.v_raw
설계 C-3: 같은 데이터·같은 에이전트·같은 질문으로 본 서버(v_designed)와 정확도를 비교한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("kr-finance-raw", instructions="DART open API wrapper.")


@mcp.tool()
def dart_corp_code(corp_name: str) -> list[dict]:
    """corp_code lookup."""
    from dta.data.dart_client import DartClient

    df = DartClient().corp_codes()
    hit = df[(df["corp_name"].str.contains(corp_name, regex=False)) & (df["stock_code"].str.len() == 6)]
    return hit.head(10)[["corp_code", "corp_name", "stock_code"]].to_dict("records")


@mcp.tool()
def dart_fnltt(corp_code: str, bsns_year: str, fs_div: str = "CFS") -> list[dict]:
    """fnlttSinglAcntAll. reprt_code=11011."""
    from dta.data.dart_client import DartClient
    from dta.data.financials import fetch_financials

    df = fetch_financials(DartClient(), corp_code, int(bsns_year), fs_div)
    out = []
    for r in df.itertuples(index=False):
        amt = "" if r.amount is None or r.amount != r.amount else str(int(r.amount))
        prev = "" if r.amount_prev is None or r.amount_prev != r.amount_prev else str(int(r.amount_prev))
        out.append({"sj_div": r.sj_div, "account_id": r.account_id, "account_nm": r.account_nm, "thstrm_amount": amt, "frmtrm_amount": prev})
    return out


if __name__ == "__main__":
    mcp.run()
