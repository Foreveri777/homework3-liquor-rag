# 白酒财报问答知识库（作业 3 · 方向 A）

同一批财报建一个能提问、答案带出处的问答知识库：10 家白酒上市公司的 2025 年报 + 2026 半年报，向量 + BM25 混合检索，DeepSeek 作答，每句带出处编号。

仓库：<https://github.com/Foreveri777/homework3-liquor-rag>

## 交付物

| 交付项 | 位置 |
| --- | --- |
| 代码仓库 | 本仓库 |
| 一页结论 | `results/conclusion.pdf` |
| 问答页面截图 | `results/page_screenshot.png` |
| 10 题逐题记录 | `results/qa_log.md` |

## 公司范围（10 家）

贵州茅台(600519)、五粮液(000858)、山西汾酒(600809)、洋河股份(002304)、泸州老窖(000568)、古井贡酒(000596)、今世缘(603369)、水井坊(600779)、舍得酒业(600702)、口子窖(603589)

## 目录结构

```
homework3/
├── scripts/
│   ├── download_reports.py   # 巨潮资讯批量下载财报（PDF 不入库，靠它重拉）
│   ├── extract_chunks.py     # 提文字 + pdfplumber 表格按行列还原 + 切块（带公司/章节/页码）
│   ├── build_index.py        # Qwen3-Embedding-0.6B 向量化 + BM25 索引（只跑一次）
│   └── run_eval.py           # 10 道题逐题记录 -> results/qa_log.md
├── web/
│   ├── server.py             # FastAPI：混合召回 top6 -> DeepSeek 作答（角标出处）
│   └── index.html            # 问答页面
├── results/
│   ├── qa_log.md             # 10 道题逐题记录 + 人工核对汇总
│   ├── page_screenshot.png   # 问答页面截图
│   └── conclusion.pdf        # 一页结论
├── data/                     # 财报 PDF、chunks.jsonl、索引（git 忽略，重跑脚本可再生成）
├── .env.example              # 密钥填这里（真实 .env 已 git 忽略）
└── .gitignore
```

## 怎么跑

```bash
pip install pymupdf pdfplumber rank_bm25 jieba fastapi "uvicorn[standard]" \
            numpy modelscope torch sentence-transformers curl_cffi

python scripts/download_reports.py   # 下载 20 份财报 PDF
python scripts/extract_chunks.py     # 提取切块 -> data/chunks.jsonl
python scripts/build_index.py        # 建向量+BM25 索引（首次会下载 1.2GB 模型）
python web/server.py                 # 起服务，打开 http://127.0.0.1:8321
```

密钥只放 `.env`（已加入 .gitignore），不进仓库、不下发浏览器。

## 技术要点

- **切块**：按页内文本行累积，目标约 800 字/块；表格经 pdfplumber 还原成「表头:值」文字行，与正文同库切块；每块带公司/报告/章节/页码。
- **检索**：Qwen3-Embedding-0.6B（1024 维，本机 CPU，课堂起步推荐款）余弦相似度 + jieba 分词 BM25，各自 min-max 归一后等权融合，取 top 6。
- **作答**：DeepSeek（deepseek-chat），系统提示要求只依据资料块、逐句标注 [n] 出处、材料未覆盖要明说。
