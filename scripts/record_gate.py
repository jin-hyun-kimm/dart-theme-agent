"""인간 게이트 실행 기록: 그래프가 interrupt 에서 멈춘 상태와, 승인 뒤 확정된 상태를 JSON 으로 남긴다.

실행: PYTHONPATH=src .venv/bin/python scripts/record_gate.py --theme defense --max-candidates 25
"""

from __future__ import annotations

import argparse
import json
import time

from langgraph.types import Command

from dta.config import RESULTS_DIR
from dta.eval.themes import load_themes
from dta.graph.graph import build_graph


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", default="defense")
    ap.add_argument("--max-candidates", type=int, default=25)
    a = ap.parse_args()
    _, themes = load_themes()
    t = next(x for x in themes if x.id == a.theme)
    graph = build_graph(with_gate=True)
    cfg = {"configurable": {"thread_id": f"gate-{int(time.time())}"}, "max_concurrency": 8}
    t0 = time.time()
    out = graph.invoke({"theme_name": t.name, "theme_description": t.description, "k_per_query": 20, "top_chunks": 3, "max_candidates": a.max_candidates}, cfg)
    paused = graph.get_state(cfg)
    rec = {"theme": t.name, "config": cfg["configurable"], "seconds_to_gate": round(time.time() - t0, 1),
           "interrupt_payload": [i.value for i in out.get("__interrupt__", [])], "paused_next_nodes": list(paused.next),
           "basket_at_gate": paused.values.get("basket"), "approved_before": paused.values.get("approved")}
    out2 = graph.invoke(Command(resume={"approve": True}), cfg)
    after = graph.get_state(cfg)
    rec.update({"resume_command": {"approve": True}, "approved_after": out2.get("approved"), "next_after": list(after.next), "seconds_total": round(time.time() - t0, 1)})
    p = RESULTS_DIR / "gate_record.json"
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(p, "interrupt:", rec["interrupt_payload"], "approved:", rec["approved_after"], "next:", rec["next_after"])


if __name__ == "__main__":
    main()
