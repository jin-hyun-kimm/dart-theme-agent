from dta.index.bm25 import BM25Index, tokenize
from dta.index.hybrid import rrf


def test_kiwi_tokenize_keeps_nouns():
    toks = tokenize("당사는 원자력 발전소용 주기기를 2025년부터 공급하고 있습니다")
    assert "원자력" in toks and "발전소" in toks
    assert "당사" in toks
    assert not any(t in ("는", "를", "있", "습니다") for t in toks)


def test_bm25_ranks_relevant_doc_first():
    idx = BM25Index.build(
        ["a", "b", "c"],
        ["원자력 발전소용 주기기와 보조기기를 제작한다", "화장품 브랜드를 운영한다", "가스터빈을 국산화했다"],
    )
    res = idx.search("원전 주기기 원자력", k=3)
    assert res and res[0][0] == "a"


def test_rrf_merges_rankings():
    merged = rrf([["a", "b", "c"], ["b", "a", "d"]])
    ids = [m[0] for m in merged]
    assert ids[:2] == ["a", "b"] or ids[:2] == ["b", "a"]
    assert "d" in ids and "c" in ids
