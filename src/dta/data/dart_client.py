"""OpenDART 접근: 고유번호 매핑, 사업보고서 접수번호 선택, 원문 XML 내려받기(캐시).

원칙: 네트워크를 타는 함수는 전부 data/raw·data/cache 에 결과를 남기고, 두 번째 호출은 파일을 읽는다.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from dta.config import CACHE_DIR, RAW_DIR, require_env

_SLEEP_SEC = 0.25  # 연속 호출 간격 (예의)


@dataclass(frozen=True)
class AnnualReportRef:
    corp_code: str
    stock_code: str
    corp_name: str
    fiscal_year: int
    rcept_no: str
    rcept_dt: str
    report_nm: str


class DartClient:
    def __init__(self, api_key: str | None = None) -> None:
        import OpenDartReader  # 지연 임포트: 키 없이도 모듈은 임포트된다

        self.dart = OpenDartReader(api_key or require_env("OPENDART_API_KEY"))
        self._corp_codes: pd.DataFrame | None = None

    # --- 고유번호 ---
    def corp_codes(self) -> pd.DataFrame:
        """columns: corp_code, corp_name, stock_code(6자리 또는 빈값), modify_date."""
        if self._corp_codes is None:
            path = CACHE_DIR / "dart_corp_codes.csv"
            if path.exists():
                df = pd.read_csv(path, dtype=str).fillna("")
            else:
                df = self.dart.corp_codes.copy()
                df = df.astype(str).fillna("")
                df["stock_code"] = df["stock_code"].str.strip()
                df.to_csv(path, index=False)
            self._corp_codes = df
        return self._corp_codes

    def corp_code_for(self, stock_code: str) -> str | None:
        df = self.corp_codes()
        hit = df[df["stock_code"] == stock_code]
        if hit.empty:
            return None
        return str(hit.iloc[0]["corp_code"])

    # --- 사업보고서 선택 ---
    def annual_report(self, corp_code: str, fiscal_year: int) -> AnnualReportRef | None:
        """사업연도 fiscal_year 의 사업보고서 중 **가장 늦게 접수된 것**(정정 포함)을 고른다."""
        start = f"{fiscal_year + 1}-01-01"
        end = f"{fiscal_year + 1}-12-31"
        lst = self.dart.list(corp_code, start=start, end=end, kind="A", final=True)
        time.sleep(_SLEEP_SEC)
        if lst is None or len(lst) == 0:
            return None
        lst = lst.astype(str)
        tag = f"({fiscal_year}.12)"
        mask = lst["report_nm"].str.contains("사업보고서") & lst["report_nm"].str.contains(tag, regex=False)
        cand = lst[mask]
        if cand.empty:
            return None
        row = cand.sort_values("rcept_dt").iloc[-1]
        return AnnualReportRef(
            corp_code=str(row["corp_code"]),
            stock_code=str(row.get("stock_code", "")),
            corp_name=str(row["corp_name"]),
            fiscal_year=fiscal_year,
            rcept_no=str(row["rcept_no"]),
            rcept_dt=str(row["rcept_dt"]),
            report_nm=str(row["report_nm"]),
        )

    # --- 원문 ---
    def document_xml_path(self, rcept_no: str) -> Path:
        return RAW_DIR / "dart" / f"{rcept_no}.xml"

    def fetch_document_xml(self, rcept_no: str) -> Path:
        path = self.document_xml_path(rcept_no)
        if path.exists() and path.stat().st_size > 1000:
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        xml_text = self.dart.document(rcept_no)
        time.sleep(_SLEEP_SEC)
        if not xml_text or len(xml_text) < 1000:
            raise RuntimeError(f"원문이 비어 있다: rcept_no={rcept_no} len={len(xml_text or '')}")
        path.write_text(xml_text, encoding="utf-8")
        return path
