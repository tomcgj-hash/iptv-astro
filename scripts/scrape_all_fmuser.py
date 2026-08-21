#!/usr/bin/env python3
"""抓取 FMUSER 全部分类下的所有产品（修复：匹配相对+绝对 URL，递归发现分类）。
输出: scripts/fmuser_all_products.json
"""
import json
import os
import re
import time
from urllib.request import Request, urlopen

for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
    os.environ.pop(k, None)

BASE = "https://www.fmradiobroadcast.com"


def fetch(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    with urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", errors="ignore")


def extract_products(html):
    """提取页面中所有产品详情链接（相对+绝对 URL 都匹配）"""
    pattern = r'<a[^>]*href="((?:https://www\.fmradiobroadcast\.com)?/product/detail/[^"]+\.html)"[^>]*>(.*?)</a>'
    items = re.findall(pattern, html, re.S)
    prods = {}
    for href, title_html in items:
        url = href if href.startswith("http") else BASE + href
        title = re.sub(r"<[^>]+>", " ", title_html)
        title = re.sub(r"\s+", " ", title).strip()
        if title and len(title) > 3:
            prods[url] = title
    return prods


def extract_categories(html):
    """提取页面中的分类链接（相对+绝对）"""
    pattern = r'href="((?:https://www\.fmradiobroadcast\.com)?/product/[a-z0-9-]+)"'
    cats = set()
    for href in re.findall(pattern, html):
        path = href.replace("https://www.fmradiobroadcast.com", "")
        if "/detail/" not in path and path != "/product":
            cats.add(path)
    return cats


def main():
    # BFS 发现所有分类
    todo = {"/product"}
    all_cats = set()
    all_products = {}

    while todo:
        cat = todo.pop()
        if cat in all_cats:
            continue
        all_cats.add(cat)
        try:
            html = fetch(BASE + cat)
        except Exception as e:
            print(f"  ✗ {cat}: {e}")
            continue
        prods = extract_products(html)
        for u, t in prods.items():
            all_products.setdefault(u, t)
        new_cats = extract_categories(html)
        todo |= (new_cats - all_cats)
        print(f"  {cat}: {len(prods)} 产品, 新分类 {len(new_cats - all_cats)}")
        time.sleep(0.5)

    # 输出
    result = [{"title": t, "url": u} for u, t in all_products.items()]
    result.sort(key=lambda x: x["title"].lower())
    with open("scripts/fmuser_all_products.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n=== 汇总 ===")
    print(f"发现分类: {len(all_cats)} 个")
    print(f"产品总数: {len(result)} 个")
    for p in result:
        print(f"  {p['title'][:70]}")


if __name__ == "__main__":
    main()
