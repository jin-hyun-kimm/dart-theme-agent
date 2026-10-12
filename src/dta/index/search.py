"""검색: dense / hybrid(dense + BM25 → RRF). 결과를 기업 단위로 모은다 (그래프 '검색' 노드와 MCP search_report_text 가 공유)."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from dta.index.bm25 import BM25Index
from dta.index.build import BM25_PATH, load_chunks
from dta.index.chunk import Chunk
from dta.index.embed import Embedder
from dta.index.hybrid import rrf
from dta.index.store import VectorStore


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float
    rank: int


@dataclass
class CompanyHit:
    stock_code: str
    corp_name: str
    best_rank: int
    hits: list[Hit] = field(default_factory=list)


class Searcher:
    def __init__(
        self,
        embedder_name: str = "kure",
        mode: str = "hybrid",
        *,
        chunks: list[Chunk] | None = None,
        embedder=None,
        store: VectorStore | None = None,
        bm25: BM25Index | None = None,
    ) -> None:
        """기본은 디스크의 색인을 읽는다. 테스트는 chunks·embedder·store·bm25 를 주입한다."""
        if mode not in ("dense", "hybrid", "bm25"):
            raise ValueError(mode)
        self.mode = mode
        self.embedder = embedder if embedder is not None else Embedder(embedder_name)
        self.store = store if store is not None else VectorStore(embedder_name)
        self.chunks = {c.chunk_id: c for c in (chunks if chunks is not None else load_chunks())}
        if mode in ("hybrid", "bm25"):
            self.bm25 = bm25 if bm25 is not None else BM25Index.load(BM25_PATH)
        else:
            self.bm25 = None

    def search(self, query: str, k: int = 20, fiscal_year: int | None = None) -> list[Hit]:
        over = k * 3 if fiscal_year else k * 2
        dense_ids: list[str] = []
        if self.mode in ("dense", "hybrid"):
            where = {"fiscal_year": fiscal_year} if fiscal_year else None
            dense_ids = [
                cid
                for cid, _s, _d, _m in self.store.query(self.embedder.encode([query])[0], k=over, where=where)
            ]
        bm25_ids: list[str] = []
        if self.bm25 is not None:
            bm25_ids = [cid for cid, _s in self.bm25.search(query, k=over * 2)]
            if fiscal_year:
                bm25_ids = [cid for cid in bm25_ids if self.chunks[cid].fiscal_year == fiscal_year]
        if self.mode == "dense":
            ranked = [(cid, 1.0 / (i + 1)) for i, cid in enumerate(dense_ids)]
        elif self.mode == "bm25":
            ranked = [(cid, 1.0 / (i + 1)) for i, cid in enumerate(bm25_ids)]
        else:
            ranked = rrf([dense_ids, bm25_ids])
        out = []
        for rank, (cid, score) in enumerate(ranked[:k], start=1):
            if cid in self.chunks:
                out.append(Hit(chunk=self.chunks[cid], score=float(score), rank=rank))
        return out


def aggregate_by_company(hits: list[Hit], top_chunks: int = 3) -> list[CompanyHit]:
    by: dict[str, CompanyHit] = {}
    for h in hits:
        c = h.chunk
        ch = by.setdefault(
            c.stock_code, CompanyHit(stock_code=c.stock_code, corp_name=c.corp_name, best_rank=h.rank)
        )
        ch.best_rank = min(ch.best_rank, h.rank)
        if len(ch.hits) < top_chunks:
            ch.hits.append(h)
    return sorted(by.values(), key=lambda x: x.best_rank)


@lru_cache(maxsize=4)
def get_searcher(embedder_name: str = "kure", mode: str = "hybrid") -> Searcher:
    return Searcher(embedder_name, mode)
