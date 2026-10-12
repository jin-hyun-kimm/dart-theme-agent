"""CLI. 실행: PYTHONPATH=src .venv/bin/python -m dta.app.cli <명령>

theme "원전" --desc "원자력 발전 밸류체인 ..."   테마 바스켓 생성(확정 전 묻는다)
corpus                                         사업보고서 수집·파싱 (D1)
index [kure bge-m3]                            색인 (D2)
mcp [--http]                                   MCP 서버 실행
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from dta.config import RESULTS_DIR


def _print_basket(basket: list[dict]) -> None:
    w = max((len(j["corp_name"]) for j in basket), default=4)
    print(f"{'기업':<{w}}  판정  근거(앞 60자) · 출처")
    for j in basket:
        ev = (j["evidence"][:60] + "…") if len(j["evidence"]) > 60 else j["evidence"]
        src = f"[{j['rcept_no']} · {j['section_path'].split(' > ')[-1]}]" if j["rcept_no"] else ""
        print(f"{j['corp_name']:<{w}}  {j['label']}  {ev} {src}")
        if j["label"] == "모름":
            print(f"{'':<{w}}        └ {j['reason']}")


def cmd_theme(a: argparse.Namespace) -> int:
    from langgraph.types import Command

    from dta.graph.graph import build_graph

    graph = build_graph(with_gate=not a.no_gate)
    cfg = {"configurable": {"thread_id": f"cli-{int(time.time())}"}}
    state = {
        "theme_name": a.name,
        "theme_description": a.desc,
        "fiscal_year": a.year,
        "k_per_query": a.k,
        "top_chunks": a.top_chunks,
        "max_candidates": a.max_candidates,
    }
    t0 = time.time()
    out = graph.invoke(state, cfg)
    snap = graph.get_state(cfg).values
    basket = snap.get("basket", [])
    print(
        f"\n테마 「{a.name}」 · 후보 {len(snap.get('candidates', []))} · 판정 {len(basket)} · {time.time() - t0:.0f}s"
    )
    print("밸류체인 단계:", " / ".join(s["name"] for s in snap.get("stages", [])))
    _print_basket(basket)
    if "__interrupt__" in out:
        ans = input("\n이 바스켓을 확정할까요? [y/N] ").strip().lower()
        graph.invoke(Command(resume={"approve": ans == "y"}), cfg)
        snap = graph.get_state(cfg).values
    out_dir = Path(a.out or (RESULTS_DIR / "baskets"))
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{a.name}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(
        json.dumps({k: v for k, v in snap.items() if k != "candidates"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"저장: {path}")
    return 0


def cmd_corpus(_a: argparse.Namespace) -> int:
    import runpy

    runpy.run_path(
        str(Path(__file__).resolve().parents[3] / "scripts" / "build_corpus.py"), run_name="__main__"
    )
    return 0


def cmd_mcp(a: argparse.Namespace) -> int:
    from dta.mcp_server.server import mcp

    mcp.run(transport="streamable-http" if a.http else "stdio")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="dta", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("theme")
    t.add_argument("name")
    t.add_argument("--desc", required=True)
    t.add_argument("--year", type=int, default=None)
    t.add_argument("--k", type=int, default=20)
    t.add_argument("--top-chunks", type=int, default=3)
    t.add_argument("--max-candidates", type=int, default=60)
    t.add_argument("--no-gate", action="store_true")
    t.add_argument("--out", default=None)
    t.set_defaults(fn=cmd_theme)
    c = sub.add_parser("corpus")
    c.set_defaults(fn=cmd_corpus)
    i = sub.add_parser("index")
    i.add_argument("names", nargs="*", default=["kure", "bge-m3"])
    i.set_defaults(fn=lambda a: _index(a.names))
    m = sub.add_parser("mcp")
    m.add_argument("--http", action="store_true")
    m.set_defaults(fn=cmd_mcp)
    a = p.parse_args(argv)
    return a.fn(a)


def _index(names: list[str]) -> int:
    from dta.index.build import build_bm25, build_chunks, build_vectors

    chunks = build_chunks()
    build_bm25(chunks)
    for n in names:
        build_vectors(chunks, n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
