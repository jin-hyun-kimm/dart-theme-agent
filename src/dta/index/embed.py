"""임베딩 2종 (설계 D4). 맥 MPS 우선, 없으면 CPU.

속도 옵션(.env): EMBED_MAX_SEQ(기본 0 = 모델 기본 8192) · EMBED_FP16(기본 0).
2026-10-12 실측(KURE, 청크 256): fp32/8192 16.3 청크/초, fp16/512 19.3 청크/초(1.18x) — cos 최소 0.9928(512 절단 탓).
18% 를 얻자고 절단·정밀도 손실을 감수하지 않는다. 기본은 fp32·절단 없음.
색인 빌드는 store.count() 부터 이어서 하므로(순서 고정) 옵션을 바꿔 재시작해도 앞부분을 잃지 않는다 —
단, 같은 컬렉션 안에서 fp16/fp32 를 섞지 않도록 한 번 정하면 끝까지 간다.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from dta.config import env

MODELS = {"kure": "nlpai-lab/KURE-v1", "bge-m3": "BAAI/bge-m3"}


def device_name() -> str:
    import torch

    return "mps" if torch.backends.mps.is_available() else "cpu"


@lru_cache(maxsize=2)
def _load(name: str):
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODELS[name], device=device_name())
    max_seq = int(env("EMBED_MAX_SEQ", "0") or 0)
    if max_seq > 0:
        model.max_seq_length = max_seq
    if device_name() == "mps" and (env("EMBED_FP16", "0") or "0") == "1":
        model.half()
    return model


class Embedder:
    def __init__(self, name: str) -> None:
        if name not in MODELS:
            raise ValueError(f"모르는 임베딩 이름 {name}; 가능: {list(MODELS)}")
        self.name = name

    @property
    def model(self):
        return _load(self.name)

    def encode(self, texts: list[str], batch_size: int = 16) -> np.ndarray:
        out = self.model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(out, dtype=np.float32)
