import pandas as pd

from dta.data.financials import pick


def test_pick_prefers_standard_account_id_then_name():
    df = pd.DataFrame(
        {
            "account_id": ["ifrs-full_Revenue", "-standard-", "ifrs-full_ProfitLoss"],
            "account_nm": ["매출액", "영업이익", "당기순이익"],
            "amount": [1000, 200, 150],
        }
    )
    assert pick(df, "revenue") == 1000
    assert pick(df, "operating_income") == 200  # 계정명으로 폴백
    assert pick(df, "total_assets") is None
