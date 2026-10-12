"""검색 계층을 가짜 임베더 + 임시 Chroma + 진짜 BM25 로 검사한다 (모델 다운로드 0)."""

import numpy as np

from dta.index.bm25 import BM25Index
from dta.index.chunk import Chunk
from dta.index.search import Searcher, aggregate_by_company
from dta.index.store import VectorStore

VOCAB = ["원자력", "원전", "주기기", "화장품", "브랜드", "가스터빈", "선박", "조선"]


class FakeEmbedder:
    """단어 포함 여부를 8차원 벡터로 — 의미 유사도의 아주 거친 대용."""

    def encode(self, texts, batch_size=16):
        vecs = np.array([[1.0 if w in t else 0.0 for w in VOCAB] for t in texts], dtype=float)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return vecs / np.where(norms == 0, 1, norms)


def _chunk(cid, stock, name, year, text):
    return Chunk(chunk_id=cid, corp_code="c" + stock, stock_code=stock, corp_name=name, fiscal_year=year,
                 rcept_no="r" + cid, section_path="II > 1", kind="p", text=text, first_order=0)


CHUNKS = [
    _chunk("a24", "000001", "두산", 2024, "원자력 발전소용 원전 주기기를 제작한다"),
    _chunk("a25", "000001", "두산", 2025, "원전 주기기와 가스터빈을 제작한다"),
    _chunk("b24", "000002", "아모레", 2024, "화장품 브랜드를 운영한다"),
    _chunk("c24", "000003", "HD현대", 2024, "선박을 건조하는 조선 회사다"),
    # 무관한 문서들 — 말뭉치가 너무 작으면 절반의 문서에 나오는 단어의 BM25 IDF 가 0 이 된다 (rank_bm25 특성)
    _chunk("d24", "000004", "은행", 2024, "예금과 대출을 취급하는 은행이다"),
    _chunk("e24", "000005", "통신", 2024, "이동통신 서비스를 제공한다"),
    _chunk("f24", "000006", "건설", 2024, "아파트를 짓는 건설 회사다"),
    _chunk("g24", "000007", "식품", 2024, "라면과 과자를 만든다"),
]


def _searcher(tmp_path, mode):
    emb = FakeEmbedder()
    store = VectorStore("fake", path=tmp_path / "chroma")
    store.add([c.chunk_id for c in CHUNKS], emb.encode([c.text for c in CHUNKS]), [c.text for c in CHUNKS],
              [{"stock_code": c.stock_code, "fiscal_year": c.fiscal_year} for c in CHUNKS])
    bm25 = BM25Index.build([c.chunk_id for c in CHUNKS], [c.text for c in CHUNKS])
    return Searcher("fake", mode, chunks=CHUNKS, embedder=emb, store=store, bm25=bm25)


def test_dense_hybrid_bm25_rank_relevant_first(tmp_path):
    for mode in ("dense", "hybrid", "bm25"):
        s = _searcher(tmp_path / mode, mode)
        hits = s.search("원전 주기기", k=4)
        assert hits and hits[0].chunk.stock_code == "000001", mode
        assert [h.rank for h in hits] == list(range(1, len(hits) + 1))


def test_fiscal_year_filter_applies_to_both_paths(tmp_path):
    s = _searcher(tmp_path, "hybrid")
    hits = s.search("원전 주기기", k=4, fiscal_year=2025)
    assert {h.chunk.fiscal_year for h in hits} == {2025}


def test_aggregate_by_company_keeps_best_rank_and_top_chunks(tmp_path):
    s = _searcher(tmp_path, "hybrid")
    comps = aggregate_by_company(s.search("원전 주기기 조선", k=4), top_chunks=1)
    assert comps[0].stock_code == "000001" and len(comps[0].hits) == 1
    assert [c.best_rank for c in comps] == sorted(c.best_rank for c in comps)
