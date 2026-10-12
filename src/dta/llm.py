"""LLM 접근은 이 모듈 한 곳에서만 만든다 (복희 '호출부는 정해진 곳만' 원칙, AST 게이트 테스트가 막는다).

설계 D3: Gemini(Vertex AI, ADC). 모델·리전은 .env.
"""

from __future__ import annotations

from functools import lru_cache

from dta.config import env, require_env


@lru_cache(maxsize=4)
def get_chat_model(temperature: float = 0.0, max_output_tokens: int = 2048):
    from langchain_google_vertexai import ChatVertexAI

    model = env("GEMINI_MODEL", "gemini-3.5-flash")
    return ChatVertexAI(
        model=model,
        project=require_env("GOOGLE_CLOUD_PROJECT"),
        location=env("GOOGLE_CLOUD_LOCATION", "asia-northeast1"),
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        max_retries=1,
    )
