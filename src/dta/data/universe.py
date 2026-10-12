"""코스피200 구성종목 (pykrx). 결과는 data/cache 에 CSV 로 캐시한다."""

from __future__ import annotations

import pandas as pd
from pykrx import stock

from dta.config import CACHE_DIR, UNIVERSE_DATE, UNIVERSE_INDEX_CODE


def _cache_path(date: str) -> str:
    return str(CACHE_DIR / f"universe_kospi200_{date}.csv")


def load_universe(date: str = UNIVERSE_DATE, refresh: bool = False) -> pd.DataFrame:
    """columns: ticker(6자리 문자열), name. 코스피200 구성종목."""
    path = _cache_path(date)
    if not refresh:
        try:
            df = pd.read_csv(path, dtype={"ticker": str})
            if len(df) > 150:
                return df
        except FileNotFoundError:
            pass
    tickers = stock.get_index_portfolio_deposit_file(UNIVERSE_INDEX_CODE, date)
    if not tickers:
        raise RuntimeError(
            f"코스피200 구성종목이 비어 있다(date={date}). 거래일인지, KRX 로그인(.env KRX_ID/KRX_PW)이 됐는지 확인한다."
        )
    rows = [{"ticker": t, "name": stock.get_market_ticker_name(t)} for t in tickers]
    df = pd.DataFrame(rows).sort_values("ticker").reset_index(drop=True)
    df.to_csv(path, index=False)
    return df
