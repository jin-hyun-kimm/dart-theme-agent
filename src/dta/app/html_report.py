"""results/REPORT.md → results/index.html. 우리가 내는 마크다운 부분집합(제목·표·목록·굵게·코드·인용)만 바꾼다. 의존성 없음.

실행: PYTHONPATH=src .venv/bin/python -m dta.app.html_report
"""

from __future__ import annotations

import html
import re

from dta.config import RESULTS_DIR

CSS = """
:root{--ink:#1a1a1a;--ink3:#6b6b6b;--line:#e3e3e3;--accent:#c8441c;--bg:#fbfaf8}
body{font-family:-apple-system,"Pretendard","Apple SD Gothic Neo",sans-serif;color:var(--ink);background:var(--bg);max-width:960px;margin:40px auto;padding:0 16px;line-height:1.6}
h1{font-size:28px;margin:0 0 8px}h2{font-size:20px;margin:36px 0 10px;border-bottom:2px solid var(--accent);padding-bottom:4px}h3{font-size:16px;margin:24px 0 6px}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:14px}th,td{border:1px solid var(--line);padding:6px 10px;text-align:left}th{background:#f1ede8}
td:not(:first-child),th:not(:first-child){text-align:right}
blockquote{border-left:3px solid var(--accent);margin:8px 0;padding:4px 12px;color:var(--ink3)}
code{background:#f1ede8;padding:1px 4px;border-radius:3px;font-size:13px}p.small{color:var(--ink3);font-size:13px}
"""


def _inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(r"_(.+?)_", r"<i>\1</i>", s)
    return s


def md_to_html(md: str) -> str:
    out: list[str] = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|\s*:?-+", lines[i + 1]):
            header = [c.strip() for c in ln.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            out.append("<table><tr>" + "".join(f"<th>{_inline(h)}</th>" for h in header) + "</tr>")
            out += ["<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in rows]
            out.append("</table>")
            continue
        if ln.startswith("# "):
            out.append(f"<h1>{_inline(ln[2:])}</h1>")
        elif ln.startswith("## "):
            out.append(f"<h2>{_inline(ln[3:])}</h2>")
        elif ln.startswith("### "):
            out.append(f"<h3>{_inline(ln[4:])}</h3>")
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{_inline(lines[i][2:])}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif ln.startswith("> "):
            out.append(f"<blockquote>{_inline(ln[2:])}</blockquote>")
        elif ln.strip():
            out.append(f"<p>{_inline(ln)}</p>")
        i += 1
    return "\n".join(out)


def main() -> None:
    md = (RESULTS_DIR / "REPORT.md").read_text(encoding="utf-8")
    body = md_to_html(md)
    page = (
        "<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>근거 — 결과</title><style>{CSS}</style></head><body>{body}"
        "<p class='small'>투자 조언이 아니다. 종목·시점 추천, 목표가, 수익률 예측을 하지 않는다. 데이터: DART·KRX 공개 자료.</p></body></html>"
    )
    out = RESULTS_DIR / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"{out} ({len(page):,} bytes)")


if __name__ == "__main__":
    main()
