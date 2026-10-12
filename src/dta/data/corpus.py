"""말뭉치 구축: 유니버스 → 고유번호 → 사업보고서 → 원문 → '사업의 내용' 문단. 재실행 가능(매니페스트 기준).

산출:
- data/cache/corpus_manifest.csv : stock_code, corp_code, corp_name, fiscal_year, rcept_no, rcept_dt, status(ok|fail), reason, n_paras, n_chars
- data/cache/paras/{rcept_no}.jsonl : Paragraph 한 줄씩
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict

import pandas as pd

from dta.config import CACHE_DIR, FISCAL_YEARS
from dta.data.dart_client import DartClient
from dta.data.report_parser import Paragraph, ParseFailure, extract_section

MANIFEST = CACHE_DIR / "corpus_manifest.csv"
PARAS_DIR = CACHE_DIR / "paras"
COLUMNS = [
    "stock_code",
    "corp_code",
    "corp_name",
    "fiscal_year",
    "rcept_no",
    "rcept_dt",
    "status",
    "reason",
    "n_paras",
    "n_chars",
]


def load_manifest() -> pd.DataFrame:
    if MANIFEST.exists():
        return pd.read_csv(MANIFEST, dtype={"stock_code": str, "corp_code": str, "rcept_no": str}).fillna("")
    return pd.DataFrame(columns=COLUMNS)


def load_paragraphs(rcept_no: str) -> list[Paragraph]:
    path = PARAS_DIR / f"{rcept_no}.jsonl"
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            out.append(Paragraph(**json.loads(line)))
    return out


def _save_paragraphs(rcept_no: str, paras: list[Paragraph]) -> None:
    PARAS_DIR.mkdir(parents=True, exist_ok=True)
    with open(PARAS_DIR / f"{rcept_no}.jsonl", "w", encoding="utf-8") as f:
        for p in paras:
            f.write(json.dumps(asdict(p), ensure_ascii=False) + "\n")


def build_corpus(
    client: DartClient, universe: pd.DataFrame, fiscal_years=FISCAL_YEARS, log=sys.stderr
) -> pd.DataFrame:
    man = load_manifest()
    done = {(r.stock_code, int(r.fiscal_year)) for r in man.itertuples() if r.status == "ok"}
    rows: list[dict] = man.to_dict("records")
    total = len(universe) * len(fiscal_years)
    i = 0
    for u in universe.itertuples():
        stock_code, name = str(u.ticker), str(u.name)
        corp_code = client.corp_code_for(stock_code)
        for fy in fiscal_years:
            i += 1
            if (stock_code, fy) in done:
                continue
            rows = [r for r in rows if not (r["stock_code"] == stock_code and int(r["fiscal_year"]) == fy)]
            row = {
                "stock_code": stock_code,
                "corp_code": corp_code or "",
                "corp_name": name,
                "fiscal_year": fy,
                "rcept_no": "",
                "rcept_dt": "",
                "status": "fail",
                "reason": "",
                "n_paras": 0,
                "n_chars": 0,
            }
            try:
                if not corp_code:
                    raise ParseFailure("no_corp_code", stock_code)
                refs = client.annual_reports(corp_code, fy)
                if not refs:
                    raise ParseFailure("no_report", f"{name} {fy}")
                try:
                    ref, path = client.fetch_first_available(refs)
                except ValueError as e:
                    raise ParseFailure("no_document_file", str(e)[:80]) from e
                row["rcept_no"], row["rcept_dt"], row["corp_name"] = ref.rcept_no, ref.rcept_dt, ref.corp_name
                paras = extract_section(path.read_text(encoding="utf-8"))
                _save_paragraphs(ref.rcept_no, paras)
                row.update(status="ok", n_paras=len(paras), n_chars=sum(len(p.text) for p in paras))
            except ParseFailure as e:
                row["reason"] = e.reason
            except Exception as e:  # noqa: BLE001 — 한 건의 실패가 전체를 멈추면 안 된다. 사유를 남긴다
                row["reason"] = f"error:{type(e).__name__}"
            rows.append(row)
            if i % 20 == 0:
                print(f"  {i}/{total} {name} {fy} → {row['status']} {row['reason']}", file=log, flush=True)
                pd.DataFrame(rows, columns=COLUMNS).to_csv(MANIFEST, index=False)
    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_csv(MANIFEST, index=False)
    return df


def summarize(man: pd.DataFrame) -> pd.DataFrame:
    """D1 표: 상태·사유별 건수. 분모는 유니버스×연도."""
    g = man.groupby(["status", "reason"], dropna=False).size().reset_index(name="n")
    g["share"] = (g["n"] / len(man)).round(3)
    return g.sort_values("n", ascending=False)
