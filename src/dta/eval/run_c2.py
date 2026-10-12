"""C-2 검색 품질: 임베딩 2종 × {dense, hybrid} × 테마 → 기업 단위 Recall@10/@30. LLM 없음.

질의 = 테마 설명 1개 + (있으면) 캐시된 밸류체인 단계 검색어(results/stages/{theme_id}.json — 그래프의 '정의' 노드가 저장).
실행: PYTHONPATH=src .venv/bin/python -m dta.eval.run_c2
"""

from __future__ import annotations

import json
import time

import pandas as pd

from dta.config import RESULTS_DIR
from dta.eval.gold import build_gold
from dta.eval.metrics import recall_at_k
from dta.eval.themes import load_themes
from dta.index.search import Searcher, aggregate_by_company

STAGES_DIR = RESULTS_DIR / "stages"


def theme_queries(theme_id: str, description: str) -> list[str]:
    qs = [description]
    p = STAGES_DIR / f"{theme_id}.json"
    if p.exists():
        for s in json.loads(p.read_text(encoding="utf-8")):
            qs.extend(s["queries"])
    return qs


def company_ranking(
    searcher: Searcher, queries: list[str], k: int = 60, fiscal_year: int | None = None
) -> list[str]:
    hits = []
    for q in queries:
        hits.extend(searcher.search(q, k=k, fiscal_year=fiscal_year))
    return [c.stock_code for c in aggregate_by_company(hits, top_chunks=1)]


def main(
    embedders=("kure", "bge-m3"), modes=("dense", "hybrid"), fiscal_year: int | None = None
) -> pd.DataFrame:
    date, themes = load_themes()
    golds = {t.id: build_gold(t, date) for t in themes}
    rows = []
    seen_bm25 = False
    for emb in embedders:
        for mode in modes:
            if mode == "bm25":
                if seen_bm25:
                    continue  # BM25 는 임베딩과 무관 → 한 번만
                seen_bm25 = True
            s = Searcher(emb, mode)
            for t in themes:
                t0 = time.time()
                ranking = company_ranking(s, theme_queries(t.id, t.description), fiscal_year=fiscal_year)
                m = recall_at_k(ranking, set(golds[t.id].in_universe))
                rows.append(
                    {"embedder": "-" if mode == "bm25" else emb,
                        "mode": mode,
                        "theme": t.name,
                        "n_excluded": golds[t.id].n_excluded,
                        "latency_s": round(time.time() - t0, 2),
                        **m,
                    }
                )
                print(rows[-1], flush=True)
    df = pd.DataFrame(rows)
    out = RESULTS_DIR / "c2_retrieval.csv"
    if out.exists():  # 임베딩별로 따로 돌려도 한 표에 모인다 (같은 embedder·mode·theme 는 새 결과로 교체)
        old = pd.read_csv(out)
        key = ["embedder", "mode", "theme"]
        old = old.merge(df[key].drop_duplicates(), on=key, how="left", indicator=True)
        old = old[old["_merge"] == "left_only"].drop(columns="_merge")
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(out, index=False)
    summary = df.groupby(["embedder", "mode"])[["recall@10", "recall@30"]].mean().round(3)
    print(summary.to_string())
    (RESULTS_DIR / "c2_retrieval_summary.md").write_text(summary.to_markdown(), encoding="utf-8")
    return df


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--embedders", default="kure,bge-m3")
    ap.add_argument("--modes", default="bm25,dense,hybrid")
    ap.add_argument("--year", type=int, default=None)
    a = ap.parse_args()
    main(tuple(a.embedders.split(",")), tuple(a.modes.split(",")), a.year)
