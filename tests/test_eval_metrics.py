from dta.eval.metrics import basket_metrics, recall_at_k


def test_basket_metrics_with_abstention():
    basket = [
        {"stock_code": "1", "label": "핵심", "evidence_verified": True},
        {"stock_code": "2", "label": "관련", "evidence_verified": True},
        {"stock_code": "3", "label": "모름", "evidence_verified": False},
        {"stock_code": "4", "label": "모름", "evidence_verified": False},
        {"stock_code": "5", "label": "무관", "evidence_verified": False},
    ]
    m = basket_metrics(basket, {"1", "3", "9"})
    assert m["n_predicted"] == 2 and m["n_tp"] == 1
    assert m["precision"] == 0.5 and abs(m["recall"] - 1 / 3) < 1e-9
    assert m["n_unknown"] == 2 and m["abstain_correct"] == 0.5  # 3 은 정답인데 기권, 4 는 맞게 기권
    assert m["n_evidence_verified"] == 2


def test_recall_at_k_and_empty_gold():
    r = recall_at_k(["a", "b", "c"], {"b", "z"}, ks=(1, 2))
    assert r["recall@1"] == 0.0 and r["recall@2"] == 0.5
    assert recall_at_k(["a"], set())["recall@10"] is None
