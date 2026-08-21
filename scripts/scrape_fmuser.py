#!/usr/bin/env python3
"""批量抓取 FMUSER IPTV 相关产品信息，输出结构化 JSON。
用法: python3 scrape_fmuser.py
"""
import json
import re
import subprocess
import time
from urllib.request import Request, urlopen

BASE = "https://www.fmradiobroadcast.com"

# IPTV 相关产品页
PRODUCT_PAGES = [
    "/product/iptv-headend",
    "/product/catv-headend-equipment",
]

# 已知的 IPTV 产品详情页（从分类页提取）
DETAIL_PAGES = [
    "/product/detail/hotel-iptv.html",
    "/product/detail/fbe700-integrated-iptv-gateway.html",
    "/product/detail/fbe013-smart-magic-hotel-iptv-set-top-box-stb-kit.html",
    "/product/detail/hospitality-iptv-solution.html",
    "/product/detail/education-iptv-solution.html",
    "/product/detail/hospital-iptv-solution.html",
    "/product/detail/train-iptv-solution.html",
    "/product/detail/iptv-government-solution.html",
    "/product/detail/maritime-iptv-solution.html",
    "/product/detail/fitness-room-iptv-solution.html",
    "/product/detail/enterprise-iptv-solution.html",
    "/product/detail/prison-iptv-solution.html",
    "/product/detail/iptv-solution-for-isp.html",
]


def fetch(url):
    # 禁用系统代理（环境变量指向无效代理），直连
    import os
    for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
        os.environ.pop(k, None)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    with urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", errors="ignore")


def clean(html):
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_detail(path):
    url = BASE + path
    try:
        html = fetch(url)
    except Exception as e:
        return {"url": url, "error": str(e)}

    title = re.search(r"<title>(.*?)</title>", html, re.S)
    desc = re.search(r'<meta name="description" content="([^"]*)"', html)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)

    # 提取图片
    imgs = re.findall(r'<img[^>]*src="([^"]*(?:/UpLoad/|/Images/)[^"]*)"', html)
    main_img = imgs[0] if imgs else ""

    # 提取参数表
    specs = {}
    tables = re.findall(r"<table[^>]*>(.*?)</table>", html, re.S)
    for t in tables:
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)
        for r in rows:
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)
            clean_cells = [clean(c) for c in cells]
            if len(clean_cells) >= 2 and clean_cells[0] and clean_cells[1]:
                key = clean_cells[0][:80]
                if key not in specs:
                    specs[key] = clean_cells[1][:200]

    return {
        "name": clean(h1.group(1)) if h1 else (clean(title.group(1)) if title else path),
        "title": clean(title.group(1)) if title else "",
        "description": clean(desc.group(1)) if desc else "",
        "url": url,
        "image": main_img,
        "specs": specs,
    }


def main():
    results = []
    for path in DETAIL_PAGES:
        print(f"抓取: {path}")
        data = parse_detail(path)
        results.append(data)
        time.sleep(0.8)  # 礼貌间隔

    with open("fmuser_products.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n完成! 共 {len(results)} 个产品")
    for r in results:
        status = f"{len(r.get('specs', {}))} specs"
        if "error" in r:
            status = "ERROR: " + r["error"][:40]
        print(f"  - {r.get('name', 'N/A')[:55]:55s} [{status}]")


if __name__ == "__main__":
    main()
