"""키워드 검색: kiwi 형태소 분석(명사·외래어·숫자·어근) + BM25Okapi. 색인은 pickle 로 저장."""

from __future__ import annotations

import pickle
from functools import lru_cache
from pathlib import Path

from rank_bm25 import BM25Okapi

_KEEP_TAGS = ("NNG", "NNP", "NNB", "SL", "SN", "XR", "SH")


@lru_cache(maxsize=1)
def _kiwi():
    from kiwipiepy import Kiwi

    return Kiwi(num_workers=0)


def tokenize(text: str) -> list[str]:
    toks = _kiwi().tokenize(text)
    return [t.form.lower() for t in toks if t.tag in _KEEP_TAGS and len(t.form) > 1 or t.tag == "SN"]


class BM25Index:
    def __init__(self, ids: list[str], tokenized: list[list[str]]) -> None:
        self.ids = ids
        self.bm25 = BM25Okapi(tokenized)

    @classmethod
    def build(cls, ids: list[str], texts: list[str]) -> BM25Index:
        return cls(ids, [tokenize(t) for t in texts])

    def search(self, query: str, k: int = 20) -> list[tuple[str, float]]:
        q = tokenize(query)
        if not q:
            return []
        scores = self.bm25.get_scores(q)
        order = scores.argsort()[::-1][:k]
        return [(self.ids[i], float(scores[i])) for i in order if scores[i] > 0]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"ids": self.ids, "bm25": self.bm25}, f)

    @classmethod
    def load(cls, path: Path) -> BM25Index:
        with open(path, "rb") as f:
            d = pickle.load(f)  # noqa: S301 — 우리가 만든 파일만 읽는다
        obj = cls.__new__(cls)
        obj.ids, obj.bm25 = d["ids"], d["bm25"]
        return obj
