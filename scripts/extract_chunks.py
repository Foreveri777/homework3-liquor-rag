# -*- coding: utf-8 -*-
"""
提取财报 PDF：文字按页提取，表格用 pdfplumber 按行列还原成文字行；
随后切块，每块带 公司/报告/章节/页码 元数据。
产出：data/chunks.jsonl（每行一个块）
"""
import json
import os
import re

import fitz  # PyMuPDF
import pdfplumber

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PDF_DIR = os.path.abspath(os.path.join(BASE, "data", "pdfs"))
OUT = os.path.abspath(os.path.join(BASE, "data", "chunks.jsonl"))

MIN_CHUNK = 60          # 太短没有信息量
TARGET = 800            # 目标块长（字）
MAX_CHUNK = 1200

SECTION_RE = re.compile(r"^(第[一二三四五六七八九十百]+[章节]\s*.{0,30}|[一二三四五六七八九十]+、\s*.{0,30})$")


def table_to_lines(table):
    """把 pdfplumber 的二维表格还原成可读文字行。"""
    if not table:
        return []
    rows = [[("" if c is None else str(c).replace("\n", " ").strip()) for c in row] for row in table]
    rows = [r for r in rows if any(r)]
    if not rows:
        return []
    header = rows[0]
    lines = []
    for r in rows[1:]:
        pairs = []
        for h, v in zip(header, r):
            if v:
                pairs.append(f"{h}:{v}" if h else v)
        if pairs:
            lines.append("表格行 | " + " | ".join(pairs))
    return lines


def extract_pdf(path):
    """返回 [(page_no, [text_lines])]，文字行 + 表格还原行，按页组织。"""
    pages = {}
    with fitz.open(path) as doc:
        for i, page in enumerate(doc):
            text = page.get_text("text") or ""
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            pages[i + 1] = lines
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                tables = page.extract_tables() or []
                tbl_lines = []
                for t in tables:
                    tbl_lines.extend(table_to_lines(t))
                if tbl_lines:
                    pages.setdefault(i + 1, []).extend(tbl_lines)
    except Exception as e:
        print(f"  pdfplumber 跳过表格（{os.path.basename(path)}: {e}）")
    return sorted(pages.items())


def chunk_pages(pages, meta):
    """按页内行累积切块，每块附元数据；页内维护最近的章节名。"""
    chunks = []
    section = ""
    buf, buf_page = [], None
    seq = 0

    def flush():
        nonlocal buf, buf_page, seq
        text = "\n".join(buf).strip()
        buf = []
        if len(text) < MIN_CHUNK:
            return
        seq += 1
        chunks.append({
            "id": f"{meta['code']}-{meta['report']}-{seq:04d}",
            **meta,
            "section": section,
            "page": buf_page,
            "text": text[:MAX_CHUNK],
        })

    for page_no, lines in pages:
        for line in lines:
            m = SECTION_RE.match(line)
            if m and len(line) <= 40:
                section = line
            buf.append(line)
            if buf_page is None:
                buf_page = page_no
            if sum(len(x) for x in buf) >= TARGET:
                flush()
                buf_page = page_no
        flush()
        buf_page = None
    return chunks


def main():
    with open(os.path.join(PDF_DIR, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    total = 0
    with open(OUT, "w", encoding="utf-8") as out:
        for item in manifest:
            path = os.path.join(PDF_DIR, item["file"])
            if not os.path.exists(path):
                print(f"缺文件：{item['file']}")
                continue
            meta = {"code": item["code"], "company": item["name"], "report": item["type"]}
            pages = extract_pdf(path)
            chunks = chunk_pages(pages, meta)
            total += len(chunks)
            for c in chunks:
                out.write(json.dumps(c, ensure_ascii=False) + "\n")
            print(f"{item['name']} {item['type']}: {len(pages)} 页 -> {len(chunks)} 块")
    print(f"全部完成：{total} 块 -> {OUT}")


if __name__ == "__main__":
    main()
