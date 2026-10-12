"""테마별 진단: 정답 기업이 몇 위에 잡혔는지, 놓친 기업은 왜 놓쳤는지(그 기업 청크에 검색어가 있기나 한지).

실행: PYTHONPATH=src .venv/bin/python scripts/diagnose_theme.py --theme nuclear --mode bm25 [--embedder kure]
"""

from __future__ import annotations

import argparse

from dta.data.universe import load_universe
from dta.eval.gold import build_gold
from dta.eval.run_c2 import theme_queries
from dta.eval.themes import load_themes
from dta.index.search import Searcher, aggregate_by_company


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", required=True)
    ap.add_argument("--mode", default="bm25")
    ap.add_argument("--embedder", default="kure")
    ap.add_argument("--k", type=int, default=60)
    a = ap.parse_args()
    date, themes = load_themes()
    t = next(x for x in themes if x.id == a.theme)
    gold = build_gold(t, date)
    names = dict(zip(load_universe(date)["ticker"], load_universe(date)["name"], strict=True))
    s = Searcher(a.embedder, a.mode)
    queries = theme_queries(t.id, t.description)
    hits = []
    for q in queries:
        hits.extend(s.search(q, k=a.k))
    comps = aggregate_by_company(hits, top_chunks=1)
    rank = {c.stock_code: i + 1 for i, c in enumerate(comps)}
    print(f"[{t.name}] {t.etf_name} · 정답 {len(gold.in_universe)} (범위 밖 {gold.n_excluded}) · 질의 {len(queries)} · 후보 기업 {len(comps)}")
    print("\n정답 기업 (비중순) → 기업 순위")
    for tk in sorted(gold.in_universe, key=lambda x: -gold.weights.get(x, 0)):
        r = rank.get(tk)
        print(f"  {'O' if r and r <= 30 else 'x'} {names.get(tk, tk):<14} {gold.weights.get(tk, 0):5.1f}%  순위 {r if r else '-'}")
    print("\n상위 15 후보 (정답 여부)")
    for c in comps[:15]:
        mark = "★" if c.stock_code in gold.in_universe else " "
        h = c.hits[0]
        print(f"  {mark} {c.corp_name:<14} best_rank={c.best_rank:<3} {h.chunk.section_path.split(' > ')[-1][:18]:<18} {h.chunk.text[:70].replace(chr(10), ' ')}")


if __name__ == "__main__":
    main()
