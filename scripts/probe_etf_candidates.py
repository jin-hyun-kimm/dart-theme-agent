"""D1: 테마 ETF 후보의 코스피200 포함률을 재서 5개를 고르기 위한 표를 만든다.

실행: .venv/bin/python scripts/probe_etf_candidates.py
출력: results/d1_etf_candidates.csv (전 후보), 화면에 상위 30개
"""

from __future__ import annotations

import sys
import time

import pandas as pd

from dta.config import RESULTS_DIR, UNIVERSE_DATE
from dta.data.etf import coverage, holdings, list_etfs, theme_candidates
from dta.data.universe import load_universe


def main() -> int:
    date = UNIVERSE_DATE
    uni = load_universe(date)
    uni_set = set(uni["ticker"])
    print(f"코스피200 구성종목: {len(uni)} (기준일 {date})")

    etfs = list_etfs(date)
    cands = theme_candidates(etfs)
    print(f"ETF 전체 {len(etfs)} → 테마 후보 {len(cands)} (키워드 필터)")

    rows = []
    for i, r in cands.iterrows():
        try:
            h = holdings(r["ticker"], date)
        except Exception as e:  # noqa: BLE001 — 후보 하나 실패가 전체를 막으면 안 된다
            rows.append({"ticker": r["ticker"], "name": r["name"], "error": type(e).__name__})
            continue
        c = coverage(h, uni_set)
        rows.append({"ticker": r["ticker"], "name": r["name"], **c})
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(cands)} ...", file=sys.stderr)
        time.sleep(0.3)

    df = pd.DataFrame(rows)
    out = RESULTS_DIR / "d1_etf_candidates.csv"
    df.to_csv(out, index=False)
    ok = df[df.get("error").isna()] if "error" in df.columns else df
    ok = ok[ok["n_total"] >= 8].sort_values(["ratio_count", "n_in_universe"], ascending=False)
    cols = ["ticker", "name", "n_total", "n_in_universe", "n_excluded", "ratio_count", "ratio_weight"]
    pd.set_option("display.width", 200)
    pd.set_option("display.max_rows", 60)
    print(ok[cols].head(40).to_string(index=False))
    print(
        f"\n저장: {out}  (후보 {len(df)}, 실패 {df['error'].notna().sum() if 'error' in df.columns else 0})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
