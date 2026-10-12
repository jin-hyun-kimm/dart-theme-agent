"""가짜 LLM·가짜 검색으로 그래프의 흐름·근거 검증·기권·게이트를 확인한다 (네트워크 0)."""

from dataclasses import dataclass

from langgraph.types import Command

from dta.graph.graph import build_graph
from dta.graph.nodes import evidence_in_chunk
from dta.graph.state import Judgement, Stage, ThemeDefinition


@dataclass
class _Chunk:
    chunk_id: str
    stock_code: str
    corp_name: str
    text: str
    section_path: str = "II > 1"
    rcept_no: str = "r1"
    fiscal_year: int = 2024


@dataclass
class _Hit:
    chunk: _Chunk
    rank: int
    score: float = 1.0


CORPUS = [
    _Chunk(
        "a:0",
        "000001",
        "원전주기기",
        "당사는 원자력 발전소용 주기기와 보조기기를 설계·제작하여 발전사에 공급하고 있습니다.",
    ),
    _Chunk(
        "b:0", "000002", "화장품사", "당사는 기초 화장품 브랜드를 운영하며 면세점과 온라인 채널로 판매합니다."
    ),
    _Chunk(
        "c:0",
        "000003",
        "건설사",
        "당사는 과거 원전 건설에 참여한 바 있으나 현재는 주택 사업에 집중하고 있습니다.",
    ),
]


def fake_search(query, k, fy):
    return [_Hit(c, i + 1) for i, c in enumerate(CORPUS)]


class FakeStructured:
    def __init__(self, schema):
        self.schema = schema

    def invoke(self, prompt):
        if self.schema is ThemeDefinition:
            return ThemeDefinition(stages=[Stage(name="주기기", queries=["원자로 주기기", "증기발생기"])])
        if "원전주기기" in prompt:
            return Judgement(
                label="핵심",
                evidence="당사는 원자력 발전소용 주기기와 보조기기를 설계·제작하여 발전사에 공급하고 있습니다.",
                evidence_chunk_id="a:0",
                reason="주기기 제작이 주 사업",
            )
        if "화장품사" in prompt:
            return Judgement(label="무관", reason="화장품")
        # 건설사: 라벨은 관련이라 했지만 근거를 바꿔 썼다 → 코드가 모름으로 내린다
        return Judgement(
            label="관련",
            evidence="당사는 원전 건설을 주력으로 한다",
            evidence_chunk_id="c:0",
            reason="원전 건설",
        )


class FakeLLM:
    def with_structured_output(self, schema):
        return FakeStructured(schema)


def test_evidence_must_be_verbatim():
    assert evidence_in_chunk(
        "주기기와  보조기기를 설계", "당사는 원자력 발전소용 주기기와 보조기기를 설계·제작"
    )
    assert not evidence_in_chunk("주기기를 만든다", "당사는 주기기와 보조기기를 설계")


def test_graph_end_to_end_with_gate():
    graph = build_graph(llm_factory=lambda: FakeLLM(), search_fn=fake_search)
    cfg = {"configurable": {"thread_id": "t1"}}
    state = {
        "theme_name": "원전",
        "theme_description": "원자력 발전 밸류체인",
        "k_per_query": 10,
        "top_chunks": 2,
    }
    out = graph.invoke(state, cfg)
    assert "__interrupt__" in out  # 게이트에서 멈춤
    snap = graph.get_state(cfg).values
    labels = {j["corp_name"]: j["label"] for j in snap["basket"]}
    assert labels == {"원전주기기": "핵심", "화장품사": "무관", "건설사": "모름"}
    bad = next(j for j in snap["basket"] if j["corp_name"] == "건설사")
    assert bad["evidence"] == "" and bad["evidence_verified"] is False and "원문과 일치하지" in bad["reason"]
    good = next(j for j in snap["basket"] if j["corp_name"] == "원전주기기")
    assert good["evidence_verified"] and good["rcept_no"] == "r1"
    out2 = graph.invoke(Command(resume={"approve": True}), cfg)
    assert out2["approved"] is True


def test_skip_define_keeps_given_stages():
    calls = {"define": 0}

    class CountingLLM(FakeLLM):
        def with_structured_output(self, schema):
            if schema is ThemeDefinition:
                calls["define"] += 1
            return FakeStructured(schema)

    graph = build_graph(llm_factory=lambda: CountingLLM(), search_fn=fake_search, with_gate=False)
    cfg = {"configurable": {"thread_id": "t2"}}
    out = graph.invoke(
        {"theme_name": "원전", "theme_description": "원자력 발전 밸류체인", "skip_define": True,
         "stages": [{"name": "전체", "queries": ["원자력 발전 밸류체인"]}]},
        cfg,
    )
    assert calls["define"] == 0
    assert out["stages"][0]["name"] == "전체"
    assert len(out["basket"]) == 3
