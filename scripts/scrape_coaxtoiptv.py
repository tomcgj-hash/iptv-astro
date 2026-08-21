#!/usr/bin/env python3
"""抓取 coaxtoiptv.com 全部产品详情 + 图片，替换 FMUSER 数据。
输出: scripts/coaxtoiptv_products.json
"""
import json
import os
import re
import time
from urllib.request import Request, urlopen

for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
    os.environ.pop(k, None)

BASE = "https://www.coaxtoiptv.com"
LIST = "scripts/coaxtoiptv_product_urls.json"
OUT = "scripts/coaxtoiptv_products.json"
IMG_DIR = "public/images/coax"
os.makedirs(IMG_DIR, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"


def fetch(url):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", errors="ignore")


def download(url, dest):
    # URL 中的空格和特殊字符需要编码（图片文件名含空格）
    from urllib.parse import quote
    encoded = quote(url, safe=':/?&=#%')
    req = Request(encoded, headers={"User-Agent": UA})
    with urlopen(req, timeout=45) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


def clean(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip()


def parse_detail(url):
    html = fetch(url)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    name = clean(h1.group(1)) if h1 else url.split("/")[-1]
    desc = re.search(r'<meta name="description" content="([^"]*)"', html)

    # 图片（/images/products/ 路径，URL 编码空格）
    imgs = re.findall(r'<img[^>]*src="(/images/products/[^"]+)"', html)
    seen_imgs = []
    for i in imgs:
        if i not in seen_imgs:
            seen_imgs.append(i)

    # 规格表
    specs = {}
    tables = re.findall(r"<table[^>]*>(.*?)</table>", html, re.S)
    for t in tables:
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)
        for r in rows:
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)
            cc = [clean(c) for c in cells]
            if len(cc) >= 2 and cc[0] and cc[1] and cc[0].lower() not in ("items", "specifications", "parameter", "parameters"):
                k = cc[0][:80]
                if k not in specs:
                    specs[k] = cc[1][:200]

    return {
        "name": name,
        "description": clean(desc.group(1)) if desc else "",
        "url": url,
        "images": seen_imgs,
        "specs": specs,
    }


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:80]


def main():
    with open(LIST, encoding="utf-8") as f:
        urls = json.load(f)

    done = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            for d in json.load(f):
                done[d["url"]] = d

    total = len(urls)
    for i, item in enumerate(urls, 1):
        url = BASE + item["url"]
        if url in done:
            print(f"[{i}/{total}] 跳过: {item['url']}")
            continue
        try:
            detail = parse_detail(url)
            detail["category"] = item["category"]
            # 下载图片
            gallery = []
            for gi, img in enumerate(detail["images"][:6], 1):
                img_url = BASE + img
                ext = os.path.splitext(img.split("?")[0])[1] or ".jpg"
                slug = slugify(detail["name"])
                dest = os.path.join(IMG_DIR, f"{slug}-{gi}{ext}")
                try:
                    size = download(img_url, dest)
                    gallery.append(f"/images/coax/{slug}-{gi}{ext}")
                except Exception as e:
                    print(f"    图失败 {img}: {str(e)[:40]}")
                    continue
            detail["image"] = gallery[0] if gallery else ""
            detail["gallery"] = gallery
            detail.pop("images", None)
            done[url] = detail
            print(f"[{i}/{total}] ✓ {detail['name'][:50]} ({len(gallery)}图, {len(detail['specs'])}规格)")
        except Exception as e:
            print(f"[{i}/{total}] ✗ {item['url']}: {str(e)[:60]}")
            done[url] = {"name": item["title"], "description": "", "url": url,
                         "category": item["category"], "specs": {}, "image": "", "gallery": [], "error": str(e)}

        if i % 5 == 0:
            with open(OUT, "w", encoding="utf-8") as f:
                json.dump(list(done.values()), f, ensure_ascii=False, indent=2)
        time.sleep(0.3)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(list(done.values()), f, ensure_ascii=False, indent=2)
    ok = sum(1 for d in done.values() if not d.get("error"))
    print(f"\n完成: {len(done)} 个（成功 {ok}）")


if __name__ == "__main__":
    main()
