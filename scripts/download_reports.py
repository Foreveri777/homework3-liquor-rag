# -*- coding: utf-8 -*-
"""
从巨潮资讯（cninfo.com.cn）批量下载白酒上市公司财报 PDF。
用法：python scripts/download_reports.py
产出：data/pdfs/<代码>_<简称>_<报告类型>.pdf 与 data/pdfs/manifest.json
说明：财报 PDF 体积大，不入 git 仓库；本脚本即为作业要求的「下载脚本」。
"""
import json
import os
import time

from curl_cffi import requests

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PDF_DIR = os.path.abspath(os.path.join(BASE, "data", "pdfs"))
os.makedirs(PDF_DIR, exist_ok=True)

# 10 家白酒上市公司
COMPANIES = [
    ("600519", "贵州茅台"),
    ("000858", "五粮液"),
    ("600809", "山西汾酒"),
    ("002304", "洋河股份"),
    ("000568", "泸州老窖"),
    ("000596", "古井贡酒"),
    ("603369", "今世缘"),
    ("600779", "水井坊"),
    ("600702", "舍得酒业"),
    ("603589", "口子窖"),
]

# 要下载的报告类型：category -> (文件名标记, 标题必须包含, 标题不得包含)
WANT = [
    ("category_ndbg_szsh", "年报", ["年度报告"], ["摘要", "英文", "取消", "已取消", "H股"]),
    ("category_bndbg_szsh", "半年报", ["半年度报告"], ["摘要", "英文", "取消", "已取消", "H股"]),
]

session = requests.Session(impersonate="chrome")
session.headers.update({
    "Referer": "https://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/notice",
    "Origin": "https://www.cninfo.com.cn",
})


def get_org_id(code, name):
    r = session.post(
        "https://www.cninfo.com.cn/new/information/topSearch/query",
        data={"keyWord": name, "maxNum": 10},
        timeout=20,
    )
    for item in r.json():
        if item.get("code") == code:
            return item["orgId"]
    raise RuntimeError(f"找不到 orgId: {code} {name}")


def latest_report(code, org_id, category, must, must_not):
    r = session.post(
        "https://www.cninfo.com.cn/new/hisAnnouncement/query",
        data={
            "pageNum": 1,
            "pageSize": 30,
            "column": "szse" if code.startswith(("0", "3")) else "sse",
            "tabName": "fulltext",
            "stock": f"{code},{org_id}",
            "category": category,
            "isHLtitle": "true",
        },
        timeout=20,
    )
    for ann in r.json().get("announcements") or []:
        title = ann.get("announcementTitle", "")
        title = title.replace("<em>", "").replace("</em>", "")
        if all(k in title for k in must) and not any(k in title for k in must_not):
            return title, ann["adjunctUrl"]
    return None, None


def download(url_path, out_path):
    url = "https://static.cninfo.com.cn/" + url_path
    r = session.get(url, timeout=120)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(r.content)
    return len(r.content)


def main():
    manifest = []
    for code, name in COMPANIES:
        org_id = get_org_id(code, name)
        print(f"[{code} {name}] orgId={org_id}")
        for category, tag, must, must_not in WANT:
            title, path = latest_report(code, org_id, category, must, must_not)
            if not path:
                print(f"  !! 未找到 {tag}")
                continue
            out = os.path.join(PDF_DIR, f"{code}_{name}_{tag}.pdf")
            if os.path.exists(out) and os.path.getsize(out) > 100000:
                size = os.path.getsize(out)
                print(f"  已存在 {os.path.basename(out)}")
            else:
                size = download(path, out)
                print(f"  下载 {title} -> {size/1024/1024:.1f} MB")
                time.sleep(1)
            manifest.append({
                "code": code, "name": name, "type": tag,
                "title": title, "file": os.path.basename(out),
            })
    with open(os.path.join(PDF_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"完成，共 {len(manifest)} 份，清单见 manifest.json")


if __name__ == "__main__":
    main()
