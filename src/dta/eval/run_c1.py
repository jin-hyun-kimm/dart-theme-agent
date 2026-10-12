"""C-1 테마 복원: 테마 5개 × 구성 3가지 → 정밀도·재현율·기권 (설계 §4-3).

R0 검색만      : '정의' 단계 검색어로 검색한 뒤 상위 N 기업을 그대로 바스켓으로 (검증 없음)
R1 검색+검증   : 그래프 전체 (정의→검색→검증→조립), 핵심·관련을 바스켓으로
R2 다중질의 없음: 정의 노드 없이 테마 설명 한 줄로만 검색 + 검증 (ablation)

실행: PYTHONPATH=src .venv/bin/python -m dta.eval.run_c1 [--embedder kure] [--mode hybrid] [--themes nuclear,defense]
산출: results/c1_baskets/{theme}_{config}.json · results/c1_theme_recovery.csv · results/stages/{theme}.json
"""

from __future__ import annotations

import argparse
import json
import time

import pandas as pd

from dta.config import RESULTS_DIR
from dta.eval.gold import build_gold
from dta.eval.metrics import basket_metrics
from dta.eval.themes import load_themes
from dta.graph.graph import build_graph
from dta.graph.nodes import make_retrieve
from dta.index.search import get_searcher

STAGES_DIR = RESULTS_DIR / "stages"
BASKETS_DIR = RESULTS_DIR / "c1_baskets"  # 기본(KURE hybrid). 다른 구성은 --baskets-dir 로 분리
R0_TOP_N = 15  # 검색만 구성의 바스켓 크기 (정답 평균 크기 ~9.4 의 1.5배)
MAX_CONCURRENCY = 8  # 검증 노드 병렬 LLM 호출 상한 (Vertex 한도·504 보호)


def _search_fn(embedder: str, mode: str):
    s = get_searcher(embedder, mode)
    return lambda q, k, fy: s.search(q, k=k, fiscal_year=fy)


def run_theme(
    theme, gold, embedder: str, mode: str, fiscal_year: int | None, k: int, top_chunks: int
) -> list[dict]:
    search_fn = _search_fn(embedder, mode)
    base = {
        "theme_name": theme.name,
        "theme_description": theme.description,
        "fiscal_year": fiscal_year,
        "k_per_query": k,
        "top_chunks": top_chunks,
        "max_candidates": 60,
    }
    rows = []

    # R1: 그래프 전체
    g = build_graph(search_fn=search_fn, with_gate=False)
    cfg = {"configurable": {"thread_id": f"c1-{theme.id}-R1"}, "max_concurrency": MAX_CONCURRENCY}
    t0 = time.time()
    out = g.invoke(dict(base), cfg)
    t_r1 = time.time() - t0
    stages = out.get("stages", [])
    STAGES_DIR.mkdir(parents=True, exist_ok=True)
    (STAGES_DIR / f"{theme.id}.json").write_text(
        json.dumps(stages, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _save(theme.id, "R1", out)
    rows.append(_row(theme, "R1 검색+검증", out["basket"], gold, t_r1, n_candidates=len(out["candidates"])))

    # R0: 같은 검색어로 검색만 → 상위 N 기업을 '핵심'으로 간주
    retrieve = make_retrieve(search_fn)
    cands = retrieve({**base, "stages": stages})["candidates"]
    r0_basket = [
        {
            "stock_code": c["stock_code"],
            "corp_name": c["corp_name"],
            "label": "핵심" if i < R0_TOP_N else "무관",
            "evidence": "",
            "evidence_verified": False,
            "reason": "검색 순위",
        }
        for i, c in enumerate(cands)
    ]
    _save(theme.id, "R0", {"basket": r0_basket, "stages": stages})
    rows.append(_row(theme, "R0 검색만", r0_basket, gold, 0.0, n_candidates=len(cands)))

    # R2: 정의 없이 테마 설명 한 줄로 검색 + 검증
    g2 = build_graph(search_fn=search_fn, with_gate=False)
    cfg2 = {"configurable": {"thread_id": f"c1-{theme.id}-R2"}, "max_concurrency": MAX_CONCURRENCY}
    t0 = time.time()
    # 정의 노드를 건너뛰고(skip_define) 테마 설명 한 줄을 유일한 검색어로 쓴다
    out2 = g2.invoke({**base, "skip_define": True, "stages": [{"name": "전체", "queries": [theme.description]}]}, cfg2)
    _save(theme.id, "R2", out2)
    rows.append(
        _row(
            theme,
            "R2 단일질의+검증",
            out2["basket"],
            gold,
            time.time() - t0,
            n_candidates=len(out2["candidates"]),
        )
    )
    return rows


def _save(theme_id: str, config: str, out: dict) -> None:
    BASKETS_DIR.mkdir(parents=True, exist_ok=True)
    slim = {k: v for k, v in out.items() if k != "candidates"}
    (BASKETS_DIR / f"{theme_id}_{config}.json").write_text(
        json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _row(theme, config: str, basket: list[dict], gold, seconds: float, n_candidates: int) -> dict:
    m = basket_metrics(basket, set(gold.in_universe))
    return {
        "theme": theme.name,
        "config": config,
        "n_gold_all": len(gold.all_tickers),
        "n_excluded": gold.n_excluded,
        "n_candidates": n_candidates,
        "seconds": round(seconds, 1),
        **m,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--embedder", default="kure")
    ap.add_argument("--mode", default="hybrid")
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--top-chunks", type=int, default=3)
    ap.add_argument("--themes", default="")
    ap.add_argument("--baskets-dir", default="c1_baskets")
    a = ap.parse_args()
    global BASKETS_DIR
    BASKETS_DIR = RESULTS_DIR / a.baskets_dir
    date, themes = load_themes()
    if a.themes:
        want = set(a.themes.split(","))
        themes = [t for t in themes if t.id in want]
    rows = []
    for t in themes:
        gold = build_gold(t, date)
        print(
            f"\n=== {t.name} ({t.etf_name}) 정답 {len(gold.in_universe)}/{len(gold.all_tickers)} ===",
            flush=True,
        )
        rows.extend(run_theme(t, gold, a.embedder, a.mode, a.year, a.k, a.top_chunks))
        for r in rows[-3:]:
            print(
                {
                    k: r[k]
                    for k in (
                        "config",
                        "n_predicted",
                        "n_tp",
                        "precision",
                        "recall",
                        "n_unknown",
                        "abstain_correct",
                        "seconds",
                    )
                },
                flush=True,
            )
    df = pd.DataFrame(rows)
    out = RESULTS_DIR / f"c1_theme_recovery_{a.embedder}_{a.mode}.csv"
    df.to_csv(out, index=False)
    summary = df.groupby("config")[["precision", "recall", "abstain_rate", "abstain_correct"]].mean().round(3)
    print("\n" + summary.to_string())
    (RESULTS_DIR / f"c1_summary_{a.embedder}_{a.mode}.md").write_text(summary.to_markdown(), encoding="utf-8")


if __name__ == "__main__":
    main()
