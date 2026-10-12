"""테마 ETF 후보와 구성종목(PDF). 정답(골드) 구축의 원료.

pykrx 의 ETF 포트폴리오 예탁 파일(PDF)은 날짜 기준 구성종목·비중을 준다.
"""

from __future__ import annotations

import re

import pandas as pd
from pykrx import stock

from dta.config import CACHE_DIR, ETF_EXCLUDE_KEYWORDS, THEME_KEYWORDS

_TICKER_RE = re.compile(r"^\d{6}$")


def list_etfs(date: str) -> pd.DataFrame:
    """columns: ticker, name — 그 날짜의 전체 ETF."""
    path = CACHE_DIR / f"etf_list_{date}.csv"
    if path.exists():
        return pd.read_csv(path, dtype={"ticker": str})
    tickers = stock.get_etf_ticker_list(date)
    rows = [{"ticker": t, "name": stock.get_etf_ticker_name(t)} for t in tickers]
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return df


def is_theme_candidate(name: str) -> bool:
    if any(k.lower() in name.lower() for k in ETF_EXCLUDE_KEYWORDS):
        return False
    return any(k.lower() in name.lower() for k in THEME_KEYWORDS)


def theme_candidates(etfs: pd.DataFrame) -> pd.DataFrame:
    mask = etfs["name"].map(is_theme_candidate)
    return etfs[mask].reset_index(drop=True)


def holdings(etf_ticker: str, date: str) -> pd.DataFrame:
    """columns: ticker, weight(%). 주식 종목만(6자리 티커), 비중>0."""
    path = CACHE_DIR / "etf_pdf" / f"{etf_ticker}_{date}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return pd.read_csv(path, dtype={"ticker": str})
    pdf = stock.get_etf_portfolio_deposit_file(etf_ticker, date)
    pdf = pdf.reset_index()
    first_col = pdf.columns[0]
    pdf = pdf.rename(columns={first_col: "ticker"})
    weight_col = next((c for c in pdf.columns if "비중" in str(c)), None)
    out = pd.DataFrame(
        {"ticker": pdf["ticker"].astype(str), "weight": pdf[weight_col] if weight_col else 0.0}
    )
    out = out[out["ticker"].map(lambda t: bool(_TICKER_RE.match(t)))]
    out = out[out["weight"] > 0].sort_values("weight", ascending=False).reset_index(drop=True)
    out.to_csv(path, index=False)
    return out


def coverage(hold: pd.DataFrame, universe_tickers: set[str]) -> dict:
    """정답 분모 산정(설계 D7): 구성종목 중 유니버스에 든 수와 뺀 수를 같이 돌려준다."""
    n_total = len(hold)
    inside = hold[hold["ticker"].isin(universe_tickers)]
    n_in = len(inside)
    w_in = float(inside["weight"].sum()) if n_in else 0.0
    return {
        "n_total": n_total,
        "n_in_universe": n_in,
        "n_excluded": n_total - n_in,
        "ratio_count": (n_in / n_total) if n_total else 0.0,
        "ratio_weight": w_in / float(hold["weight"].sum()) if n_total and hold["weight"].sum() else 0.0,
    }
