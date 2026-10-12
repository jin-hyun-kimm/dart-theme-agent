import pandas as pd

from dta.data.etf import coverage, is_theme_candidate


def test_coverage_counts_and_excluded():
    hold = pd.DataFrame({"ticker": ["005930", "000660", "999999"], "weight": [50.0, 30.0, 20.0]})
    c = coverage(hold, {"005930", "000660"})
    assert c["n_total"] == 3
    assert c["n_in_universe"] == 2
    assert c["n_excluded"] == 1
    assert abs(c["ratio_count"] - 2 / 3) < 1e-9
    assert abs(c["ratio_weight"] - 0.8) < 1e-9


def test_theme_candidate_filter():
    assert is_theme_candidate("KODEX K-방산")
    assert not is_theme_candidate("KODEX 200")
    assert not is_theme_candidate("KODEX 반도체 레버리지")
    assert not is_theme_candidate("TIGER 미국반도체")
