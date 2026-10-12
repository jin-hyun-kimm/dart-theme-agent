"""DART 사업보고서 원문 XML → "사업의 내용" 섹션의 문단 목록.

DART 원문은 XML 이지만 사용자 정의 엔티티·불완전 태그가 섞여 있어 BeautifulSoup(lxml-xml 이 아닌 html.parser)로
관대하게 읽는다. 구조는 대략 아래와 같다(회사·연도마다 편차가 있어 실패 사유를 남긴다).

<SECTION-1><TITLE>II. 사업의 내용</TITLE>
  <SECTION-2><TITLE>1. 사업의 개요</TITLE><P>...</P><TABLE>...</TABLE></SECTION-2>
  ...
</SECTION-1>
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

TOP_SECTION_RE = re.compile(r"^\s*[IVXⅠ-Ⅹ]+\s*\.")  # "II. 사업의 내용" 같은 최상위 제목
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class Paragraph:
    section_path: str  # 예: "II. 사업의 내용 > 2. 주요 제품 및 서비스"
    kind: str  # "p" | "table_row"
    text: str
    order: int


class ParseFailure(Exception):
    """실패 사유를 코드로 남긴다: no_title / empty_section / too_short / parse_error"""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def _clean(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def _find_section_title(soup: BeautifulSoup, keyword: str) -> Tag | None:
    titles = soup.find_all(["title", "TITLE"])
    # 최상위 제목("II. 사업의 내용") 우선, 없으면 키워드를 포함한 첫 제목
    for t in titles:
        txt = _clean(t.get_text(" "))
        if keyword in txt and TOP_SECTION_RE.match(txt):
            return t
    for t in titles:
        if keyword in _clean(t.get_text(" ")):
            return t
    return None


def _table_rows(table: Tag) -> list[str]:
    rows: list[str] = []
    for tr in table.find_all(["tr", "TR"]):
        cells = [_clean(td.get_text(" ")) for td in tr.find_all(["td", "th", "TD", "TH"])]
        cells = [c for c in cells if c]
        if len(cells) >= 2:
            rows.append(" | ".join(cells))
    return rows


def extract_section(xml_text: str, keyword: str = "사업의 내용", min_chars: int = 500) -> list[Paragraph]:
    try:
        soup = BeautifulSoup(xml_text, "html.parser")
    except Exception as e:  # noqa: BLE001
        raise ParseFailure("parse_error", type(e).__name__) from e

    title = _find_section_title(soup, keyword)
    if title is None:
        raise ParseFailure("no_title", keyword)
    top_title = _clean(title.get_text(" "))

    container = title.parent if isinstance(title.parent, Tag) else None
    if container is None or container.name in ("[document]", "body", "document"):
        raise ParseFailure("empty_section", "제목의 부모 섹션을 못 찾음")

    paras: list[Paragraph] = []
    sub_title = ""
    order = 0
    seen_tables: set[int] = set()
    for el in container.descendants:
        if not isinstance(el, Tag):
            continue
        name = el.name.lower()
        if name == "title":
            if el is title:
                continue
            sub_title = _clean(el.get_text(" "))
            continue
        if name == "table":
            if id(el) in seen_tables:
                continue
            seen_tables.add(id(el))
            path = f"{top_title} > {sub_title}" if sub_title else top_title
            for row in _table_rows(el):
                paras.append(Paragraph(section_path=path, kind="table_row", text=row, order=order))
                order += 1
            continue
        if name == "p":
            if el.find_parent(["table", "TABLE"]) is not None:
                continue
            txt = _clean(el.get_text(" "))
            if len(txt) < 8:
                continue
            path = f"{top_title} > {sub_title}" if sub_title else top_title
            paras.append(Paragraph(section_path=path, kind="p", text=txt, order=order))
            order += 1

    total = sum(len(p.text) for p in paras)
    if not paras:
        raise ParseFailure("empty_section", top_title)
    if total < min_chars:
        raise ParseFailure("too_short", f"{total} chars")
    return paras
