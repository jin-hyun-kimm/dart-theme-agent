"""Gemini(Vertex) 호출 + 구조화 출력이 되는지 1회 확인. 비용: 토큰 수백."""

import time

from pydantic import BaseModel, Field

from dta.llm import get_chat_model


class Judgement(BaseModel):
    label: str = Field(description="핵심|관련|무관|모름 중 하나")
    evidence: str = Field(description="원문에서 그대로 옮긴 근거 문장 1개")


def main() -> None:
    llm = get_chat_model()
    t = time.time()
    r = llm.invoke("한 단어로 답하라: 대한민국의 수도는?")
    print("plain:", r.content[:50], f"({time.time() - t:.1f}s)")
    t = time.time()
    s = llm.with_structured_output(Judgement).invoke(
        "다음 문단이 '원전 밸류체인' 테마에 속하는 기업의 활동을 말하는지 판정하고 근거 문장을 원문 그대로 옮겨라.\n"
        "문단: 당사는 원자력 발전소용 주기기와 보조기기를 설계·제작하여 국내외 발전사에 공급하고 있습니다."
    )
    print("structured:", s, f"({time.time() - t:.1f}s)")


if __name__ == "__main__":
    main()
