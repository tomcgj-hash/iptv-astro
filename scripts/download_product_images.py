#!/usr/bin/env python3
"""下载 FMUSER 产品真实主图到本地 public/images/products/。

- 从 scripts/fmuser_products.json 读取产品 URL
- 抓详情页, 提取 data-property="ImageUrl" 的主图 (备选: og:image)
- 下载原图 (去掉 ?imageView 缩略参数) 到 public/images/products/<slug>.<ext>
- 输出映射 scripts/product_images.json = {slug: "/images/products/<file>"}

用法: python3 scripts/download_product_images.py
"""
import json
import os
import re
import sys
import time
from urllib.request import Request, urlopen

BASE = "https://www.fmradiobroadcast.com"
OUT_DIR = "public/images/products"
MAP_OUT = "scripts/product_images.json"

# 禁用系统代理 (环境变量指向无效代理)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(k, None)


def fetch(url, binary=False, timeout=45):
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "Referer": BASE + "/",
    })
    with urlopen(req, timeout=timeout) as r:
        data = r.read()
        return data if binary else data.decode("utf-8", errors="ignore")


def find_main_image(html):
    """优先产品图集第一张 (etalage_thumb_image), 其次 og:image, 最后模板 ImageUrl。"""
    m = re.search(
        r'<img[^>]*class="etalage_thumb_image"[^>]*data-original="([^"]+)"', html)
    if m:
        return m.group(1)
    m = re.search(
        r'<img[^>]*data-property="ImageUrl"[^>]*src="([^"]+)"', html)
    if m:
        return m.group(1)
    m = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
    if m:
        return m.group(1)
    # 兜底: etalage 无 data-original 时
    m = re.search(r'<img[^>]*class="etalage_thumb_image"[^>]*src="([^"]+)"', html)
    if m:
        return m.group(1)
    return None


def slugify(name):
    import html as _html
    clean = _html.unescape(name)
    clean = re.sub(r"^\s*FMUSER\s+", "", clean)
    clean = re.sub(r"\s*\|.*$", "", clean)
    clean = re.sub(r"[:：].*$", "", clean).strip()
    slug = re.sub(r"[^a-z0-9]+", "-", clean.lower()).strip("-")
    return slug or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:50]


def main():
    with open("scripts/fmuser_products.json", encoding="utf-8") as f:
        raw = json.load(f)

    os.makedirs(OUT_DIR, exist_ok=True)
    mapping = {}
    ok, fail = 0, 0

    for p in raw:
        url = p.get("url", "")
        name = p.get("name", "")
        slug = slugify(name)
        if not url or "error" in p:
            print(f"[skip] {slug}: 无 URL 或抓取失败")
            continue

        try:
            html = fetch(url)
        except Exception as e:
            print(f"[FAIL] {slug}: 页面抓取失败 {e}")
            fail += 1
            continue

        img = find_main_image(html)
        if not img:
            print(f"[WARN] {slug}: 未找到主图, 保留原图")
            fail += 1
            continue

        if img.startswith("/"):
            img = BASE + img
        # 去掉缩略参数 (?imageView2/2/q/75)
        img = re.sub(r"\?.*$", "", img)

        ext = os.path.splitext(img)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            ext = ".jpg"  # 无扩展名默认 jpg

        fname = f"{slug}{ext}"
        fpath = os.path.join(OUT_DIR, fname)
        try:
            data = fetch(img, binary=True)
            # 用 Content-Type 校验扩展名
            if ext == ".jpg" and data[:3] == b"\x89PNG":
                fname = f"{slug}.png"
                fpath = os.path.join(OUT_DIR, fname)
            with open(fpath, "wb") as f:
                f.write(data)
            mapping[slug] = f"/images/products/{fname}"
            print(f"[OK] {slug} <- {img} ({len(data)//1024} KB)")
            ok += 1
        except Exception as e:
            print(f"[FAIL] {slug}: 图片下载失败 {e}")
            fail += 1

        time.sleep(0.5)

    with open(MAP_OUT, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=1)

    print(f"\n完成: {ok} 成功, {fail} 失败/跳过. 映射 -> {MAP_OUT}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
