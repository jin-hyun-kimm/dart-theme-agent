"""경로·환경·범위 설정. 설계 D1~D8 의 값이 여기 한 곳에 있다."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CACHE_DIR = DATA_DIR / "cache"
INDEX_DIR = DATA_DIR / "index"
RESULTS_DIR = ROOT / "results"
FIXTURES_DIR = ROOT / "tests" / "fixtures"

load_dotenv(ROOT / ".env")

# --- 범위 (설계 D1·D6) ---
UNIVERSE_INDEX_CODE = "1028"  # KRX 지수 코드: 코스피200
UNIVERSE_DATE = "20261008"  # 구성종목 기준일 = 마지막 거래일 (10-09 한글날, 10-10 토)
FISCAL_YEARS = (2024, 2025)  # 사업연도. 사업보고서는 이듬해 3월 제출
REPORT_SECTION_TITLE = "사업의 내용"  # 설계 D2

# --- 테마 ETF 후보 선별용 키워드 (D1 에서 포함률을 재서 5개 확정) ---
THEME_KEYWORDS = (
    "방산",
    "조선",
    "원전",
    "원자력",
    "전력",
    "반도체",
    "2차전지",
    "이차전지",
    "배터리",
    "로봇",
    "바이오",
    "우주",
    "AI",
    "인공지능",
    "자동차",
    "건설",
    "철강",
    "화장품",
    "게임",
    "엔터",
    "헬스케어",
    "밸류체인",
    "소부장",
    "에너지",
    "수소",
    "태양광",
    "풍력",
    "은행",
    "보험",
    "증권",
    "지주",
    "유통",
    "식품",
    "소프트웨어",
    "통신",
    "미디어",
)
# 테마 ETF 가 아닌 것 (제외)
ETF_EXCLUDE_KEYWORDS = (
    "레버리지",
    "인버스",
    "채권",
    "국고채",
    "회사채",
    "커버드콜",
    "커버드",
    "월배당",
    "TRF",
    "혼합",
    "선물",
    "달러",
    "금",
    "은선물",
    "원유",
    "WTI",
    "리츠",
    "부동산",
    "머니마켓",
    "MMF",
    "CD금리",
    "KOFR",
    "단기",
    "미국",
    "중국",
    "일본",
    "글로벌",
    "유로",
    "인도",
    "베트남",
    "나스닥",
    "S&P",
    "TOP10TR",
    "배당",
    "고배당",
    "저변동",
    "퀄리티",
    "모멘텀",
    "밸류",
    "성장",
    "200",
    "코스닥150",
    "코스피",
    "코스닥",
    "TDF",
    "채권혼합",
    "주식혼합",
    "타겟",
    "데일리",
)


def env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def require_env(name: str) -> str:
    value = env(name)
    if value is None:
        raise RuntimeError(f"환경변수 {name} 가 비어 있다. .env 를 확인한다 (.env.example 참고).")
    return value


for _d in (RAW_DIR, CACHE_DIR, INDEX_DIR, RESULTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
