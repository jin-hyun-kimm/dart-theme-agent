"""C-3 채점: 답변 문장에서 숫자·단위를 읽어 정답과 허용오차로 비교. 실패 유형을 분류한다."""

from __future__ import annotations

import re

_NUM = re.compile(r"(-?\d[\d,]*\.?\d*)\s*(조|억|백만|천만|만|원|%)?")
UNIT = {"조": 1e12, "억": 1e8, "천만": 1e7, "백만": 1e6, "만": 1e4, "원": 1.0}
_DECREASE = re.compile(r"^\s*(감소|하락|줄|축소|역성장|적자)")  # "29.6% 감소" → -29.6


def extract_amounts_won(text: str) -> list[float]:
    """'1조 2,345억원' 같은 복합 표기도 합산한다."""
    vals: list[float] = []
    pending = 0.0
    had = False
    sign = 1.0  # "-2조 3,210억원": 첫 부분의 부호가 복합 표기 전체에 걸린다
    last_mag = float("inf")  # 복합 표기는 큰 단위 → 작은 단위 순. 순서가 깨지면(괄호 되풀이 등) 새 값으로 본다
    for m in _NUM.finditer(text):
        num = float(m.group(1).replace(",", ""))
        unit = m.group(2)
        if unit in ("조", "억", "천만", "백만", "만"):
            if had and UNIT[unit] >= last_mag:
                vals.append(pending)
                pending = 0.0
                sign = 1.0
            if not had:
                sign = -1.0 if num < 0 else 1.0
            pending += abs(num) * UNIT[unit] * sign
            last_mag = UNIT[unit]
            had = True
        elif unit == "원":
            if had:
                vals.append(pending + (num if num < 1e4 else 0.0))
            else:
                vals.append(num)
            pending, had, last_mag = 0.0, False, float("inf")
        elif unit == "%":
            if had:
                vals.append(pending)
                pending, had, last_mag = 0.0, False, float("inf")
        else:
            if had:
                vals.append(pending)
                pending, had, last_mag = 0.0, False, float("inf")
            elif num >= 1e6:
                vals.append(num)  # 단위 없는 큰 숫자는 원으로 간주
    if had:
        vals.append(pending)
    return vals


def extract_pcts(text: str) -> list[float]:
    """'29.6% 감소' 처럼 뒤따르는 낱말이 방향을 말하면 부호에 반영한다."""
    out = []
    for m in _NUM.finditer(text):
        if m.group(2) != "%":
            continue
        v = float(m.group(1).replace(",", ""))
        tail = text[m.end() : m.end() + 6]
        if v > 0 and _DECREASE.match(tail):
            v = -v
        out.append(v)
    return out


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
