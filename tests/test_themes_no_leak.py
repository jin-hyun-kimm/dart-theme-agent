"""설계 D8: 테마 설명에 구성종목(정답)이 들어가면 안 된다. 캐시된 ETF 구성종목이 있을 때만 검사한다."""

from dta.config import CACHE_DIR
from dta.eval.themes import load_themes


def test_theme_descriptions_do_not_name_constituents():
    date, themes = load_themes()
    try:
        from dta.data.universe import load_universe

        names = dict(zip(load_universe(date)["ticker"], load_universe(date)["name"], strict=True))
    except Exception:  # noqa: BLE001 — 캐시 없음(키 전) → 검사할 수 없음
        return
    for t in themes:
        pdf = CACHE_DIR / "etf_pdf" / f"{t.etf_ticker}_{date}.csv"
        if not pdf.exists():
            continue
        import pandas as pd

        for tk in pd.read_csv(pdf, dtype={"ticker": str})["ticker"]:
            nm = names.get(tk)
            assert not nm or nm not in t.description, f"{t.id}: 설명에 구성종목 '{nm}' 노출"
