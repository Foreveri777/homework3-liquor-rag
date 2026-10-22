# -*- coding: utf-8 -*-
"""
建索引（只跑一次）：
1. Qwen3-Embedding-0.6B（课堂起步推荐款，本机 CPU）把全部文本块向量化，1024 维
2. jieba 分词 + BM25Okapi 建 BM25 索引
产出：data/embeddings.npy、data/bm25.pkl
"""
import json
import os
import pickle
import time

import jieba
import numpy as np

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA = os.path.abspath(os.path.join(BASE, "data"))
CHUNKS = os.path.join(DATA, "chunks.jsonl")
EMB_OUT = os.path.join(DATA, "embeddings.npy")
BM25_OUT = os.path.join(DATA, "bm25.pkl")

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"


def load_chunks():
    chunks = []
    with open(CHUNKS, encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line))
    return chunks


def main():
    chunks = load_chunks()
    texts = [c["text"] for c in chunks]
    print(f"共 {len(chunks)} 块")

    t0 = time.time()
    import time as _t
    _t0 = _t.time()
    import torch
    torch.set_num_threads(8)   # 限制线程数，避免多进程抢核
    from modelscope import snapshot_download
    from sentence_transformers import SentenceTransformer
    model_dir = snapshot_download(MODEL_NAME)
    print(f"模型目录：{model_dir}")
    model = SentenceTransformer(model_dir, device="cpu")
    model.max_seq_length = 512          # 块长约 800 字，截断到 512 token 足够
    emb = model.encode(texts, batch_size=16, show_progress_bar=True,
                       normalize_embeddings=True)
    emb = np.asarray(emb, dtype=np.float32)
    np.save(EMB_OUT, emb)
    print(f"向量完成：{emb.shape}，耗时 {time.time()-t0:.0f}s")

    t0 = time.time()
    from rank_bm25 import BM25Okapi
    tokenized = [list(jieba.cut(t)) for t in texts]
    bm25 = BM25Okapi(tokenized)
    with open(BM25_OUT, "wb") as f:
        pickle.dump({"bm25": bm25, "ids": [c["id"] for c in chunks]}, f)
    print(f"BM25 完成，耗时 {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
