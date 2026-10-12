"""정답(골드): ETF 구성종목 ∩ 코스피200. 뺀 수를 같이 돌려준다 (설계 D7)."""

from __future__ import annotations

from dataclasses import dataclass

from dta.data.etf import holdings
from dta.data.universe import load_universe
from dta.eval.themes import Theme


@dataclass(frozen=True)
class Gold:
    theme_id: str
    all_tickers: frozenset[str]
    in_universe: frozenset[str]
    weights: dict[str, float]

    @property
    def n_excluded(self) -> int:
        return len(self.all_tickers) - len(self.in_universe)


def build_gold(theme: Theme, date: str) -> Gold:
    uni = set(load_universe(date)["ticker"])
    h = holdings(theme.etf_ticker, date)
    allt = frozenset(h["ticker"])
    return Gold(
        theme_id=theme.id,
        all_tickers=allt,
        in_universe=frozenset(t for t in allt if t in uni),
        weights={r.ticker: float(r.weight) for r in h.itertuples()},
    )
