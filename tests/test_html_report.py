from dta.app.html_report import md_to_html


def test_table_and_headings_convert():
    md = "# 제목\n\n## 절\n\n| 구성 | 재현율 |\n|---|---|\n| R1 | **80%** |\n\n- 항목 `코드`\n> 인용\n"
    h = md_to_html(md)
    assert "<h1>제목</h1>" in h and "<h2>절</h2>" in h
    assert "<th>구성</th>" in h and "<td><b>80%</b></td>" in h
    assert "<li>항목 <code>코드</code></li>" in h and "<blockquote>인용</blockquote>" in h
    assert "<script" not in md_to_html("<script>alert(1)</script>")
