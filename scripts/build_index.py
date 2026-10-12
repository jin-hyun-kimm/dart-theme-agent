"""D2: 청크 → BM25 + 임베딩별 Chroma. 실행: PYTHONPATH=src .venv/bin/python scripts/build_index.py [kure bge-m3]"""

import sys
import time

from dta.index.build import build_bm25, build_chunks, build_vectors


def main(names: list[str]) -> None:
    t = time.time()
    chunks = build_chunks()
    print(f"청크 {len(chunks):,} ({time.time() - t:.0f}s)")
    t = time.time()
    build_bm25(chunks)
    print(f"BM25 완료 ({time.time() - t:.0f}s)")
    for name in names:
        t = time.time()
        store = build_vectors(chunks, name)
        print(f"{name}: {store.count():,} 벡터 ({time.time() - t:.0f}s)")


if __name__ == "__main__":
    main(sys.argv[1:] or ["kure", "bge-m3"])
