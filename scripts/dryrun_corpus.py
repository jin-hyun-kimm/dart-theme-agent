"""D1 사전 점검: 회사 3곳 × 2024 사업보고서를 받아 파서가 실제 DART XML 에서 '사업의 내용'을 뽑는지 본다."""

import sys
from collections import Counter

from dta.data.dart_client import DartClient
from dta.data.report_parser import ParseFailure, extract_section

SAMPLES = [("005930", "삼성전자"), ("034020", "두산에너빌리티"), ("012450", "한화에어로스페이스")]


def main() -> int:
    c = DartClient()
    print("corp_codes:", len(c.corp_codes()))
    for stock_code, name in SAMPLES:
        corp = c.corp_code_for(stock_code)
        ref = c.annual_report(corp, 2024)
        if ref is None:
            print(f"{name}: 사업보고서 없음"); continue
        path = c.fetch_document_xml(ref.rcept_no)
        xml = path.read_text(encoding="utf-8")
        print(f"\n{name} corp={corp} rcept={ref.rcept_no} dt={ref.rcept_dt} nm={ref.report_nm} xml={len(xml):,}자")
        # 제목 태그 구조 들여다보기
        import re
        titles = re.findall(r"<TITLE[^>]*>(.*?)</TITLE>", xml, flags=re.S | re.I)
        tops = [re.sub(r"\s+", " ", t).strip() for t in titles if re.match(r"\s*[IVXⅠ-Ⅹ]+\s*\.", t)]
        print("  최상위 제목:", tops[:12])
        try:
            paras = extract_section(xml)
        except ParseFailure as e:
            print("  파서 실패:", e.reason, e.detail); continue
        kinds = Counter(p.kind for p in paras)
        paths = Counter(p.section_path for p in paras)
        print(f"  문단 {len(paras)} (p {kinds['p']}, 표행 {kinds['table_row']}), 글자 {sum(len(p.text) for p in paras):,}")
        for sp, n in list(paths.items())[:8]:
            print(f"   - {sp} ({n})")
        print("  샘플:", paras[1].text[:160].replace("\n", " "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
