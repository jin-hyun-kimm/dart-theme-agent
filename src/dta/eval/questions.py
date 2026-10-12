"""C-3 질문 100개 생성기. 정답은 DART 재무 API(캐시)에서 계산한다 — 사람 라벨 0.

유형: single_cfs 40 · single_ofs 20 · yoy 20 · compare 20. 각 질문에 gold 값(원)과 허용오차(0.5%)를 붙인다.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import asdict, dataclass

from dta.config import RESULTS_DIR
from dta.data.corpus import load_manifest
from dta.data.dart_client import DartClient
from dta.data.financials import fetch_financials, pick

QUESTIONS_PATH = RESULTS_DIR / "c3_questions.jsonl"
ITEMS = {"revenue": "매출액", "operating_income": "영업이익", "net_income": "당기순이익"}


@dataclass(frozen=True)
class Question:
    qid: str
    qtype: str
    text: str
    gold_won: float
    gold_kind: str  # "won" | "pct" | "name"
    gold_name: str
    tolerance: float
    companies: list[str]
    fiscal_year: int
    fs_div: str
    item: str


def _fin(client, corp_code: str, year: int, fs_div: str):
    try:
        df = fetch_financials(client, corp_code, year, fs_div)
    except Exception:  # noqa: BLE001 — 한 회사 실패는 건너뛴다
        return None
    return df if len(df) else None


def generate(n_single_cfs=40, n_single_ofs=20, n_yoy=20, n_compare=20, seed=7) -> list[Question]:
    rnd = random.Random(seed)
    man = load_manifest()
    comps = man[man["status"] == "ok"][["stock_code", "corp_code", "corp_name"]].drop_duplicates("stock_code")
    comps = comps.sample(frac=1.0, random_state=seed).to_dict("records")
    client = DartClient()
    qs: list[Question] = []

    def single(fs_div: str, n: int, tag: str) -> None:
        i = 0
        for c in comps:
            if i >= n:
                break
            year = rnd.choice([2024, 2025])
            item = rnd.choice(list(ITEMS))
            df = _fin(client, c["corp_code"], year, fs_div)
            v = pick(df, item) if df is not None else None
            if v is None or v == 0:
                continue
            label = "연결" if fs_div == "CFS" else "별도"
            qs.append(
                Question(
                    f"{tag}{i:03d}",
                    tag,
                    f"{c['corp_name']}의 {year}년 {label} 기준 {ITEMS[item]}은 얼마인가? (억원 단위로 답하라)",
                    float(v),
                    "won",
                    c["corp_name"],
                    0.005,
                    [c["stock_code"]],
                    year,
                    fs_div,
                    item,
                )
            )
            i += 1

    single("CFS", n_single_cfs, "single_cfs")
    single("OFS", n_single_ofs, "single_ofs")

    i = 0
    for c in comps:
        if i >= n_yoy:
            break
        item = rnd.choice(list(ITEMS))
        d25, d24 = _fin(client, c["corp_code"], 2025, "CFS"), _fin(client, c["corp_code"], 2024, "CFS")
        v25 = pick(d25, item) if d25 is not None else None
        v24 = pick(d24, item) if d24 is not None else None
        if not v25 or not v24 or v24 <= 0 or v25 <= 0:
            continue
        pct = (v25 - v24) / v24 * 100
        qs.append(
            Question(
                f"yoy{i:03d}",
                "yoy",
                f"{c['corp_name']}의 2025년 연결 {ITEMS[item]}은 2024년 대비 몇 % 변했는가? (소수점 첫째 자리까지)",
                float(pct),
                "pct",
                c["corp_name"],
                0.3,
                [c["stock_code"]],
                2025,
                "CFS",
                item,
            )
        )
        i += 1

    i = 0
    for a, b in zip(comps[::2], comps[1::2], strict=False):
        if i >= n_compare:
            break
        item = rnd.choice(list(ITEMS))
        year = rnd.choice([2024, 2025])
        da, db = _fin(client, a["corp_code"], year, "CFS"), _fin(client, b["corp_code"], year, "CFS")
        va = pick(da, item) if da is not None else None
        vb = pick(db, item) if db is not None else None
        if va is None or vb is None or va == vb:
            continue
        winner = a if va > vb else b
        qs.append(
            Question(
                f"cmp{i:03d}",
                "compare",
                f"{a['corp_name']}과 {b['corp_name']} 중 {year}년 연결 {ITEMS[item]}이 더 큰 회사는 어디인가? 회사명으로 답하라.",
                float(max(va, vb)),
                "name",
                winner["corp_name"],
                0.0,
                [a["stock_code"], b["stock_code"]],
                year,
                "CFS",
                item,
            )
        )
        i += 1
    return qs


def save(qs: list[Question]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(QUESTIONS_PATH, "w", encoding="utf-8") as f:
        for q in qs:
            f.write(json.dumps(asdict(q), ensure_ascii=False) + "\n")


def load() -> list[Question]:
    with open(QUESTIONS_PATH, encoding="utf-8") as f:
        return [Question(**json.loads(line)) for line in f]


if __name__ == "__main__":
    questions = generate()
    save(questions)
    print(len(questions), Counter(q.qtype for q in questions))
