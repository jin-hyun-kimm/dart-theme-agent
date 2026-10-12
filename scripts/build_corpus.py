"""D1: 코스피200 × 사업연도 2개의 사업보고서 '사업의 내용'을 모은다. 실행 뒤 상태·사유 표를 찍는다.

실행: PYTHONPATH=src .venv/bin/python scripts/build_corpus.py
필요: .env 의 OPENDART_API_KEY, KRX_ID/KRX_PW(유니버스 캐시가 없을 때)
"""

from dta.config import RESULTS_DIR
from dta.data.corpus import build_corpus, summarize
from dta.data.dart_client import DartClient
from dta.data.universe import load_universe


def main() -> None:
    uni = load_universe()
    print(f"유니버스 {len(uni)}")
    client = DartClient()
    man = build_corpus(client, uni)
    table = summarize(man)
    print(table.to_string(index=False))
    out = RESULTS_DIR / "d1_corpus_status.csv"
    table.to_csv(out, index=False)
    ok = man[man["status"] == "ok"]
    print(
        f"\nok {len(ok)}/{len(man)} · 문단 {int(ok['n_paras'].sum()):,} · 글자 {int(ok['n_chars'].sum()):,} → {out}"
    )


if __name__ == "__main__":
    main()
