"""C-3 채점: 답변 문장에서 숫자·단위를 읽어 정답과 허용오차로 비교. 실패 유형을 분류한다."""

from __future__ import annotations

import re

_NUM = re.compile(r"(-?\d[\d,]*\.?\d*)\s*(조|억|백만|천만|만|원|%)?")
UNIT = {"조": 1e12, "억": 1e8, "천만": 1e7, "백만": 1e6, "만": 1e4, "원": 1.0}


def extract_amounts_won(text: str) -> list[float]:
    """'1조 2,345억원' 같은 복합 표기도 합산한다."""
    vals: list[float] = []
    pending = 0.0
    had = False
    for m in _NUM.finditer(text):
        num = float(m.group(1).replace(",", ""))
        unit = m.group(2)
        if unit in ("조", "억", "천만", "백만", "만"):
            pending += num * UNIT[unit]
            had = True
        elif unit == "원":
            if had:
                vals.append(pending + (num if num < 1e4 else 0.0))
            else:
                vals.append(num)
            pending, had = 0.0, False
        elif unit == "%":
            if had:
                vals.append(pending)
                pending, had = 0.0, False
        else:
            if had:
                vals.append(pending)
                pending, had = 0.0, False
            elif num >= 1e6:
                vals.append(num)  # 단위 없는 큰 숫자는 원으로 간주
    if had:
        vals.append(pending)
    return vals


def extract_pcts(text: str) -> list[float]:
    return [float(m.group(1).replace(",", "")) for m in _NUM.finditer(text) if m.group(2) == "%"]


def grade(q, answer: str) -> dict:
    """returns {correct: bool, fail_type: str|None, got: ...}"""
    if q.gold_kind == "name":
        ok = q.gold_name in answer
        return {"correct": ok, "fail_type": None if ok else "wrong_company", "got": answer[:80]}
    if q.gold_kind == "pct":
        got = extract_pcts(answer)
        for g in got:
            if abs(g - q.gold_won) <= q.tolerance:
                return {"correct": True, "fail_type": None, "got": g}
        return {"correct": False, "fail_type": "wrong_pct" if got else "no_number", "got": got[:3]}
    got = extract_amounts_won(answer)
    for g in got:
        if g and abs(g - q.gold_won) / abs(q.gold_won) <= q.tolerance:
            return {"correct": True, "fail_type": None, "got": g}
    for g in got:  # 실패 유형 추정: 단위 오류(10^n 배수)
        if g:
            ratio = g / q.gold_won
            for p in (1e4, 1e6, 1e8, 1e-4, 1e-6, 1e-8, 1e3, 1e-3):
                if abs(ratio / p - 1) <= q.tolerance:
                    return {"correct": False, "fail_type": "unit", "got": g}
    return {"correct": False, "fail_type": "wrong_value" if got else "no_number", "got": got[:3]}
