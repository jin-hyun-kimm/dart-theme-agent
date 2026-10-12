"""C-1 R1 바스켓을 라벨별로 펼쳐 본다: 핵심/관련/모름/무관 × 정답 여부. '핵심만' 정밀도·재현율도 낸다.

실행: PYTHONPATH=src .venv/bin/python scripts/c1_breakdown.py
"""

import json

from dta.config import RESULTS_DIR
from dta.eval.gold import build_gold
from dta.eval.metrics import basket_metrics
from dta.eval.themes import load_themes

date, themes = load_themes()
rows = []
for t in themes:
    p = RESULTS_DIR / "c1_baskets" / f"{t.id}_R1.json"
    if not p.exists():
        continue
    gold = set(build_gold(t, date).in_universe)
    basket = json.loads(p.read_text(encoding="utf-8"))["basket"]
    m_all = basket_metrics(basket, gold)
    m_core = basket_metrics(basket, gold, include_labels=("핵심",))
    rows.append((t.name, m_all, m_core))
    print(f"\n=== {t.name} · 정답 {len(gold)} ===")
    for label in ("핵심", "관련", "모름", "무관"):
        names = [f"{'★' if j['stock_code'] in gold else '·'}{j['corp_name']}" for j in basket if j["label"] == label]
        print(f"  {label}({len(names)}): " + " ".join(names))
    print(f"  핵심+관련: P {m_all['precision']:.2f} R {m_all['recall']:.2f} | 핵심만: P {m_core['precision']:.2f} R {m_core['recall']:.2f}")
print("\n| 테마 | 핵심+관련 P | R | 핵심만 P | R |")
print("|---|---|---|---|---|")
for name, a, c in rows:
    print(f"| {name} | {a['precision']:.2f} | {a['recall']:.2f} | {c['precision']:.2f} | {c['recall']:.2f} |")
n = len(rows)
print(f"| 평균 | {sum(a['precision'] for _, a, _ in rows)/n:.2f} | {sum(a['recall'] for _, a, _ in rows)/n:.2f} | {sum(c['precision'] for _, _, c in rows)/n:.2f} | {sum(c['recall'] for _, _, c in rows)/n:.2f} |")
