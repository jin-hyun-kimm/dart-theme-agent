"""어휘 게이트 (설계 D14, 복희 이식): 프롬프트·화면 문구에 종목 추천·예측 어휘가 들어가면 테스트가 막는다.

데이터(사업보고서 원문)에는 적용하지 않는다. LLM 이 만든 문장에는 검증 노드가 별도로 적용한다.
"""

from __future__ import annotations

import re

BANNED = (
    "추천",
    "매수하세요",
    "매도하세요",
    "사세요",
    "파세요",
    "목표가",
    "목표주가",
    "상승할 것",
    "하락할 것",
    "오를 것",
    "내릴 것",
    "유망",
    "수익률 예측",
    "급등",
    "급락",
)
# 부정문("추천하지 않는다")은 허용
_ALLOW_RE = re.compile(r"추천(하지|을 하지|은 하지)\s*(않|말)")


def find_banned(text: str) -> list[str]:
    stripped = _ALLOW_RE.sub("", text)
    return [w for w in BANNED if w in stripped]
