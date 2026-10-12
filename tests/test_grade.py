from types import SimpleNamespace

from dta.eval.grade import extract_amounts_won, grade


def test_extract_compound_korean_units():
    assert extract_amounts_won("매출액은 1조 2,345억원입니다") == [1.2345e12]
    assert extract_amounts_won("영업이익 6,566억 원") == [6.566e11]
    assert extract_amounts_won("약 123,456,789,000원") == [123456789000.0]


def test_grade_unit_error_classified():
    q = SimpleNamespace(gold_kind="won", gold_won=6.566e11, tolerance=0.005, gold_name="x")
    assert grade(q, "영업이익은 6,566억원입니다")["correct"]
    r = grade(q, "영업이익은 6,566원입니다")
    assert not r["correct"] and r["fail_type"] == "unit"
    assert grade(q, "모르겠습니다")["fail_type"] == "no_number"


def test_grade_pct_and_name():
    qp = SimpleNamespace(gold_kind="pct", gold_won=12.3, tolerance=0.3, gold_name="x")
    assert grade(qp, "전년 대비 12.4% 증가")["correct"]
    qn = SimpleNamespace(gold_kind="name", gold_won=0, tolerance=0, gold_name="삼성전자")
    assert grade(qn, "삼성전자가 더 큽니다")["correct"]
