from pathlib import Path

from dta.guard.vocab import find_banned

ROOT = Path(__file__).resolve().parents[1]


def test_find_banned_detects_recommendation_words():
    assert find_banned("이 종목을 추천합니다") == ["추천"]
    assert "목표가" in find_banned("목표가 10만원")


def test_negated_recommendation_is_allowed():
    assert find_banned("종목·시점 추천은 하지 않는다") == []
    assert find_banned("이 도구는 추천하지 않는다") == []


def test_prompt_files_and_app_strings_have_no_banned_words():
    scanned = 0
    for folder in ("src/dta/graph/prompts", "src/dta/app", "src/dta/mcp_server"):
        for path in (ROOT / folder).rglob("*"):
            if path.suffix not in (".md", ".txt", ".py"):
                continue
            hits = find_banned(path.read_text(encoding="utf-8"))
            assert not hits, f"{path.relative_to(ROOT)}: {hits}"
            scanned += 1
    assert scanned >= 0
