#!/usr/bin/env python3
"""从 coaxtoiptv_products.json 生成网站产品数据 src/data/products.js
- 新分类：encoder/modulator/encoder-modulator/ird-decoder/multiplexer/ip-gateway/software/transmitter/headend-processor/pcie-card/other
"""
import html
import json
import os
import re

RAW = "scripts/coaxtoiptv_products.json"
OUT = "src/data/products.js"

# coaxtoiptv 分类展示名
CAT_NAMES = {
    "encoder": "Encoder",
    "modulator": "Modulator / Modem",
    "encoder-modulator": "Encoder Modulator",
    "ird-decoder": "IRD / Decoder / Transcoder",
    "multiplexer": "Multiplexer / Scrambler",
    "ip-gateway": "IP Gateway",
    "software": "Software & Systems",
    "transmitter": "Transmitter / Receiver",
    "headend-processor": "Headend Processor",
    "pcie-card": "PCIe Cards",
    "other": "Other Devices",
}

# 分类排序
CAT_ORDER = ["encoder", "modulator", "encoder-modulator", "ip-gateway", "ird-decoder",
             "multiplexer", "transmitter", "headend-processor", "pcie-card", "software", "other"]

SKIP_KEYS = {"items", "specifications", "feature", "features", "description",
             "product description", "overview", "highlights", "what's in the box",
             "whats in the box", "package includes", "included", "more", "parameter", "parameters"}
SKIP_PREFIX = ("related", "see also", "you may", "recommended", "download")


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:80]


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
    if len(desc) > 160:
        desc = desc[:160]
        cut = max(desc.rfind("."), desc.rfind("|"), desc.rfind("—"))
        if cut > 80:
            desc = desc[: cut + 1]
    desc = desc[:160]

    # 自动生成描述（为空时）
    if not desc:
        cat_kw = CAT_NAMES.get(p.get("category", ""), "broadcast equipment")
        desc = f"Buy {name} — a professional {cat_kw} from COAX to IPTV. In stock, worldwide shipping, OEM/ODM supported. Get a quote today."[:160]

    specs = {}
    for k, v in p.get("specs", {}).items():
        kk = html.unescape(k).strip().rstrip(":")
        vv = html.unescape(v).strip()
        kl = kk.lower()
        if kl in SKIP_KEYS or any(kl.startswith(s) for s in SKIP_PREFIX):
            continue
        if kk and vv:
            specs[kk] = vv[:200]

    products.append({
        "name": name,
        "slug": slug,
        "category": p.get("category", "other"),
        "description": desc,
        "image": p.get("image", ""),
        "gallery": p.get("gallery", []),
        "source_url": p.get("url", ""),
        "specs": specs,
    })

# 去重 + 过滤无图产品（用户要求：没有图片的产品不展示）
seen = set()
unique = []
for p in products:
    if p["slug"] not in seen and p.get("image"):
        seen.add(p["slug"])
        unique.append(p)

unique.sort(key=lambda x: (CAT_ORDER.index(x["category"]) if x["category"] in CAT_ORDER else 99, x["name"].lower()))

with open(OUT, "w", encoding="utf-8") as f:
    f.write("// 产品数据 — 来源：COAX to IPTV (www.coaxtoiptv.com)\n")
    f.write("// 自动生成，勿手改。\n")
    f.write("export const CAT_NAMES = " + json.dumps(CAT_NAMES, ensure_ascii=False, indent=2) + ";\n\n")
    f.write("export const PRODUCTS = " + json.dumps(unique, ensure_ascii=False, indent=2) + ";\n")

from collections import Counter
cnt = Counter(p["category"] for p in unique)
print(f"生成 {len(unique)} 个产品 → {OUT}")
for k, v in cnt.most_common():
    print(f"  {CAT_NAMES.get(k, k)}: {v}")
imgs = sum(1 for p in unique if p.get("image"))
gal = sum(len(p.get("gallery", [])) for p in unique)
print(f"\n有主图: {imgs}/{len(unique)}, 画廊图总数: {gal}")
