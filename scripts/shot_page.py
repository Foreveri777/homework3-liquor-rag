# -*- coding: utf-8 -*-
"""打开问答页面、提问、截图（作业要求的页面截图）。"""
import os
import time

from DrissionPage import ChromiumPage

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.abspath(os.path.join(BASE, "results", "page_screenshot.png"))

page = ChromiumPage()
page.set.window.size(1280, 1000)
page.get("http://127.0.0.1:8321")
page.wait(2)
page.ele("#q").input("贵州茅台2026年上半年的营业收入是多少？同比增长了多少？")
page.ele("#go").click()
for _ in range(40):
    page.wait(2)
    if page.ele("css:.answer", timeout=1):
        page.wait(3)
        break
page.get_screenshot(path=OUT, full_page=True)
print("screenshot ->", OUT)
page.quit()
