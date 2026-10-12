"""DART 단일회사 전체 재무제표 → 정규화된 긴 표. ② 실험의 정답과 MCP get_financials 의 원료.

단위: DART 는 원(KRW) 단위 정수 문자열을 준다. 여기서는 원 그대로 두고, 도구 계층에서 억원으로 바꾼다
(설계 §4-1: 모든 숫자 출력에 unit·fs_div·fiscal_year·source 를 붙인다).
"""

from __future__ import annotations

import time

import pandas as pd

from dta.config import CACHE_DIR

REPRT_ANNUAL = "11011"  # 사업보고서
ACCOUNT_IDS = {
    "revenue": ("ifrs-full_Revenue", "매출액"),
    "operating_income": ("dart_OperatingIncomeLoss", "영업이익"),
    "net_income": ("ifrs-full_ProfitLoss", "당기순이익"),
    "total_assets": ("ifrs-full_Assets", "자산총계"),
    "total_equity": ("ifrs-full_Equity", "자본총계"),
    "total_liabilities": ("ifrs-full_Liabilities", "부채총계"),
}


def _to_int(s: str) -> int | None:
    s = (s or "").replace(",", "").strip()
    if s in ("", "-"):
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def fetch_financials(dart_client, corp_code: str, fiscal_year: int, fs_div: str = "CFS") -> pd.DataFrame:
    """columns: corp_code, fiscal_year, fs_div, account_id, account_nm, sj_div, amount(원, 당기), amount_prev(원, 전기).

    fs_div: CFS 연결 / OFS 별도. 캐시: data/cache/fin/{corp}_{year}_{fs}.csv
    """
    path = CACHE_DIR / "fin" / f"{corp_code}_{fiscal_year}_{fs_div}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return pd.read_csv(path, dtype={"corp_code": str})
    raw = dart_client.dart.finstate_all(corp_code, fiscal_year, reprt_code=REPRT_ANNUAL, fs_div=fs_div)
    time.sleep(0.25)
    if raw is None or len(raw) == 0:
        df = pd.DataFrame(
            columns=[
                "corp_code",
                "fiscal_year",
                "fs_div",
                "account_id",
                "account_nm",
                "sj_div",
                "amount",
                "amount_prev",
            ]
        )
        df.to_csv(path, index=False)
        return df
    raw = raw.astype(str)
    df = pd.DataFrame(
        {
            "corp_code": corp_code,
            "fiscal_year": fiscal_year,
            "fs_div": fs_div,
            "account_id": raw["account_id"].str.strip(),
            "account_nm": raw["account_nm"].str.strip(),
            "sj_div": raw["sj_div"].str.strip(),
            "amount": raw["thstrm_amount"].map(_to_int),
            "amount_prev": raw["frmtrm_amount"].map(_to_int) if "frmtrm_amount" in raw.columns else None,
        }
    )
    df.to_csv(path, index=False)
    return df


def pick(df: pd.DataFrame, key: str) -> int | None:
    """정규화 키(revenue 등)로 당기 금액(원)을 하나 고른다. 표준 계정ID 우선, 없으면 계정명 일치."""
    account_id, account_nm = ACCOUNT_IDS[key]
    hit = df[df["account_id"] == account_id]
    if hit.empty:
        hit = df[df["account_nm"].str.replace(" ", "") == account_nm]
    if hit.empty:
        return None
    # 손익 항목은 손익계산서(IS) 또는 포괄손익계산서(CIS) 에 둘 다 있을 수 있다 → 첫 행
    v = hit.iloc[0]["amount"]
    return None if pd.isna(v) else int(v)
