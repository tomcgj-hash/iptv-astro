#!/usr/bin/env python3
"""从 fmuser_core_details.json 生成网站产品数据 src/data/products.js
- 保留 slug/category/description/specs/image
- 分类名映射
"""
import html
import json
import os
import re

RAW = "scripts/fmuser_core_details.json"
OUT = "src/data/products.js"

# 分类展示名（英文，用于页面）
CAT_NAMES = {
    "fm-transmitters": "FM Transmitters",
    "am-transmitters": "AM Transmitters",
    "tv-transmitters": "TV Transmitters",
    "antennas": "Broadcast Antennas",
    "filters": "Cavity Filters",
    "combiners": "Combiners",
    "couplers": "Couplers & Dividers",
    "rf-load": "RF Dummy Loads",
    "iptv": "IPTV & Streaming",
    "fiber": "Fiber Optics",
    "rf-cables": "RF Cables & Connectors",
    "amplifiers": "RF Amplifiers",
    "stl": "STL Links",
    "towers": "Towers & Masts",
    "accessories": "Accessories",
    "satellite": "Satellite Equipment",
    "test-equipment": "Test Equipment",
    "solutions": "Solutions & Packages",
    "studio": "Radio Studio",
    "other": "Other Equipment",
}

# 分类排序
CAT_ORDER = ["fm-transmitters", "am-transmitters", "tv-transmitters", "antennas",
             "iptv", "filters", "combiners", "couplers", "rf-load", "amplifiers",
             "stl", "rf-cables", "fiber", "towers", "satellite", "test-equipment",
             "accessories", "studio", "solutions", "other"]

SKIP_KEYS = {"items", "specifications", "feature", "features", "description",
             "product description", "overview", "highlights", "what's in the box",
             "whats in the box", "package includes", "included", "more"}
SKIP_PREFIX = ("iptv for", "related", "see also", "you may", "recommended", "download")


def slugify(name):
    n = re.sub(r"^\s*FMUSER\s+", "", name)
    n = re.sub(r"\s*\|.*$", "", n)
    # 冒号转连字符而不是截断（产品名是 "型号: 描述" 格式）
    n = re.sub(r"[:：]", " ", n).strip()
    s = re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")
    s = s[:80]
    # 过短 slug（型号前缀型，如 ADSS/GJXFA）→ 附加名称后半部分
    if len(s) < 12:
        words = n.split()
        if len(words) > 3:
            alt = re.sub(r"[^a-z0-9]+", "-", " ".join(words[1:]).lower()).strip("-")
            if len(alt) > len(s):
                s = alt[:80]
    return s


# 分类描述模板（SEO：描述里带关键词）
CAT_DESC = {
    "fm-transmitters": "FM broadcast transmitter",
    "am-transmitters": "AM broadcast transmitter",
    "tv-transmitters": "TV broadcast transmitter",
    "antennas": "broadcast antenna",
    "filters": "RF cavity filter",
    "combiners": "RF combiner",
    "couplers": "RF coupler",
    "rf-load": "RF dummy load",
    "iptv": "IPTV streaming system",
    "fiber": "fiber optic product",
    "rf-cables": "RF cable and connector",
    "amplifiers": "RF power amplifier",
    "stl": "studio transmitter link",
    "towers": "broadcast tower",
    "accessories": "broadcast accessory",
    "satellite": "satellite equipment",
    "test-equipment": "RF test equipment",
    "solutions": "broadcast solution",
    "studio": "radio studio equipment",
    "other": "broadcast equipment",
}


def auto_description(p, name, specs):
    """为空描述的产品自动生成 SEO description"""
    cat_kw = CAT_DESC.get(p.get("category", ""), "broadcast equipment")
    d = f"Buy {name} — a professional {cat_kw} from FMUSER."
    # 附加 2-3 个关键规格
    keys = list(specs.keys())
    extra = []
    for k in keys:
        if k.lower() in ("terms", "specifications", "more", "model", "items"):
            continue
        v = specs[k]
        if len(str(v)) < 60:
            extra.append(f"{k}: {v}")
        if len(extra) >= 3:
            break
    if extra:
        d += " Key specs: " + " | ".join(extra) + "."
    d += " In stock, worldwide shipping, OEM/ODM supported. Get a quote today."
    # 截断到 155 字符（SEO 最佳长度，在句号处截断）
    if len(d) > 155:
        d = d[:155]
        cut = max(d.rfind("."), d.rfind("|"), d.rfind("—"))
        if cut > 80:
            d = d[: cut + 1]
    return d[:160]


with open(RAW, encoding="utf-8") as f:
    raw = json.load(f)

products = []
for p in raw:
    if p.get("error"):
        continue
    name = html.unescape(p.get("name", "")).strip()
    slug = slugify(name)
    if not slug:
        continue

    desc = html.unescape(p.get("description", "")).strip()
    # 统一截断到 160 字符
    if len(desc) > 160:
        desc = desc[:160]
        cut = max(desc.rfind("."), desc.rfind("|"), desc.rfind("—"))
        if cut > 80:
            desc = desc[: cut + 1]
    desc = desc[:160]

    specs = {}
    for k, v in p.get("specs", {}).items():
        kk = html.unescape(k).strip().rstrip(":")
        vv = html.unescape(v).strip()
        kl = kk.lower()
        if kl in SKIP_KEYS or any(kl.startswith(s) for s in SKIP_PREFIX):
            continue
        if kk and vv:
            specs[kk] = vv[:200]

    if not desc:
        desc = auto_description(p, name, specs)

    products.append({
        "name": name,
        "slug": slug,
        "category": p.get("category", "other"),
        "description": desc,
        "image": p.get("image", ""),
        "source_url": p.get("url", ""),
        "specs": specs,
    })

# 去重（同名产品）
seen = set()
unique = []
for p in products:
    key = p["slug"]
    if key not in seen:
        seen.add(key)
        unique.append(p)

unique.sort(key=lambda x: (CAT_ORDER.index(x["category"]) if x["category"] in CAT_ORDER else 99, x["name"].lower()))

with open(OUT, "w", encoding="utf-8") as f:
    f.write("// 产品数据 — 来源：FMUSER (www.fmradiobroadcast.com)\n")
    f.write("// 自动生成，勿手改。\n")
    f.write("export const CAT_NAMES = " + json.dumps(CAT_NAMES, ensure_ascii=False, indent=2) + ";\n\n")
    f.write("export const PRODUCTS = " + json.dumps(unique, ensure_ascii=False, indent=2) + ";\n")

from collections import Counter
cnt = Counter(p["category"] for p in unique)
print(f"生成 {len(unique)} 个产品 → {OUT}")
for k, v in cnt.most_common():
    print(f"  {CAT_NAMES.get(k, k)}: {v}")
imgs = sum(1 for p in unique if p["image"])
print(f"\n有图: {imgs}/{len(unique)}")
