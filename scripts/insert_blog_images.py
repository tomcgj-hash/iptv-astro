#!/usr/bin/env python3
"""补齐博客配图：每篇目标 2 张，已有 2 张跳过，缺的按锚点插入。"""
import re

POSTS = "/opt/data/iptv-astro/src/data/posts.js"

# 完整锚点映射（每篇 2 个锚点）
INSERT_MAP = {
    "how-to-choose-best-iptv-service-2026": {
        "## Red Flags to Avoid": "how-to-choose-best-iptv-service-2026-tv-room.jpg",
        "## Final Checklist": "how-to-choose-best-iptv-service-2026-remote-tv.jpg",
    },
    "iptv-vs-cable-vs-satellite": {
        "## Cable TV": "iptv-vs-cable-vs-satellite-cable.jpg",
        "## Which One Should You Choose?": "iptv-vs-cable-vs-satellite-satellite.jpg",
    },
    "how-to-set-up-iptv-fire-stick-smart-tv-android": {
        "## 1. Amazon Fire Stick": "how-to-set-up-iptv-fire-stick-smart-tv-android-firestick.jpg",
        "## 2. Android TV / Google TV": "how-to-set-up-iptv-fire-stick-smart-tv-android-android-tv.jpg",
    },
    "iptv-buffering-causes-and-fixes": {
        "## 1. Weak Wi-Fi Signal": "iptv-buffering-10-causes-fixes-router.jpg",
        "## 10. Device Overheating": "iptv-buffering-10-causes-fixes-wifi.jpg",
    },
    "iptv-for-hotels-complete-headend-guide": {
        "## What Is a Hotel IPTV Headend?": "iptv-for-hotels-complete-headend-guide-hotel-room.jpg",
        "## Business Benefits for Hotel Owners": "iptv-for-hotels-complete-headend-guide-headend.jpg",
    },
    "fm-transmitters-explained-50w-vs-5kw": {
        "## Understanding Power Classes": "fm-transmitters-explained-50w-vs-5kw-radio-studio.jpg",
        "## Solid-State vs Tube Transmitters": "fm-transmitters-explained-50w-vs-5kw-antenna.jpg",
    },
    "how-to-choose-broadcast-antenna-fm-vhf-uhf": {
        "## Antenna Types by Use Case": "how-to-choose-broadcast-antenna-fm-vhf-uhf-antenna-tower.jpg",
        "## Practical Checklist Before Buying": "how-to-choose-broadcast-antenna-fm-vhf-uhf-radio-mic.jpg",
    },
    "iptv-headend-equipment-encoder-gateway-stb": {
        "## 1. Encoders": "iptv-headend-equipment-encoder-gateway-stb-server-room.jpg",
        "## 3. IPTV Gateway": "iptv-headend-equipment-encoder-gateway-stb-encoder.jpg",
    },
    "hotel-iptv-systems-stb-vs-smart-tv-apps": {
        "## Set-Top Boxes (STB): The Traditional Route": "hotel-iptv-systems-stb-vs-smart-tv-apps-hotel-lobby.jpg",
        "## Smart TV Apps: The Modern Approach": "hotel-iptv-systems-stb-vs-smart-tv-apps-tv-screen.jpg",
    },
    "how-to-build-small-fm-radio-station-budget": {
        "## Step 2: The Studio": "how-to-build-small-fm-radio-station-budget-studio.jpg",
        "## Step 4: Antenna & Feeder": "how-to-build-small-fm-radio-station-budget-broadcast.jpg",
    },
}

with open(POSTS, encoding="utf-8") as f:
    js = f.read()

count = 0
for slug, inserts in INSERT_MAP.items():
    m = re.search(rf"slug: '{re.escape(slug)}'.*?content: `(.*?)`,\s*\n", js, re.S)
    if not m:
        print(f"✗ {slug}: 未找到 content")
        continue
    content = m.group(1)
    existing = re.findall(r'^!\[.*?\]\(([^)]+)\)', content, re.M)
    existing_files = {e.split('/')[-1] for e in existing}
    modified = content
    added = 0
    for anchor, imgfile in inserts.items():
        if imgfile in existing_files:
            continue  # 已有
        if anchor in modified:
            img_line = f"![{imgfile.replace('-', ' ').replace('.jpg', '')}]({imgfile})"
            modified = modified.replace(f"{anchor}", f"{img_line}\n\n{anchor}", 1)
            added += 1
            print(f"  + {slug}: {imgfile}")
        else:
            print(f"  ⚠ {slug}: 未找到锚点 '{anchor}'")
    if modified != content:
        js = js[:m.start(1)] + modified + js[m.end(1):]
        count += 1

with open(POSTS, "w", encoding="utf-8") as f:
    f.write(js)

# 最终统计
final_posts = re.findall(r"slug: '([^']+)'.*?content: `(.*?)`,\s*\n", js, re.S)
print(f"\n=== 最终配图统计 ===")
total_imgs = 0
for slug, content in final_posts:
    n = len(re.findall(r'^!\[', content, re.M))
    total_imgs += n
    if n < 2:
        print(f"  ⚠ {slug}: 只有 {n} 张")
print(f"10 篇共 {total_imgs} 张配图")
