"""LLM 접근은 이 모듈 한 곳에서만 만든다 (복희 '호출부는 정해진 곳만' 원칙, AST 게이트 테스트가 막는다).

설계 D3: Gemini(Vertex AI, ADC). 모델·리전·생각 단계는 .env.
생각 단계 기본 low — 복희 실측(2026-09-15): 기본은 요청당 20초를 넘겨 504, MINIMAL 은 사실을 빠뜨렸고 LOW 가 균형.
"""

from __future__ import annotations

from functools import lru_cache

from dta.config import env, require_env


@lru_cache(maxsize=4)
def get_chat_model(temperature: float = 0.0, max_output_tokens: int = 2048):
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=env("GEMINI_MODEL", "gemini-3.5-flash"),
        vertexai=True,
        project=require_env("GOOGLE_CLOUD_PROJECT"),
        location=env("GOOGLE_CLOUD_LOCATION", "asia-northeast1"),
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        thinking_level=env("GEMINI_THINKING_LEVEL", "low"),
        max_retries=1,
        timeout=60,
    )
