# -*- coding: utf-8 -*-
"""用 Playwright 打开问答页面提问并截图（作业交付用页面截图）。"""
import os
from playwright.sync_api import sync_playwright

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.abspath(os.path.join(BASE, "results", "page_screenshot.png"))

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-proxy-server"])
    pg = b.new_page(viewport={"width": 1280, "height": 1000}, locale="zh-CN")
    pg.goto("http://127.0.0.1:8321", wait_until="load")
    pg.fill("#q", "贵州茅台2026年上半年的营业收入是多少？同比增长了多少？")
    pg.click("#go")
    pg.wait_for_selector(".answer", timeout=180000)
    pg.wait_for_timeout(2500)
    pg.screenshot(path=OUT, full_page=True)
    print("screenshot ->", OUT, os.path.getsize(OUT) if os.path.exists(OUT) else "?")
    b.close()
