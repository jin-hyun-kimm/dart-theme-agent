"""임베딩 2종 (설계 D4). 맥 MPS 우선, 없으면 CPU."""

from __future__ import annotations

from functools import lru_cache

import numpy as np

MODELS = {"kure": "nlpai-lab/KURE-v1", "bge-m3": "BAAI/bge-m3"}


def device_name() -> str:
    import torch

    return "mps" if torch.backends.mps.is_available() else "cpu"


@lru_cache(maxsize=2)
def _load(name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODELS[name], device=device_name())


class Embedder:
    def __init__(self, name: str) -> None:
        if name not in MODELS:
            raise ValueError(f"모르는 임베딩 이름 {name}; 가능: {list(MODELS)}")
        self.name = name

    @property
    def model(self):
        return _load(self.name)

    def encode(self, texts: list[str], batch_size: int = 16) -> np.ndarray:
        return self.model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
