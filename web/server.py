# -*- coding: utf-8 -*-
"""
问答服务：向量 + BM25 混合召回 top-k，交 DeepSeek 作答，答案每句带出处编号。
启动：python web/server.py   然后浏览器打开 http://127.0.0.1:8321
"""
import json
import os
import pickle

import numpy as np
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA = os.path.abspath(os.path.join(BASE, "data"))
WEB = os.path.dirname(os.path.abspath(__file__))

TOP_K = 6
MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
QUERY_PREFIX = ("Instruct: Given a web search query, retrieve relevant "
                "passages that answer the query\nQuery:")

# ---------- 加载 .env ----------
env_path = os.path.join(BASE, ".env")
if os.path.exists(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# ---------- 启动时加载索引 ----------
print("加载索引与模型……")
chunks = []
with open(os.path.join(DATA, "chunks.jsonl"), encoding="utf-8") as f:
    for line in f:
        chunks.append(json.loads(line))
id2idx = {c["id"]: i for i, c in enumerate(chunks)}
embeddings = np.load(os.path.join(DATA, "embeddings.npy"))
with open(os.path.join(DATA, "bm25.pkl"), "rb") as f:
    bm25_pack = pickle.load(f)
bm25 = bm25_pack["bm25"]

from modelscope import snapshot_download
from sentence_transformers import SentenceTransformer
model = SentenceTransformer(snapshot_download(MODEL_NAME), device="cpu")

import jieba  # noqa: E402

app = FastAPI()


COMPANIES = sorted({c["company"] for c in chunks})


def meta_filter(question):
    """问题里提到公司名 / 报告类型时，先在对应范围的块里找（跨公司题则限定这几家）。"""
    hit = [co for co in COMPANIES if co in question]
    report = None
    if "半年" in question and "年报" not in question:
        report = "半年报"
    elif "年报" in question or "年度报告" in question:
        report = "年报"
    if not hit and not report:
        return None
    idxs = [i for i, c in enumerate(chunks)
            if (not hit or c["company"] in hit) and (not report or c["report"] == report)]
    return idxs or None


def hybrid_search(question, k=TOP_K):
    q_emb = model.encode([QUERY_PREFIX + question], normalize_embeddings=True)
    vec = np.asarray(q_emb[0], dtype=np.float32)
    cos = embeddings @ vec                      # 已归一化，点积即余弦
    bm = np.asarray(bm25.get_scores(list(jieba.cut(question))), dtype=np.float32)

    def norm(x):
        lo, hi = float(x.min()), float(x.max())
        return (x - lo) / (hi - lo + 1e-9)

    hybrid = 0.5 * norm(cos) + 0.5 * norm(bm)
    idxs = meta_filter(question)
    pool = np.asarray(idxs) if idxs is not None else np.arange(len(chunks))
    sub = pool[np.argsort(-hybrid[pool])[:k]]
    results = []
    for i in sub:
        c = chunks[int(i)]
        results.append({
            "id": c["id"], "company": c["company"], "report": c["report"],
            "section": c["section"], "page": c["page"],
            "cos": round(float(cos[int(i)]), 3),
            "bm25": round(float(bm[int(i)]), 2),
            "hybrid": round(float(hybrid[int(i)]), 3),
            "text": c["text"],
        })
    return results


def deepseek_answer(question, sources):
    from curl_cffi import requests
    src_text = "\n\n".join(
        f"[{i+1}] {s['company']}·{s['report']}·第{s['page']}页"
        f"（{s['section'] or '无章节'}）\n{s['text']}"
        for i, s in enumerate(sources)
    )
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": (
                "你是一个严谨的财报问答助手。只依据给出的资料块回答问题；"
                "每个事实性句子末尾标注来源编号，格式如 [1][2]；"
                "资料块里没有的信息，明确回答『材料未覆盖』，不要编造数字。")},
            {"role": "user", "content": f"问题：{question}\n\n资料块：\n{src_text}"},
        ],
        "temperature": 0.1,
    }
    r = requests.post(
        "https://api.deepseek.com/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
        timeout=120,
    )
    data = r.json()
    return data["choices"][0]["message"]["content"]


class AskBody(BaseModel):
    question: str
    k: int = TOP_K


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB, "index.html"))


@app.post("/api/ask")
def ask(body: AskBody):
    if not body.question.strip():
        return JSONResponse({"error": "空问题"}, status_code=400)
    sources = hybrid_search(body.question.strip(), body.k)
    answer = deepseek_answer(body.question.strip(), sources)
    return {"answer": answer, "sources": sources}


@app.get("/api/chunk")
def chunk(id: str):
    i = id2idx.get(id)
    if i is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return chunks[i]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8321)
