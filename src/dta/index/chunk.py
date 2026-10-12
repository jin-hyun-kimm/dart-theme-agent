"""문단 → 청크. 섹션 경계를 넘지 않고, 문단 경계를 보존하며, 목표 길이에 맞춰 묶는다 (설계 §3)."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from dta.data.report_parser import Paragraph

_SENT_SPLIT_RE = re.compile(r"(?<=[.다요음]\s)|(?<=[.!?])\s+")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    corp_code: str
    stock_code: str
    corp_name: str
    fiscal_year: int
    rcept_no: str
    section_path: str
    kind: str  # "p" | "table"
    text: str
    first_order: int

    def to_dict(self) -> dict:
        return asdict(self)


def _split_long(text: str, max_len: int) -> list[str]:
    if len(text) <= max_len:
        return [text]
    pieces: list[str] = []
    buf = ""
    for sent in _SENT_SPLIT_RE.split(text):
        if not sent:
            continue
        if len(buf) + len(sent) > max_len and buf:
            pieces.append(buf.strip())
            buf = ""
        buf += sent if buf == "" else (" " + sent)
    if buf.strip():
        pieces.append(buf.strip())
    # 문장이 하나인데 max_len 을 넘으면 강제로 자른다
    out: list[str] = []
    for p in pieces:
        while len(p) > max_len:
            out.append(p[:max_len])
            p = p[max_len:]
        out.append(p)
    return out


def chunk_paragraphs(
    paras: list[Paragraph],
    *,
    corp_code: str,
    stock_code: str,
    corp_name: str,
    fiscal_year: int,
    rcept_no: str,
    target: int = 600,
    overlap: int = 100,
    max_len: int = 900,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_len = 0
    buf_section = ""
    buf_kind = ""
    buf_first = 0
    prev_tail = ""

    def flush() -> None:
        nonlocal buf, buf_len, prev_tail
        if not buf:
            return
        body = "\n".join(buf)
        text = (prev_tail + "\n" + body) if prev_tail else body
        chunks.append(
            Chunk(
                chunk_id=f"{rcept_no}:{len(chunks):04d}",
                corp_code=corp_code,
                stock_code=stock_code,
                corp_name=corp_name,
                fiscal_year=fiscal_year,
                rcept_no=rcept_no,
                section_path=buf_section,
                kind=buf_kind,
                text=text,
                first_order=buf_first,
            )
        )
        prev_tail = body[-overlap:] if overlap and len(body) > overlap else ""
        buf, buf_len = [], 0

    for p in paras:
        kind = "table" if p.kind == "table_row" else "p"
        if buf and (p.section_path != buf_section or kind != buf_kind):
            flush()
            prev_tail = ""  # 섹션·종류가 바뀌면 겹침을 끊는다
        for piece in _split_long(p.text, max_len):
            if buf and buf_len + len(piece) > target:
                flush()
            if not buf:
                buf_section, buf_kind, buf_first = p.section_path, kind, p.order
            buf.append(piece)
            buf_len += len(piece)
    flush()
    return chunks
