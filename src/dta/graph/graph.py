"""테마 엔진 그래프 (설계 §4-2): 정의 → 검색 → 검증(병렬) → 조립 → 인간 게이트."""

from __future__ import annotations

from collections.abc import Callable

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from dta.graph.nodes import (
    assemble,
    fan_out_verify,
    human_gate,
    make_define_theme,
    make_retrieve,
    make_verify,
)
from dta.graph.state import ThemeState


def build_graph(llm_factory: Callable[[], object] | None = None, search_fn=None, with_gate: bool = True):
    if llm_factory is None:
        from dta.llm import get_chat_model

        llm_factory = get_chat_model
    if search_fn is None:
        from dta.index.search import get_searcher

        def search_fn(q: str, k: int, fy: int | None):
            return get_searcher().search(q, k=k, fiscal_year=fy)

    g = StateGraph(ThemeState)
    g.add_node("define_theme", make_define_theme(llm_factory))
    g.add_node("retrieve", make_retrieve(search_fn))
    g.add_node("verify", make_verify(llm_factory))
    g.add_node("assemble", assemble)
    g.add_edge(START, "define_theme")
    g.add_edge("define_theme", "retrieve")
    g.add_conditional_edges("retrieve", fan_out_verify, ["verify"])
    g.add_edge("verify", "assemble")
    if with_gate:
        g.add_node("human_gate", human_gate)
        g.add_edge("assemble", "human_gate")
        g.add_edge("human_gate", END)
    else:
        g.add_edge("assemble", END)
    return g.compile(checkpointer=InMemorySaver())
