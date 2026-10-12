"""복희식 게이트: 규칙을 어기면 테스트가 멈춘다.

1. LLM 클라이언트를 만드는 곳은 dta/llm.py 뿐. 다른 모듈은 get_chat_model() 만 쓴다 (AST 로 검사).
2. 숫자 도구(get_financials)의 출력에는 unit·fs_div·fiscal_year·source 가 반드시 있다.
"""

import ast
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "dta"
LLM_CLASSES = {"ChatGoogleGenerativeAI", "ChatVertexAI", "ChatOpenAI", "ChatAnthropic", "GenerativeModel"}


def test_llm_clients_are_constructed_only_in_llm_module():
    offenders = []
    for path in SRC.rglob("*.py"):
        if path.name == "llm.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
                if name in LLM_CLASSES:
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno} {name}")
            if isinstance(node, ast.ImportFrom) and node.module and "langchain_google" in node.module:
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno} import {node.module}")
    assert not offenders, offenders


def test_get_financials_output_contract(monkeypatch):
    from dta.mcp_server import tools

    fake = pd.DataFrame(
        {"account_id": ["ifrs-full_Revenue", "dart_OperatingIncomeLoss"], "account_nm": ["매출액", "영업이익"],
         "sj_div": ["IS", "IS"], "amount": [300_000_000_000, 30_000_000_000], "amount_prev": [None, None]}
    )
    monkeypatch.setattr(tools, "_manifest", lambda: pd.DataFrame({"stock_code": ["005930"], "corp_code": ["00126380"], "corp_name": ["삼성전자"]}))
    monkeypatch.setattr(tools, "fetch_financials", lambda client, corp, year, fs: fake)
    monkeypatch.setattr("dta.data.dart_client.DartClient.__init__", lambda self, api_key=None: None)
    out = tools.get_financials("005930", 2024, "CFS")
    for key in ("unit", "fs_div", "fiscal_year", "source"):
        assert key in out, key
    assert out["items"]["revenue"]["value_eok"] == 3000.0
    assert out["ratios"]["operating_margin_pct"] == 10.0
    bad = tools.get_financials("005930", 2024, "xyz")
    assert "error" in bad and "next" in bad
