"""C-3 도구 설계 실험: 서버 변형 2개 × 질문 100개 × 같은 에이전트(단일 ReAct, 같은 모델·같은 프롬프트).

변형: raw(날것: 도구 2개·영문 키·원 단위 문자열) vs designed(본 서버: 도구 분리·한국어 설명·억원 정규화·unit 필드·next 오류)
측정: 정확도 · 평균 도구 호출 수 · 평균 토큰 · 실패 유형 분포
실행: PYTHONPATH=src .venv/bin/python -m dta.eval.run_c3 [--variants raw,designed] [--limit 100]
산출: results/c3_answers_{variant}.jsonl · results/c3_tool_design.csv · results/c3_summary.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import Counter

import pandas as pd
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from dta.config import RESULTS_DIR, ROOT
from dta.eval.grade import grade
from dta.eval.questions import load as load_questions
from dta.llm import get_chat_model

VARIANTS = {
    "raw": ["-m", "dta.mcp_server.variants.v_raw"],
    "designed": ["-m", "dta.mcp_server.server"],
}
SYSTEM = (
    "너는 한국 상장사 재무 질문에 답하는 분석 보조다. 반드시 제공된 도구로 조회한 값만 써서 답하라. "
    "최종 답은 한 문장으로, 금액은 '억원' 단위(예: 1조 2,345억원 또는 12,345억원), 비율은 % 로, 비교 질문은 회사명으로 답하라. "
    "도구가 오류를 돌려주면 그 안내를 따라 다시 시도하라. 조회로 확인되지 않으면 '확인할 수 없음'이라고 답하라."
)


def _usage(messages) -> tuple[int, int, int]:
    """(입력 토큰, 출력 토큰, 도구 호출 수)"""
    tin = tout = calls = 0
    for m in messages:
        t = getattr(m, "type", "")
        if t == "ai":
            u = getattr(m, "usage_metadata", None) or {}
            tin += int(u.get("input_tokens", 0) or 0)
            tout += int(u.get("output_tokens", 0) or 0)
            calls += len(getattr(m, "tool_calls", []) or [])
    return tin, tout, calls


async def run_variant(variant: str, questions, max_steps: int = 8) -> list[dict]:
    client = MultiServerMCPClient(
        {variant: {"command": sys.executable, "args": VARIANTS[variant], "transport": "stdio", "cwd": str(ROOT)}}
    )
    out_path = RESULTS_DIR / f"c3_answers_{variant}.jsonl"
    done = {}
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            done[d["qid"]] = d
    rows = list(done.values())
    async with client.session(variant) as session:
        tools = await load_mcp_tools(session)
        agent = create_agent(get_chat_model(), tools, system_prompt=SYSTEM)
        with open(out_path, "a", encoding="utf-8") as f:
            for q in questions:
                if q.qid in done:
                    continue
                t0 = time.time()
                try:
                    res = await agent.ainvoke(
                        {"messages": [{"role": "user", "content": q.text}]}, config={"recursion_limit": 2 * max_steps + 1}
                    )
                    msgs = res["messages"]
                    answer = msgs[-1].content if isinstance(msgs[-1].content, str) else json.dumps(msgs[-1].content, ensure_ascii=False)
                    err = ""
                except Exception as e:  # noqa: BLE001 — 실패도 한 행이다
                    msgs, answer, err = [], "", f"{type(e).__name__}: {str(e)[:120]}"
                tin, tout, calls = _usage(msgs)
                g = grade(q, answer)
                row = {"variant": variant, "qid": q.qid, "qtype": q.qtype, "question": q.text, "answer": answer[:400],
                       "correct": bool(g["correct"]), "fail_type": g["fail_type"] if not g["correct"] else None,
                       "got": str(g["got"])[:80], "gold": q.gold_won, "tool_calls": calls, "tokens_in": tin, "tokens_out": tout,
                       "seconds": round(time.time() - t0, 1), "error": err}
                rows.append(row)
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                print(f"[{variant}] {q.qid} {'O' if row['correct'] else 'X'} calls={calls} {row['seconds']}s {row['fail_type'] or ''} {err}", flush=True)
    return rows


def summarize(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    s = df.groupby("variant").agg(
        n=("qid", "count"), accuracy=("correct", "mean"), tool_calls=("tool_calls", "mean"),
        tokens_in=("tokens_in", "mean"), tokens_out=("tokens_out", "mean"), seconds=("seconds", "mean"),
    ).round(3)
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default="raw,designed")
    ap.add_argument("--limit", type=int, default=100)
    a = ap.parse_args()
    questions = load_questions()[: a.limit]
    rows: list[dict] = []
    for v in a.variants.split(","):
        rows.extend(asyncio.run(run_variant(v, questions)))
    df = pd.DataFrame(rows)
    df.to_csv(RESULTS_DIR / "c3_tool_design.csv", index=False)
    s = summarize(rows)
    print("\n" + s.to_string())
    fails = df[~df["correct"]].groupby(["variant", "fail_type"]).size().unstack(fill_value=0)
    by_type = df.groupby(["variant", "qtype"])["correct"].mean().unstack().round(3)
    md = "## 전체\n\n" + s.to_markdown() + "\n\n## 유형별 정확도\n\n" + by_type.to_markdown() + "\n\n## 실패 유형\n\n" + fails.to_markdown() + "\n"
    (RESULTS_DIR / "c3_summary.md").write_text(md, encoding="utf-8")
    print("\n" + by_type.to_string())
    print("\n" + fails.to_string())
    for _, r in df[~df["correct"]].head(5).iterrows():
        print(f"\n[{r['variant']}] {r['question']}\n → {r['answer'][:200]} (gold {r['gold']}, {r['fail_type']})")
    Counter(df["fail_type"].dropna())


if __name__ == "__main__":
    main()
