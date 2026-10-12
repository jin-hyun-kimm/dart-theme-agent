"""C-1 근거 정확도용 표본: R1 바스켓의 '핵심·관련' 근거 문장 30개를 무작위로 뽑아 사람이 읽을 마크다운을 만든다.

실행: PYTHONPATH=src .venv/bin/python scripts/sample_evidence.py [--n 30] [--seed 1]
출력: results/c1_evidence_sample.md — 진현이 각 항목에 O/X 를 적고 scripts/score_evidence.py 로 집계한다.
"""

from __future__ import annotations

import argparse
import json
import random

from dta.config import RESULTS_DIR
from dta.eval.gold import build_gold
from dta.eval.themes import load_themes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    date, themes = load_themes()
    items = []
    for t in themes:
        p = RESULTS_DIR / "c1_baskets" / f"{t.id}_R1.json"
        if not p.exists():
            continue
        gold = build_gold(t, date).in_universe
        for j in json.loads(p.read_text(encoding="utf-8"))["basket"]:
            if j["label"] in ("핵심", "관련") and j["evidence"]:
                items.append((t.name, j, j["stock_code"] in gold))
    rnd = random.Random(a.seed)
    rnd.shuffle(items)
    sample = items[: a.n]
    lines = ["# 근거 문장 표본 (사람 채점)", "",
             f"표본 {len(sample)} / 핵심·관련 판정 전체 {len(items)}. 각 항목의 `판정:` 뒤에 O(근거가 소속을 뒷받침) 또는 X 를 적는다.", ""]
    for i, (theme, j, in_gold) in enumerate(sample, 1):
        lines += [f"## {i}. [{theme}] {j['corp_name']} — {j['label']} (ETF 정답: {'예' if in_gold else '아니오'})",
                  f"> {j['evidence']}", "", f"출처: 접수번호 {j['rcept_no']} · {j['section_path']}", f"이유: {j['reason']}", "", "판정: ", ""]
    out = RESULTS_DIR / "c1_evidence_sample.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(sample)} 항목 → {out}")


if __name__ == "__main__":
    main()
