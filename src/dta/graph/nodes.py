"""그래프 노드. LLM 호출은 '정의'·'검증' 둘뿐 (설계 §4-2). 검색은 결정론."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from langgraph.types import Send, interrupt

from dta.graph.state import (
    Candidate,
    CandidateChunk,
    JudgedCandidate,
    Judgement,
    ThemeDefinition,
    ThemeState,
    VerifyInput,
)

PROMPTS = Path(__file__).parent / "prompts"
_WS = re.compile(r"\s+")


def _prompt(name: str, **kw: object) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8").format(**kw)


def _norm(s: str) -> str:
    return _WS.sub("", s)


def evidence_in_chunk(evidence: str, chunk_text: str) -> bool:
    """근거 문장이 원문에 글자 그대로(공백 무시) 들어 있는가. 바꿔 쓴 근거는 탈락."""
    e = _norm(evidence)
    return len(e) >= 10 and e in _norm(chunk_text)


def make_define_theme(llm_factory: Callable[[], object]):
    def define_theme(state: ThemeState) -> dict:
        llm = llm_factory()
        out: ThemeDefinition = llm.with_structured_output(ThemeDefinition).invoke(
            _prompt(
                "define_theme", theme_name=state["theme_name"], theme_description=state["theme_description"]
            )
        )
        return {"stages": [s.model_dump() for s in out.stages]}

    return define_theme


def make_retrieve(search_fn: Callable[[str, int, int | None], list]):
    """search_fn(query, k, fiscal_year) -> list[Hit] (dta.index.search.Hit 호환: .chunk, .rank)"""

    def retrieve(state: ThemeState) -> dict:
        k = state.get("k_per_query", 20)
        top_chunks = state.get("top_chunks", 3)
        fy = state.get("fiscal_year")
        by: dict[str, Candidate] = {}
        for stage in state.get("stages") or [{"name": "전체", "queries": [state["theme_description"]]}]:
            for q in stage["queries"]:
                for h in search_fn(q, k, fy):
                    c = h.chunk
                    cand = by.setdefault(
                        c.stock_code,
                        Candidate(
                            stock_code=c.stock_code, corp_name=c.corp_name, best_rank=h.rank, chunks=[]
                        ),
                    )
                    cand["best_rank"] = min(cand["best_rank"], h.rank)
                    if len(cand["chunks"]) < top_chunks and all(
                        x["chunk_id"] != c.chunk_id for x in cand["chunks"]
                    ):
                        cand["chunks"].append(
                            CandidateChunk(
                                chunk_id=c.chunk_id,
                                text=c.text,
                                section_path=c.section_path,
                                rcept_no=c.rcept_no,
                                fiscal_year=c.fiscal_year,
                                rank=h.rank,
                            )
                        )
        cands = sorted(by.values(), key=lambda x: x["best_rank"])[: state.get("max_candidates", 60)]
        return {"candidates": cands}

    return retrieve


def fan_out_verify(state: ThemeState) -> list[Send]:
    return [
        Send(
            "verify",
            VerifyInput(
                theme_name=state["theme_name"], theme_description=state["theme_description"], candidate=c
            ),
        )
        for c in state["candidates"]
    ]


def make_verify(llm_factory: Callable[[], object]):
    def verify(inp: VerifyInput) -> dict:
        cand = inp["candidate"]
        chunks_txt = "\n\n".join(
            f"[chunk_id={c['chunk_id']} | {c['section_path']}]\n{c['text']}" for c in cand["chunks"]
        )
        llm = llm_factory()
        try:
            j: Judgement = llm.with_structured_output(Judgement).invoke(
                _prompt(
                    "verify",
                    theme_name=inp["theme_name"],
                    theme_description=inp["theme_description"],
                    corp_name=cand["corp_name"],
                    stock_code=cand["stock_code"],
                    chunks=chunks_txt,
                )
            )
        except Exception as e:  # noqa: BLE001 — 실패는 모름 (fail-closed)
            j = Judgement(label="모름", reason=f"판정 실패: {type(e).__name__}")
        by_id = {c["chunk_id"]: c for c in cand["chunks"]}
        src = by_id.get(j.evidence_chunk_id)
        verified = bool(src) and evidence_in_chunk(j.evidence, src["text"])
        label = j.label
        reason = j.reason
        if label in ("핵심", "관련") and not verified:
            label, reason = "모름", "근거 문장이 원문과 일치하지 않음"
        return {
            "judged": [
                JudgedCandidate(
                    stock_code=cand["stock_code"],
                    corp_name=cand["corp_name"],
                    label=label,
                    evidence=j.evidence if verified else "",
                    evidence_chunk_id=j.evidence_chunk_id if verified else "",
                    rcept_no=src["rcept_no"] if src else "",
                    section_path=src["section_path"] if src else "",
                    reason=reason,
                    evidence_verified=verified,
                )
            ]
        }

    return verify


def assemble(state: ThemeState) -> dict:
    order = {"핵심": 0, "관련": 1, "모름": 2, "무관": 3}
    basket = sorted(state.get("judged", []), key=lambda j: (order.get(j["label"], 9), j["corp_name"]))
    return {"basket": basket}


def human_gate(state: ThemeState) -> dict:
    """확정 전 멈춤 (설계 D9). CLI 는 Command(resume={"approve": bool}) 로 이어 간다."""
    summary = {
        "theme": state["theme_name"],
        "n_core": sum(j["label"] == "핵심" for j in state["basket"]),
        "n_related": sum(j["label"] == "관련" for j in state["basket"]),
        "n_unknown": sum(j["label"] == "모름" for j in state["basket"]),
        "n_unrelated": sum(j["label"] == "무관" for j in state["basket"]),
    }
    answer = interrupt(summary)
    return {"approved": bool(answer.get("approve", False)) if isinstance(answer, dict) else bool(answer)}
