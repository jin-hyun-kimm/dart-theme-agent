"""결과표 조립: results/ 의 CSV 를 읽어 README 에 붙일 마크다운(results/REPORT.md)을 만든다. 숫자마다 분모를 적는다.

실행: PYTHONPATH=src .venv/bin/python -m dta.eval.report
"""

from __future__ import annotations

import pandas as pd

from dta.config import RESULTS_DIR
from dta.data.corpus import load_manifest


def _pct(x) -> str:
    return "—" if x is None or pd.isna(x) else f"{x * 100:.0f}%"


def corpus_table() -> str:
    man = load_manifest()
    if len(man) == 0:
        return "_말뭉치 없음_"
    ok = man[man["status"] == "ok"]
    lines = [f"- 대상: 코스피200 {man['stock_code'].nunique()}개사 × 사업연도 {sorted(int(y) for y in man['fiscal_year'].unique())} = {len(man)}건",
             f"- '사업의 내용' 추출 성공: **{len(ok)}/{len(man)}** ({_pct(len(ok) / len(man))}) · 문단 {int(ok['n_paras'].sum()):,} · 글자 {int(ok['n_chars'].sum()):,}"]
    fails = man[man["status"] != "ok"].groupby("reason").size()
    if len(fails):
        lines.append("- 실패 사유: " + ", ".join(f"{k} {v}" for k, v in fails.items()))
    return "\n".join(lines)


def c2_table() -> str:
    p = RESULTS_DIR / "c2_retrieval.csv"
    if not p.exists():
        return "_C-2 미실행_"
    df = pd.read_csv(p)
    s = df.groupby(["embedder", "mode"]).agg(recall10=("recall@10", "mean"), recall30=("recall@30", "mean"), latency=("latency_s", "mean")).reset_index()
    rows = ["| 임베딩 | 검색 | Recall@10 | Recall@30 | 지연(s) |", "|---|---|---|---|---|"]
    for r in s.itertuples():
        rows.append(f"| {r.embedder} | {r.mode} | {_pct(r.recall10)} | {_pct(r.recall30)} | {r.latency:.1f} |")
    n_gold = int(df.groupby("theme")["n_gold"].first().sum())
    rows.append(f"\n테마 {df['theme'].nunique()}개 평균. 분모 = 정답 구성종목 중 코스피200에 든 수(합 {n_gold}). 뺀 수 합 {int(df.groupby('theme')['n_excluded'].first().sum())}.")
    return "\n".join(rows)


def c1_table() -> str:
    ps = sorted(RESULTS_DIR.glob("c1_theme_recovery_*.csv"))
    if not ps:
        return "_C-1 미실행_"
    out = []
    for p in ps:
        df = pd.read_csv(p)
        tag = p.stem.replace("c1_theme_recovery_", "")
        s = df.groupby("config").agg(precision=("precision", "mean"), recall=("recall", "mean"), abstain=("abstain_rate", "mean"),
                                     abstain_ok=("abstain_correct", "mean"), n_pred=("n_predicted", "mean"), sec=("seconds", "mean")).reset_index()
        rows = [f"**{tag}**", "", "| 구성 | 정밀도 | 재현율 | 기권률 | 기권 적중 | 바스켓 크기 | 초 |", "|---|---|---|---|---|---|---|"]
        for r in s.itertuples():
            rows.append(f"| {r.config} | {_pct(r.precision)} | {_pct(r.recall)} | {_pct(r.abstain)} | {_pct(r.abstain_ok)} | {r.n_pred:.1f} | {r.sec:.0f} |")
        rows.append(f"\n테마 {df['theme'].nunique()}개 평균. 정답 합 {int(df.groupby('theme')['n_gold'].first().sum())}, 뺀 수 합 {int(df.groupby('theme')['n_excluded'].first().sum())}.")
        per = df.pivot_table(index="theme", columns="config", values="recall").round(2)
        rows.append("\n테마별 재현율:\n\n" + per.to_markdown())
        out.append("\n".join(rows))
    return "\n\n".join(out)


def c3_table() -> str:
    p = RESULTS_DIR / "c3_summary.md"
    return p.read_text(encoding="utf-8") if p.exists() else "_C-3 미실행_"


def main() -> None:
    md = "\n\n".join([
        "# 결과 (자동 생성 — `python -m dta.eval.report`)",
        "## 말뭉치\n\n" + corpus_table(),
        "## C-2 검색 품질 (LLM 없음)\n\n" + c2_table(),
        "## C-1 테마 복원\n\n" + c1_table(),
        "## C-3 도구 설계 실험\n\n" + c3_table(),
    ])
    (RESULTS_DIR / "REPORT.md").write_text(md + "\n", encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
