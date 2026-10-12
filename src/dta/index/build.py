"""색인 빌드: 매니페스트(ok) → 청크 → (임베딩별) Chroma + BM25. 재실행 가능."""

from __future__ import annotations

import json
import sys
import time

from dta.config import INDEX_DIR
from dta.data.corpus import load_manifest, load_paragraphs
from dta.index.bm25 import BM25Index
from dta.index.chunk import Chunk, chunk_paragraphs
from dta.index.embed import Embedder
from dta.index.store import VectorStore

CHUNKS_PATH = INDEX_DIR / "chunks.jsonl"
BM25_PATH = INDEX_DIR / "bm25.pkl"
# 설계 D15(2026-10-12 실측 뒤 추가): '3. 원재료 및 생산설비'·'5. 위험관리 및 파생거래' 의 표 행은 숫자뿐이라 색인에서 뺀다.
# 문단(p)은 모든 소절에서 넣는다. 되돌리기: 이 튜플을 비우고 build_chunks(force=True).
SKIP_TABLE_SUBSECTIONS = ("3.", "5.")


def _keep(p) -> bool:
    if p.kind != "table_row":
        return True
    sub = p.section_path.split(" > ")[-1].strip()
    return not sub.startswith(SKIP_TABLE_SUBSECTIONS)


def build_chunks(force: bool = False) -> list[Chunk]:
    if CHUNKS_PATH.exists() and not force:
        return load_chunks()
    man = load_manifest()
    chunks: list[Chunk] = []
    for r in man[man["status"] == "ok"].itertuples():
        paras = [p for p in load_paragraphs(str(r.rcept_no)) if _keep(p)]
        chunks.extend(
            chunk_paragraphs(
                paras,
                corp_code=str(r.corp_code),
                stock_code=str(r.stock_code),
                corp_name=str(r.corp_name),
                fiscal_year=int(r.fiscal_year),
                rcept_no=str(r.rcept_no),
            )
        )
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
    return chunks


def load_chunks() -> list[Chunk]:
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        return [Chunk(**json.loads(line)) for line in f]


def build_bm25(chunks: list[Chunk], force: bool = False) -> BM25Index:
    if BM25_PATH.exists() and not force:
        return BM25Index.load(BM25_PATH)
    idx = BM25Index.build([c.chunk_id for c in chunks], [c.text for c in chunks])
    idx.save(BM25_PATH)
    return idx


def build_vectors(chunks: list[Chunk], embedder_name: str, log=sys.stderr, batch: int = 256) -> VectorStore:
    store = VectorStore(embedder_name)
    if store.count() >= len(chunks):
        return store
    emb = Embedder(embedder_name)
    t0 = time.time()
    have = store.count()
    for i in range(have, len(chunks), batch):
        part = chunks[i : i + batch]
        vecs = emb.encode([c.text for c in part])
        metas = [
            {
                "stock_code": c.stock_code,
                "corp_code": c.corp_code,
                "corp_name": c.corp_name,
                "fiscal_year": c.fiscal_year,
                "rcept_no": c.rcept_no,
                "section_path": c.section_path,
                "kind": c.kind,
            }
            for c in part
        ]
        store.add([c.chunk_id for c in part], vecs, [c.text for c in part], metas)
        if (i // batch) % 10 == 0:
            rate = (i + len(part) - have) / max(time.time() - t0, 1e-6)
            print(
                f"  [{embedder_name}] {i + len(part)}/{len(chunks)} ({rate:.0f} 청크/초)",
                file=log,
                flush=True,
            )
    return store
