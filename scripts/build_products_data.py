#!/usr/bin/env python3
"""清洗 FMUSER 产品数据 → 生成网站用 src/data/products.js
- 从 name 提取 slug、简短标题、分类
- 清理描述里的 HTML 实体
- 过滤无意义的规格项
"""
import html
import json
import os
import re

RAW = "scripts/fmuser_products.json"
OUT = "src/data/products.js"
IMG_DIR = "public/images/products"


def local_image_for(slug):
    """如果 public/images/products/<slug>.<ext> 存在，返回本地路径"""
    if not os.path.isdir(IMG_DIR):
        return ""
    for f in os.listdir(IMG_DIR):
        base, ext = os.path.splitext(f)
        if base == slug and ext.lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            return f"/images/products/{f}"
    return ""

# 本地产品图映射（scripts/download_product_images.py 生成）: slug -> /images/products/xx
try:
    with open("scripts/product_images.json", encoding="utf-8") as f:
        IMG_MAP = json.load(f)
except FileNotFoundError:
    IMG_MAP = {}

with open(RAW, encoding="utf-8") as f:
    raw = json.load(f)

# 分类映射（基于名称关键词）
def classify(name):
    n = name.lower()
    if "gateway" in n or "headend" in n:
        return "headend"
    if "set-top" in n or "stb" in n or "magic box" in n:
        return "hardware"
    if "hotel" in n:
        return "hotel"
    if "hospital" in n or "health" in n:
        return "hospital"
    if "education" in n or "school" in n or "campus" in n:
        return "education"
    if "train" in n or "railway" in n:
        return "transport"
    if "maritime" in n or "ship" in n or "vessel" in n:
        return "maritime"
    if "government" in n:
        return "government"
    if "fitness" in n or "gym" in n or "yoga" in n:
        return "fitness"
    if "enterprise" in n or "corporate" in n:
        return "enterprise"
    if "prison" in n or "correctional" in n:
        return "prison"
    if "isp" in n or "residential" in n:
        return "isp"
    return "solution"

# 无意义/重复的规格 key
SKIP_KEYS = {
    "items", "specifications", "feature", "features", "description",
    "product description", "overview", "highlights", "what's in the box",
    "whats in the box", "package includes", "included",
}
SKIP_PREFIX = ("iptv for", "related", "see also", "you may", "recommended")

# 截断值
MAX_VAL = 150

products = []
for p in raw:
    if "error" in p:
        continue
    raw_name = p.get("name", "").strip()
    # 清理名称：去掉 "FMUSER " 前缀和 " | FMUSER IPTV Solution" 后缀（不做 html.unescape，保证 slug 与下载脚本一致）
    clean_name = re.sub(r"^\s*FMUSER\s+", "", raw_name)
    clean_name = re.sub(r"\s*\|.*$", "", clean_name)
    clean_name = re.sub(r"[:：].*$", "", clean_name).strip()

    # slug（与 fetch_product_images.py 完全一致：&amp; 等非字母数字字符直接变 -）
    slug = re.sub(r"[^a-z0-9]+", "-", clean_name.lower()).strip("-")
    if not slug:
        slug = re.sub(r"[^a-z0-9]+", "-", raw_name.lower()).strip("-")[:50]

    desc = html.unescape(p.get("description", "")).strip()

    # 过滤规格
    specs = {}
    for k, v in p.get("specs", {}).items():
        kk = html.unescape(k).strip().rstrip(":")
        vv = html.unescape(v).strip()
        kl = kk.lower()
        if kl in SKIP_KEYS:
            continue
        if any(kl.startswith(s) for s in SKIP_PREFIX):
            continue
        if len(kk) > 50 or len(vv) > MAX_VAL:
            vv = vv[:MAX_VAL] + "…" if len(vv) > MAX_VAL else vv
        if kk and vv:
            specs[kk] = vv

    products.append({
        "name": clean_name,
        "slug": slug,
        "category": classify(clean_name),
        "description": desc[:300],
        "image": local_image_for(slug) or p.get("image", ""),
        "source_url": p.get("url", ""),
        "specs": specs,
    })

# 按分类排序
order = {"headend": 0, "hardware": 1, "hotel": 2, "solution": 3, "hospital": 4,
         "education": 5, "transport": 6, "maritime": 7, "government": 8,
         "fitness": 9, "enterprise": 10, "prison": 11, "isp": 12}
products.sort(key=lambda x: order.get(x["category"], 99))

# 生成 JS 模块
lines = [
    "// 产品数据 — 来源：FMUSER (www.fmradiobroadcast.com)",
    "// 自动生成，勿手改。重新生成：python3 scripts/scrape_fmuser.py && python3 scripts/build_products_data.py",
    "export const PRODUCTS = " + json.dumps(products, ensure_ascii=False, indent=2) + ";",
    "",
]
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"生成 {len(products)} 个产品 → {OUT}")
for p in products:
    print(f"  [{p['category']:10s}] {p['name'][:55]:55s} ({len(p['specs'])} specs)")
