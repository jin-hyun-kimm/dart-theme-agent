"""C-3 질문 하나를 서버 변형에 돌려 도구 호출·응답 원문·최종 답을 전부 기록한다 (포트폴리오 증거용).

실행: PYTHONPATH=src .venv/bin/python scripts/trace_c3.py --qid single_cfs001 --variant raw --attempts 3 --out results/traces
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from dta.config import ROOT
from dta.eval.grade import grade
from dta.eval.questions import load as load_questions
from dta.eval.run_c3 import SYSTEM, VARIANTS, _text
from dta.llm import get_chat_model


async def run(q, variant: str, attempts: int, out_dir: Path) -> None:
    client = MultiServerMCPClient({variant: {"command": sys.executable, "args": VARIANTS[variant], "transport": "stdio", "cwd": str(ROOT)}})
    async with client.session(variant) as session:
        agent = create_agent(get_chat_model(), await load_mcp_tools(session), system_prompt=SYSTEM)
        for n in range(1, attempts + 1):
            t0 = time.time()
            trace = []
            err = ""
            try:
                res = await agent.ainvoke({"messages": [{"role": "user", "content": q.text}]}, config={"recursion_limit": 17})
                for m in res["messages"]:
                    if m.type == "human":
                        trace.append({"role": "user", "text": m.content})
                    elif m.type == "ai":
                        trace.append({"role": "assistant", "text": _text(m.content), "tool_calls": [{"name": tc["name"], "args": tc["args"]} for tc in (getattr(m, "tool_calls", None) or [])]})
                    elif m.type == "tool":
                        body = _text(m.content)
                        trace.append({"role": "tool", "name": m.name, "chars": len(body), "result": body})
                answer = _text(res["messages"][-1].content)
            except Exception as e:  # noqa: BLE001
                err, answer = f"{type(e).__name__}: {str(e)[:200]}", ""
            g = grade(q, answer)
            rec = {"qid": q.qid, "variant": variant, "attempt": n, "question": q.text, "gold": q.gold_won, "gold_kind": q.gold_kind,
                   "answer": answer, "correct": bool(g["correct"]), "fail_type": None if g["correct"] else g["fail_type"], "error": err,
                   "seconds": round(time.time() - t0, 1), "trace": trace}
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"{q.qid}_{variant}_{n}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[{variant}] {q.qid} attempt {n}: {'O' if rec['correct'] else 'X'} {rec['fail_type'] or ''} {err}", flush=True)
            if not rec["correct"] and variant == "raw":
                break  # 실패 기록을 얻었으면 멈춘다


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qid", required=True)
    ap.add_argument("--variant", default="raw")
    ap.add_argument("--attempts", type=int, default=3)
    ap.add_argument("--out", default="results/traces")
    a = ap.parse_args()
    q = next(x for x in load_questions() if x.qid == a.qid)
    asyncio.run(run(q, a.variant, a.attempts, ROOT / a.out))


if __name__ == "__main__":
    main()
