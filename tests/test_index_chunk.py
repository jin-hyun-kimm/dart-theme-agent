from dta.data.report_parser import Paragraph
from dta.index.chunk import chunk_paragraphs


def _p(path, text, order, kind="p"):
    return Paragraph(section_path=path, kind=kind, text=text, order=order)


def test_chunks_respect_section_and_target():
    a = "원자력 발전소용 주기기 문장입니다. " * 20  # ~360자
    paras = [
        _p("II > 1", a, 0),
        _p("II > 1", a, 1),
        _p("II > 1", a, 2),
        _p("II > 2", "다른 섹션 문단입니다. " * 10, 3),
        _p("II > 2", "원자력 | 1,200 | 45%", 4, kind="table_row"),
        _p("II > 2", "가스터빈 | 900 | 35%", 5, kind="table_row"),
    ]
    chunks = chunk_paragraphs(
        paras,
        corp_code="c",
        stock_code="s",
        corp_name="n",
        fiscal_year=2024,
        rcept_no="r",
        target=600,
        overlap=50,
    )
    assert all(len(c.text) <= 600 + 50 + 1 + 400 for c in chunks)  # 겹침 + 문단 하나 초과 허용
    sections = [c.section_path for c in chunks]
    assert "II > 1" in sections and "II > 2" in sections
    kinds = {c.section_path: c.kind for c in chunks}
    assert kinds["II > 2"] in ("p", "table")
    table_chunks = [c for c in chunks if c.kind == "table"]
    assert len(table_chunks) == 1 and "가스터빈 | 900" in table_chunks[0].text
    # 같은 섹션 안에서는 앞 청크 꼬리가 다음 청크 머리에 겹친다
    sec1 = [c for c in chunks if c.section_path == "II > 1"]
    assert len(sec1) >= 2 and sec1[1].text.startswith(sec1[0].text[-50:].split("\n")[-1][:10])
    assert chunks[0].chunk_id == "r:0000"


def test_long_single_paragraph_is_split():
    long = "아주 긴 문장입니다. " * 200  # ~2,200자
    chunks = chunk_paragraphs(
        [_p("II > 1", long, 0)],
        corp_code="c",
        stock_code="s",
        corp_name="n",
        fiscal_year=2024,
        rcept_no="r",
        max_len=900,
    )
    assert len(chunks) >= 3 and all(len(c.text) <= 900 + 100 + 1 for c in chunks)
