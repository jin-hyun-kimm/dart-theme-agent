from types import SimpleNamespace

from dta.eval.grade import extract_amounts_won, grade


def test_extract_compound_korean_units():
    assert extract_amounts_won("매출액은 1조 2,345억원입니다") == [1.2345e12]
    assert extract_amounts_won("영업이익 6,566억 원") == [6.566e11]
    assert extract_amounts_won("약 123,456,789,000원") == [123456789000.0]
    # 괄호 되풀이는 합산하지 않는다 (2026-10-12 C-3 스모크에서 발견)
    assert extract_amounts_won("매출액은 3조 3,931억원(33,931억원)입니다") == [3.3931e12, 3.3931e12]


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


def test_negative_compound_and_decrease_words():
    # 2026-10-12 C-3 실패 검토에서 찾은 채점기 결함 2건
    assert extract_amounts_won("영업이익은 -2조 3,210억원(영업손실 2조 3,210억원)입니다")[0] == -2.321e12
    from dta.eval.grade import extract_pcts

    assert extract_pcts("468억원 대비 29.6% 감소하였습니다") == [-29.6]
    assert extract_pcts("전년 대비 4.5% 증가") == [4.5]
