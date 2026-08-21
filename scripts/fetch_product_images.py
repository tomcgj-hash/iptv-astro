#!/usr/bin/env python3
"""从 FMUSER 产品详情页提取真实产品图片并下载到本地。
- 主图：alt 包含产品名关键词（排除 logo/banner/contact/blank）
- 下载到 public/images/products/<slug>.<ext>
- 更新 src/data/products.js 的 image 字段为本地路径
"""
import html
import json
import os
import re
import time
from urllib.request import Request, urlopen

# 禁用系统代理
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
    os.environ.pop(k, None)

BASE = "https://www.fmradiobroadcast.com"
RAW = "scripts/fmuser_products.json"
DATA_JS = "src/data/products.js"
OUT_DIR = "public/images/products"
os.makedirs(OUT_DIR, exist_ok=True)

# 排除的 alt 关键词
BAD_ALT = ("logo", "banner", "contact", "blank", "certification", "welcome-page",
           "system-", "-overview", "qam-", "isdb", "udp-ip", "dstv-", "hdmi-")


def fetch(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    with urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", errors="ignore")


def download(url, dest):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=40) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


def pick_main_image(html_text, product_slug):
    """选主图，优先级：
    1. 第一张 etalage_thumb_image（产品画廊图，每页不同 = 真实产品图）
    2. property="true" data-property="ImageUrl"（备选）
    """
    # 1. 第一张 etalage_thumb_image（真实产品图）
    m = re.search(r'<img[^>]*class="[^"]*etalage_thumb_image[^"]*"[^>]*data-original="([^"]*)"', html_text)
    if not m:
        # 兼容 data-original 在 class 前的情况
        m = re.search(r'<img[^>]*data-original="([^"]*)"[^>]*class="[^"]*etalage_thumb_image[^"]*"', html_text)
    if m:
        src = m.group(1)
        return src if src.startswith("http") else (BASE + src if src.startswith("/") else "")
    # 2. 产品主图标记（避免 Logo：必须 data-property="ImageUrl"）
    m = re.search(r'<img[^>]*data-property="ImageUrl"[^>]*src="([^"]*)"', html_text)
    if m:
        src = m.group(1).split("?")[0]
        return src if src.startswith("http") else (BASE + src if src.startswith("/") else "")
    return ""


def main():
    with open(RAW, encoding="utf-8") as f:
        raw = json.load(f)

    downloaded = []
    for p in raw:
        if "error" in p:
            continue
        raw_name = p["name"]
        clean_name = re.sub(r"^\s*FMUSER\s+", "", raw_name)
        clean_name = re.sub(r"\s*\|.*$", "", clean_name)
        clean_name = re.sub(r"[:：].*$", "", clean_name).strip()
        slug = re.sub(r"[^a-z0-9]+", "-", clean_name.lower()).strip("-")
        print(f"处理: {clean_name[:50]} ({slug})")
        try:
            html_text = fetch(p["url"])
            img_url = pick_main_image(html_text, slug)
            if not img_url:
                print(f"  ⚠ 未找到产品图，跳过")
                continue
            ext = os.path.splitext(img_url.split("?")[0])[1] or ".jpg"
            if ext.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                ext = ".jpg"
            dest = os.path.join(OUT_DIR, slug + ext)
            size = download(img_url, dest)
            p["image"] = f"/images/products/{slug}{ext}"
            downloaded.append((slug, size))
            print(f"  ✓ 下载 {size//1024}KB → {dest}")
        except Exception as e:
            print(f"  ✗ 失败: {e}")
        time.sleep(0.6)

    # 更新 src/data/products.js：按产品名匹配写入本地图片路径
    if os.path.exists(DATA_JS):
        with open(DATA_JS, encoding="utf-8") as f:
            js = f.read()
        m = re.search(r"export const PRODUCTS = (.*?);\s*$", js, re.S)
        if m:
            products = json.loads(m.group(1))
            for prod in products:
                # 在 raw 中找同 slug 的产品
                for p in raw:
                    if "error" in p:
                        continue
                    n = re.sub(r"^\s*FMUSER\s+", "", p["name"])
                    n = re.sub(r"\s*\|.*$", "", n)
                    n = re.sub(r"[:：].*$", "", n).strip()
                    s = re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")
                    if s == prod["slug"] and p.get("image", "").startswith("/images/"):
                        prod["image"] = p["image"]
                        break
            with open(DATA_JS, "w", encoding="utf-8") as f:
                f.write("// 产品数据 — 来源：FMUSER (www.fmradiobroadcast.com)\n")
                f.write("// 自动生成，勿手改。重新生成：python3 scripts/scrape_fmuser.py && python3 scripts/build_products_data.py\n")
                f.write("export const PRODUCTS = " + json.dumps(products, ensure_ascii=False, indent=2) + ";\n")
            print(f"\n已更新 {DATA_JS}")

    print(f"\n完成：下载 {len(downloaded)} 张产品图到 {OUT_DIR}/")


if __name__ == "__main__":
    main()
