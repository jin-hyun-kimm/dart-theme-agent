"""벡터 저장소: Chroma(persistent, 로컬 파일). 임베딩 이름마다 컬렉션 하나 (설계 D5).

교체 지점: 이 클래스만 바꾸면 pgvector/Qdrant 로 갈 수 있다.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from dta.config import INDEX_DIR


class VectorStore:
    def __init__(self, embedder_name: str, path: Path | None = None) -> None:
        import chromadb

        self.client = chromadb.PersistentClient(path=str(path or (INDEX_DIR / "chroma")))
        self.col = self.client.get_or_create_collection(
            name=f"reports_{embedder_name}", metadata={"hnsw:space": "cosine"}
        )

    def count(self) -> int:
        return self.col.count()

    def add(
        self, ids: list[str], embeddings: np.ndarray, documents: list[str], metadatas: list[dict]
    ) -> None:
        for i in range(0, len(ids), 500):
            sl = slice(i, i + 500)
            self.col.add(
                ids=ids[sl],
                embeddings=embeddings[sl].tolist(),
                documents=documents[sl],
                metadatas=metadatas[sl],
            )

    def query(
        self, embedding: np.ndarray, k: int = 20, where: dict | None = None
    ) -> list[tuple[str, float, str, dict]]:
        """returns [(chunk_id, similarity(0~1), document, metadata)] — 코사인 거리를 유사도로 바꿔 준다."""
        res = self.col.query(
            query_embeddings=[embedding.tolist()],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        out = []
        for cid, dist, doc, meta in zip(
            res["ids"][0], res["distances"][0], res["documents"][0], res["metadatas"][0], strict=True
        ):
            out.append((cid, 1.0 - float(dist), doc, meta))
        return out
