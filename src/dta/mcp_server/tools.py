"""MCP 도구 구현 (설계 §4-1 '설계된' 서버). 모든 숫자 출력에 unit·fs_div·fiscal_year·source 가 붙는다.

실패는 예외 대신 {"error": ..., "next": ...} 로 돌려준다 — 에이전트가 다음 행동을 고를 수 있게.
"""

from __future__ import annotations

import html
import re
from functools import lru_cache

import pandas as pd

from dta.config import UNIVERSE_DATE, env
from dta.data.corpus import load_manifest, load_paragraphs
from dta.data.financials import ACCOUNT_IDS, fetch_financials, pick

_EOK = 100_000_000  # 1억원


def _err(msg: str, nxt: str) -> dict:
    return {"error": msg, "next": nxt}


@lru_cache(maxsize=1)
def _manifest() -> pd.DataFrame:
    return load_manifest()


def _companies() -> pd.DataFrame:
    man = _manifest()
    if len(man) == 0:
        from dta.data.universe import load_universe

        try:
            uni = load_universe()
        except Exception:  # noqa: BLE001
            return pd.DataFrame(columns=["stock_code", "corp_code", "corp_name"])
        return pd.DataFrame({"stock_code": uni["ticker"], "corp_code": "", "corp_name": uni["name"]})
    return man[["stock_code", "corp_code", "corp_name"]].drop_duplicates("stock_code")


def search_companies(query: str) -> list[dict]:
    q = query.strip().lower()
    df = _companies()
    if not q:
        return []
    mask = df["corp_name"].str.lower().str.contains(re.escape(q)) | (df["stock_code"] == q)
    return df[mask].head(20).to_dict("records")


def get_financials(stock_code: str, fiscal_year: int, fs_div: str = "CFS") -> dict:
    fs_div = fs_div.upper()
    if fs_div not in ("CFS", "OFS"):
        return _err("fs_div 는 CFS(연결) 또는 OFS(별도)", "fs_div='CFS' 로 다시 호출")
    man = _manifest()
    hit = man[man["stock_code"] == stock_code]
    corp_code = str(hit.iloc[0]["corp_code"]) if len(hit) else ""
    if not corp_code:
        from dta.data.dart_client import DartClient

        try:
            corp_code = DartClient().corp_code_for(stock_code) or ""
        except Exception as e:  # noqa: BLE001
            return _err(f"고유번호 조회 실패: {e}", "search_companies 로 종목코드를 확인")
        if not corp_code:
            return _err(f"종목코드 {stock_code} 의 DART 고유번호 없음", "search_companies 로 종목코드를 확인")
    from dta.data.dart_client import DartClient

    try:
        df = fetch_financials(DartClient(), corp_code, int(fiscal_year), fs_div)
    except Exception as e:  # noqa: BLE001
        return _err(f"재무제표 조회 실패: {e}", "fiscal_year 를 바꾸거나 fs_div 를 OFS 로")
    if len(df) == 0:
        return _err(
            f"{fiscal_year}년 {fs_div} 재무제표 없음(지주사·금융사는 별도만 있을 수 있음)",
            "fs_div 를 바꿔 다시 호출",
        )
    items = {}
    for key, (_aid, nm) in ACCOUNT_IDS.items():
        won = pick(df, key)
        items[key] = {
            "name": nm,
            "value_eok": None if won is None else round(won / _EOK, 1),
            "value_won": won,
        }
    rev, oi = items["revenue"]["value_won"], items["operating_income"]["value_won"]
    ratios = {"operating_margin_pct": round(oi / rev * 100, 2) if rev and oi is not None else None}
    return {
        "stock_code": stock_code,
        "corp_code": corp_code,
        "fiscal_year": int(fiscal_year),
        "fs_div": fs_div,
        "fs_div_label": "연결" if fs_div == "CFS" else "별도",
        "unit": "억원 (value_eok) / 원 (value_won)",
        "items": items,
        "ratios": ratios,
        "source": {"api": "OpenDART fnlttSinglAcntAll", "reprt_code": "11011(사업보고서)"},
    }


def list_filings(stock_code: str, fiscal_year: int | None = None) -> dict:
    man = _manifest()
    rows = man[man["stock_code"] == stock_code]
    if fiscal_year is not None:
        rows = rows[rows["fiscal_year"].astype(int) == int(fiscal_year)]
    if len(rows) == 0:
        return _err(
            "매니페스트에 없는 종목/연도", "search_companies 로 종목코드 확인, 또는 fiscal_year 2024·2025"
        )
    return {
        "filings": rows[["corp_name", "fiscal_year", "rcept_no", "rcept_dt", "status", "reason"]].to_dict(
            "records"
        )
    }


def get_report_section(
    stock_code: str, fiscal_year: int, sub_section: str | None = None, max_chars: int = 4000
) -> dict:
    man = _manifest()
    rows = man[
        (man["stock_code"] == stock_code)
        & (man["fiscal_year"].astype(int) == int(fiscal_year))
        & (man["status"] == "ok")
    ]
    if len(rows) == 0:
        return _err("해당 연도의 '사업의 내용' 없음", "list_filings 로 상태·사유 확인")
    rcept_no = str(rows.iloc[0]["rcept_no"])
    paras = load_paragraphs(rcept_no)
    if sub_section:
        paras = [p for p in paras if sub_section in p.section_path]
    text, used = "", 0
    for p in paras:
        if len(text) + len(p.text) > max_chars:
            break
        text += p.text + "\n"
        used += 1
    return {
        "stock_code": stock_code,
        "fiscal_year": int(fiscal_year),
        "rcept_no": rcept_no,
        "section_paths": sorted({p.section_path for p in paras}),
        "n_paragraphs": len(paras),
        "n_returned": used,
        "truncated": used < len(paras),
        "text": text,
        "source": {
            "api": "OpenDART document",
            "rcept_no": rcept_no,
            "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
        },
    }


def search_report_text(
    query: str, k: int = 10, fiscal_year: int | None = None, mode: str = "hybrid", embedder: str = "kure"
) -> dict:
    try:
        from dta.index.search import get_searcher

        s = get_searcher(embedder, mode)
    except Exception as e:  # noqa: BLE001
        return _err(f"색인 없음 또는 로드 실패: {type(e).__name__}", "scripts/build_index.py 를 먼저 실행")
    hits = s.search(query, k=k, fiscal_year=fiscal_year)
    return {
        "query": query,
        "mode": mode,
        "embedder": embedder,
        "hits": [
            {
                "chunk_id": h.chunk.chunk_id,
                "rank": h.rank,
                "score": round(h.score, 4),
                "stock_code": h.chunk.stock_code,
                "corp_name": h.chunk.corp_name,
                "fiscal_year": h.chunk.fiscal_year,
                "rcept_no": h.chunk.rcept_no,
                "section_path": h.chunk.section_path,
                "text": h.chunk.text,
            }
            for h in hits
        ],
    }


def get_prices(stock_code: str, start: str, end: str) -> dict:
    from pykrx import stock

    try:
        df = stock.get_market_ohlcv(start, end, stock_code)
    except Exception as e:  # noqa: BLE001
        return _err(f"시세 조회 실패: {e}", "날짜 형식 YYYYMMDD, 종목코드 6자리 확인")
    if df is None or len(df) == 0:
        return _err("해당 기간 시세 없음", "기간을 넓히거나 종목코드 확인")
    df = df.reset_index()
    rows = [
        {
            "date": r[0].strftime("%Y-%m-%d"),
            "open": int(r[1]),
            "high": int(r[2]),
            "low": int(r[3]),
            "close": int(r[4]),
            "volume": int(r[5]),
        }
        for r in df.itertuples(index=False)
    ]
    return {
        "stock_code": stock_code,
        "unit": "원 (가격), 주 (거래량)",
        "rows": rows,
        "source": {"provider": "KRX via pykrx"},
    }


def get_etf_holdings(etf_ticker: str, date: str = UNIVERSE_DATE) -> dict:
    from dta.data.etf import holdings

    try:
        h = holdings(etf_ticker, date)
    except Exception as e:  # noqa: BLE001
        return _err(f"구성종목 조회 실패: {e}", "KRX 로그인(.env KRX_ID/KRX_PW) 또는 캐시 확인")
    return {
        "etf_ticker": etf_ticker,
        "date": date,
        "unit": "비중 %",
        "holdings": h.to_dict("records"),
        "source": {"provider": "KRX PDF via pykrx"},
    }


def search_news(query: str, display: int = 10) -> dict:
    cid, sec = env("NAVER_CLIENT_ID"), env("NAVER_CLIENT_SECRET")
    if not cid or not sec:
        return _err("네이버 API 키 없음", ".env 에 NAVER_CLIENT_ID/SECRET 설정")
    import httpx

    r = httpx.get(
        "https://openapi.naver.com/v1/search/news.json",
        params={"query": query, "display": min(display, 100), "sort": "date"},
        headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec},
        timeout=10,
    )
    if r.status_code != 200:
        return _err(f"네이버 API {r.status_code}", "쿼리를 바꾸거나 잠시 뒤 재시도")
    strip = re.compile(r"<[^>]+>")
    return {
        "query": query,
        "items": [
            {
                "title": html.unescape(strip.sub("", it["title"])),
                "description": html.unescape(strip.sub("", it["description"])),
                "pub_date": it["pubDate"],
                "link": it["originallink"] or it["link"],
            }
            for it in r.json().get("items", [])
        ],
        "source": {"provider": "네이버 검색 API"},
    }
