# -*- coding: utf-8 -*-
"""
评测脚本：10 道题（8 道单公司 + 2 道跨公司全景题）逐题跑问答，
记录召回了哪些块、回答内容，写入 results/qa_log.md 供人工核对对错。
用法：python scripts/run_eval.py
"""
import datetime
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.abspath(os.path.join(BASE, "web")))
os.chdir(BASE)

import server  # noqa: E402  复用 server 里的索引加载、检索与回答

QUESTIONS = [
    # 8 道单公司题
    ("Q1", "贵州茅台2026年上半年的营业收入是多少？同比增长了多少？"),
    ("Q2", "五粮液2025年年度归属于上市公司股东的净利润是多少？"),
    ("Q3", "山西汾酒2026年上半年经营活动产生的现金流量净额是多少？"),
    ("Q4", "洋河股份2025年年度报告的现金分红方案是什么（每10股派多少元）？"),
    ("Q5", "泸州老窖2026年上半年销售费用是多少？占营业收入的比例大约多少？"),
    ("Q6", "古井贡酒2025年年报中合同负债的期末余额是多少？"),
    ("Q7", "今世缘2026年上半年省内市场的营业收入和占比是多少？"),
    ("Q8", "水井坊2025年年报中高档酒的营业收入是多少？"),
    # 2 道跨公司全景题
    ("Q9", "对比贵州茅台和五粮液2026年上半年的营业收入与净利润增速，哪家增长更快？"),
    ("Q10", "比较山西汾酒、洋河股份、泸州老窖三家公司2025年年报中的存货期末余额，哪家最高？"),
]

out_path = os.path.join(BASE, "results", "qa_log.md")
os.makedirs(os.path.dirname(out_path), exist_ok=True)

with open(out_path, "w", encoding="utf-8") as f:
    f.write("# 问答逐题记录（10 题）\n\n")
    f.write(f"生成时间：{datetime.datetime.now():%Y-%m-%d %H:%M}\n\n")
    for qid, q in QUESTIONS:
        print(f"=== {qid} {q[:24]}...")
        sources = server.hybrid_search(q, 6)
        answer = server.deepseek_answer(q, sources)
        f.write(f"## {qid} {q}\n\n")
        f.write("**召回的块**：\n\n")
        f.write("| # | 块ID | 公司 | 报告 | 页 | 向量cos | BM25 | 混合分 |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for i, s in enumerate(sources):
            f.write(f"| {i+1} | {s['id']} | {s['company']} | {s['report']} "
                    f"| {s['page']} | {s['cos']} | {s['bm25']} | {s['hybrid']} |\n")
        f.write("\n**回答**：\n\n")
        f.write(answer + "\n\n")
        f.write("**人工核对**：（待填：对/部分对/错，错在哪）\n\n---\n\n")
        f.flush()
print(f"完成 -> {out_path}")
