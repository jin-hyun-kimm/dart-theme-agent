from pathlib import Path

import pytest

from dta.data.report_parser import ParseFailure, extract_section

FIX = Path(__file__).parent / "fixtures" / "sample_report.xml"


def test_extracts_only_business_section_with_paths():
    paras = extract_section(FIX.read_text(encoding="utf-8"), min_chars=50)
    texts = [p.text for p in paras]
    assert any("원자력 발전소용 주기기" in t for t in texts)
    assert any("가스터빈" in t for t in texts)
    assert not any("재무 문단" in t for t in texts)
    assert not any("회사 개요" in t for t in texts)
    assert not any(t == "짧음" for t in texts)
    paths = {p.section_path for p in paras}
    assert "II. 사업의 내용 > 1. 사업의 개요" in paths
    assert "II. 사업의 내용 > 2. 주요 제품 및 서비스" in paths
    rows = [p for p in paras if p.kind == "table_row"]
    assert rows and "원자력 | 1,200 | 45%" in rows[1].text


def test_missing_section_reports_reason():
    with pytest.raises(ParseFailure) as e:
        extract_section("<DOCUMENT><TITLE>I. 회사의 개요</TITLE><P>x</P></DOCUMENT>")
    assert e.value.reason == "no_title"
