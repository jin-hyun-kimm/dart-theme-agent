"""임베딩 모델 2개를 내려받고 MPS 에서 속도·차원을 잰다. 로그: data/cache/probe_embeddings.log"""

import time

import torch
from sentence_transformers import SentenceTransformer

MODELS = {"kure": "nlpai-lab/KURE-v1", "bge-m3": "BAAI/bge-m3"}
device = "mps" if torch.backends.mps.is_available() else "cpu"
print("device:", device, "torch", torch.__version__, flush=True)
texts = [
    "당사는 원자력 발전소용 주기기와 보조기기를 설계·제작하여 국내외 발전사에 공급하고 있습니다. " * 6
] * 64
for name, mid in MODELS.items():
    t0 = time.time()
    m = SentenceTransformer(mid, device=device)
    t1 = time.time()
    e = m.encode(texts, batch_size=16, normalize_embeddings=True)
    t2 = time.time()
    print(
        f"{name}: load {t1 - t0:.0f}s, encode 64×~300자 {t2 - t1:.1f}s → {64 / (t2 - t1):.1f} 청크/초, dim={e.shape[1]}, max_seq={m.max_seq_length}",
        flush=True,
    )
