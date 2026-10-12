"""테마 5개의 밸류체인 단계·검색어를 '정의' 노드로 한 번 만들어 results/stages/{id}.json 에 둔다 (C-2 가 쓴다).

실행: PYTHONPATH=src .venv/bin/python scripts/make_stages.py   (LLM 호출 5회)
"""

import json

from dta.config import RESULTS_DIR
from dta.eval.themes import load_themes
from dta.graph.nodes import make_define_theme
from dta.llm import get_chat_model


def main() -> None:
    out_dir = RESULTS_DIR / "stages"
    out_dir.mkdir(parents=True, exist_ok=True)
    define = make_define_theme(get_chat_model)
    _, themes = load_themes()
    for t in themes:
        stages = define({"theme_name": t.name, "theme_description": t.description})["stages"]
        (out_dir / f"{t.id}.json").write_text(json.dumps(stages, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{t.name}] " + " / ".join(f"{s['name']}({len(s['queries'])})" for s in stages))
        for s in stages[:2]:
            print("   ", s["queries"])


if __name__ == "__main__":
    main()
