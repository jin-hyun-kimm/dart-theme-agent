from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field

Label = Literal["핵심", "관련", "무관", "모름"]


class Stage(BaseModel):
    name: str = Field(description="밸류체인 단계 이름")
    queries: list[str] = Field(description="사업보고서에서 이 단계를 찾을 검색어 2~4개")


class ThemeDefinition(BaseModel):
    stages: list[Stage]


class Judgement(BaseModel):
    label: Label
    evidence: str = Field(default="", description="발췌에서 글자 그대로 옮긴 한 문장")
    evidence_chunk_id: str = Field(default="")
    reason: str = Field(default="")


class CandidateChunk(TypedDict):
    chunk_id: str
    text: str
    section_path: str
    rcept_no: str
    fiscal_year: int
    rank: int


class Candidate(TypedDict):
    stock_code: str
    corp_name: str
    best_rank: int
    chunks: list[CandidateChunk]


class JudgedCandidate(TypedDict):
    stock_code: str
    corp_name: str
    label: str
    evidence: str
    evidence_chunk_id: str
    rcept_no: str
    section_path: str
    reason: str
    evidence_verified: bool


class ThemeState(TypedDict, total=False):
    theme_name: str
    theme_description: str
    fiscal_year: int | None
    k_per_query: int
    top_chunks: int
    max_candidates: int
    skip_define: bool  # True 면 정의 노드를 건너뛰고 주어진 stages 를 그대로 쓴다 (C-1 R2 ablation)
    stages: list[dict]
    candidates: list[Candidate]
    judged: Annotated[list[JudgedCandidate], operator.add]
    basket: list[JudgedCandidate]
    approved: bool | None


class VerifyInput(TypedDict):
    theme_name: str
    theme_description: str
    candidate: Candidate
