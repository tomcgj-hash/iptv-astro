#!/usr/bin/env python3
"""批量抓取 FMUSER 338 个核心产品的详情 + 图片。
输出: scripts/fmuser_core_details.json（增量，断点续抓）
"""
import json
import os
import re
import sys
import time
from urllib.request import Request, urlopen

for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
    os.environ.pop(k, None)

BASE = "https://www.fmradiobroadcast.com"
LIST = "scripts/fmuser_core_products.json"
OUT = "scripts/fmuser_core_details.json"
IMG_DIR = "public/images/products"
os.makedirs(IMG_DIR, exist_ok=True)

BAD_ALT = ("logo", "banner", "contact", "blank", "certification", "welcome-page")


def fetch(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    with urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", errors="ignore")


def download(url, dest):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=45) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


def pick_main_image(html):
    m = re.search(r'<img[^>]*class="[^"]*etalage_thumb_image[^"]*"[^>]*data-original="([^"]*)"', html)
    if not m:
        m = re.search(r'<img[^>]*data-original="([^"]*)"[^>]*class="[^"]*etalage_thumb_image[^"]*"', html)
    if m:
        src = m.group(1)
        return src if src.startswith("http") else (BASE + src if src.startswith("/") else "")
    m = re.search(r'<img[^>]*data-property="ImageUrl"[^>]*src="([^"]*)"', html)
    if m:
        src = m.group(1).split("?")[0]
        return src if src.startswith("http") else (BASE + src if src.startswith("/") else "")
    return ""


def slugify(name):
    n = re.sub(r"^\s*FMUSER\s+", "", name)
    n = re.sub(r"\s*\|.*$", "", n)
    n = re.sub(r"[:：].*$", "", n).strip()
    s = re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")
    return s[:80]


def parse_detail(url):
    html = fetch(url)
    desc = re.search(r'<meta name="description" content="([^"]*)"', html)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)

    specs = {}
    tables = re.findall(r"<table[^>]*>(.*?)</table>", html, re.S)
    for t in tables:
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)
        for r in rows:
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)
            clean_cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip() for c in cells]
            if len(clean_cells) >= 2 and clean_cells[0] and clean_cells[1] and clean_cells[0].lower() not in ("items", "specifications"):
                k = clean_cells[0][:80]
                if k not in specs:
                    specs[k] = clean_cells[1][:200]

    name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h1.group(1))).strip() if h1 else url.split("/")[-1]
    name = re.sub(r"^\s*FMUSER\s+", "", name)
    return {
        "name": name,
        "description": re.sub(r"\s+", " ", desc.group(1)).strip() if desc else "",
        "url": url,
        "specs": specs,
        "_html": html,  # 供图片提取复用，不写入最终数据
    }


def main():
    with open(LIST, encoding="utf-8") as f:
        items = json.load(f)

    # 断点续抓
    done = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            for d in json.load(f):
                done[d["url"]] = d

    total = len(items)
    for i, item in enumerate(items, 1):
        url = item["url"]
        if url in done:
            print(f"[{i}/{total}] 跳过（已抓）: {item['title'][:40]}")
            continue
        try:
            detail = parse_detail(url)
            detail["category"] = item["category"]
            # 下载图片（复用已抓的 HTML）
            img_url = pick_main_image(detail.pop("_html", ""))
            slug = slugify(detail["name"])
            if img_url:
                ext = os.path.splitext(img_url.split("?")[0])[1] or ".jpg"
                if ext.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                    ext = ".jpg"
                dest = os.path.join(IMG_DIR, slug + ext)
                try:
                    size = download(img_url, dest)
                    detail["image"] = f"/images/products/{slug}{ext}"
                    print(f"[{i}/{total}] ✓ {detail['name'][:45]} ({size//1024}KB)")
                except Exception as e:
                    detail["image"] = ""
                    print(f"[{i}/{total}] ✓ {detail['name'][:45]} (图失败:{e})")
            else:
                detail["image"] = ""
                print(f"[{i}/{total}] ✓ {detail['name'][:45]} (无图)")
            done[url] = detail
        except Exception as e:
            print(f"[{i}/{total}] ✗ {item['title'][:40]}: {e}")
            done[url] = {"name": item["title"], "description": "", "url": url,
                         "category": item["category"], "specs": {}, "image": "", "error": str(e)}

        # 每 5 个存一次
        if i % 5 == 0:
            with open(OUT, "w", encoding="utf-8") as f:
                json.dump(list(done.values()), f, ensure_ascii=False, indent=2)
        time.sleep(0.4)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(list(done.values()), f, ensure_ascii=False, indent=2)
    ok = sum(1 for d in done.values() if not d.get("error"))
    print(f"\n完成: {len(done)} 个（成功 {ok}）")


if __name__ == "__main__":
    main()
