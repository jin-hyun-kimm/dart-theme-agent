"""지표. 전부 분자·분모·n 을 같이 돌려준다 (설계 §4-3)."""

from __future__ import annotations


def _ratio(num: int, den: int) -> float | None:
    return (num / den) if den else None


def basket_metrics(
    basket: list[dict], gold_in_universe: set[str], include_labels: tuple[str, ...] = ("핵심", "관련")
) -> dict:
    predicted = {j["stock_code"] for j in basket if j["label"] in include_labels}
    tp = predicted & gold_in_universe
    unknown = [j for j in basket if j["label"] == "모름"]
    unknown_not_gold = [j for j in unknown if j["stock_code"] not in gold_in_universe]
    return {
        "n_predicted": len(predicted),
        "n_gold": len(gold_in_universe),
        "n_tp": len(tp),
        "precision": _ratio(len(tp), len(predicted)),
        "recall": _ratio(len(tp), len(gold_in_universe)),
        "n_candidates": len(basket),
        "n_unknown": len(unknown),
        "abstain_rate": _ratio(len(unknown), len(basket)),
        "abstain_correct": _ratio(len(unknown_not_gold), len(unknown)),
        "n_evidence_verified": sum(1 for j in basket if j.get("evidence_verified")),
    }


def recall_at_k(
    company_ranking: list[str], gold_in_universe: set[str], ks: tuple[int, ...] = (10, 30)
) -> dict:
    out = {"n_gold": len(gold_in_universe)}
    for k in ks:
        top = set(company_ranking[:k])
        out[f"recall@{k}"] = _ratio(len(top & gold_in_universe), len(gold_in_universe))
        out[f"hits@{k}"] = len(top & gold_in_universe)
    return out
