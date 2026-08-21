#!/usr/bin/env python3
"""抓取 FMUSER 产品的全部画廊图片（多图），更新 products.js 增加 gallery 字段。
每个产品下载最多 6 张图：主图 + 细节/应用图。
"""
import json
import os
import re
import time
from urllib.request import Request, urlopen

for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
    os.environ.pop(k, None)

BASE = "https://www.fmradiobroadcast.com"
DATA_JS = "src/data/products.js"
IMG_DIR = "public/images/products"
MAX_GALLERY = 6

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


def extract_gallery(html):
    """提取详情页所有 etalage_thumb_image 图片 URL（去重，绝对 URL）"""
    urls = re.findall(r'<img[^>]*class="[^"]*etalage_thumb_image[^"]*"[^>]*data-original="([^"]*)"', html)
    if not urls:
        urls = re.findall(r'<img[^>]*data-original="([^"]*)"[^>]*class="[^"]*etalage_thumb_image[^"]*"', html)
    seen = []
    for u in urls:
        if u.startswith("http"):
            full = u
        elif u.startswith("/"):
            full = BASE + u
        else:
            continue
        if full not in seen:
            seen.append(full)
    return seen


def main():
    with open(DATA_JS, encoding="utf-8") as f:
        js = f.read()
    m = re.search(r"export const PRODUCTS = (.*?);\s*$", js, re.S)
    products = json.loads(m.group(1))
    m_cat = re.search(r"export const CAT_NAMES = (.*?);", js, re.S)
    cat_names = json.loads(m_cat.group(1)) if m_cat else {}

    def save():
        with open(DATA_JS, "w", encoding="utf-8") as f:
            f.write("// 产品数据 — 来源：FMUSER (www.fmradiobroadcast.com)\n")
            f.write("// 自动生成，勿手改。\n")
            f.write("export const CAT_NAMES = " + json.dumps(cat_names, ensure_ascii=False) + ";\n\n")
            f.write("export const PRODUCTS = " + json.dumps(products, ensure_ascii=False, indent=2) + ";\n")

    total = len(products)
    updated = 0
    for i, p in enumerate(products, 1):
        if not p.get("source_url"):
            continue
        try:
            html = fetch(p["source_url"])
            gallery_urls = extract_gallery(html)
            if not gallery_urls:
                print(f"[{i}/{total}] {p['slug'][:40]:40s} 无画廊图")
                continue

            # 下载图片，命名 slug-1, slug-2, ...
            gallery = []
            for gi, gurl in enumerate(gallery_urls[:MAX_GALLERY], 1):
                ext = os.path.splitext(gurl.split("?")[0])[1] or ".jpg"
                if ext.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                    ext = ".jpg"
                dest = os.path.join(IMG_DIR, f"{p['slug']}-{gi}{ext}")
                if not os.path.exists(dest):
                    try:
                        download(gurl, dest)
                    except Exception:
                        continue
                gallery.append(f"/images/products/{p['slug']}-{gi}{ext}")

            if gallery:
                # 主图 = 第一张；gallery = 全部
                p["image"] = gallery[0]
                p["gallery"] = gallery
                updated += 1
                print(f"[{i}/{total}] ✓ {p['slug'][:40]:40s} {len(gallery)} 图")
            else:
                print(f"[{i}/{total}] {p['slug'][:40]:40s} 下载失败")
        except Exception as e:
            print(f"[{i}/{total}] ✗ {p['slug'][:40]:40s} {str(e)[:50]}")
        if i % 5 == 0:
            save()
        time.sleep(0.3)

    save()

    total_imgs = sum(len(p.get("gallery", [p.get("image")] if p.get("image") else [])) for p in products)
    print(f"\n完成: {updated} 个产品更新为多图, 全库图片 {total_imgs} 张")


if __name__ == "__main__":
    main()
