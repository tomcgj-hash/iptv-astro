#!/usr/bin/env python3
"""SEO + 断链全站扫描器：对 dist/ 下所有 HTML 做全面检查。
输出: scripts/seo_report.md
"""
import html as html_lib
import json
import os
import re
from collections import defaultdict

DIST = "dist"
OUT = "scripts/seo_report.md"

pages = []
for root, dirs, files in os.walk(DIST):
    for f in files:
        if f.endswith(".html"):
            pages.append(os.path.join(root, f))

print(f"扫描 {len(pages)} 个 HTML 页面...\n")

# 收集所有真实存在的本地资源（用于断链判断）
real_files = set()
for root, dirs, files in os.walk(DIST):
    for f in files:
        full = os.path.join(root, f)
        rel = "/" + os.path.relpath(full, DIST).replace(os.sep, "/")
        real_files.add(rel)

issues = []
page_stats = []

for page in pages:
    rel = "/" + os.path.relpath(page, DIST).replace(os.sep, "/")
    rel = re.sub(r"/index\.html$", "/", rel)
    if rel == "/":
        rel = "/"

    with open(page, encoding="utf-8", errors="ignore") as fh:
        content = fh.read()

    stats = {"page": rel}

    # ---------- 1. Title ----------
    m = re.search(r"<title>(.*?)</title>", content, re.S)
    title = m.group(1).strip() if m else ""
    stats["title"] = title
    if not title:
        issues.append((rel, "SEO", "CRITICAL", "缺少 <title> 标签"))
    elif len(title) > 70:
        issues.append((rel, "SEO", "WARN", f"title 过长 ({len(title)} 字符 > 70): {title[:60]}..."))
    elif len(title) < 15:
        issues.append((rel, "SEO", "WARN", f"title 过短 ({len(title)} 字符 < 15): {title}"))

    # ---------- 2. meta description ----------
    m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', content)
    desc = m.group(1).strip() if m else ""
    stats["desc"] = desc
    if not desc:
        issues.append((rel, "SEO", "CRITICAL", "缺少 meta description"))
    elif len(desc) < 50:
        issues.append((rel, "SEO", "WARN", f"description 过短 ({len(desc)} 字符): {desc[:50]}"))
    elif len(desc) > 165:
        issues.append((rel, "SEO", "WARN", f"description 过长 ({len(desc)} 字符)"))

    # ---------- 3. canonical ----------
    m = re.search(r'<link[^>]*rel="canonical"[^>]*href="([^"]*)"', content)
    canonical = m.group(1) if m else ""
    stats["canonical"] = canonical
    if not canonical:
        issues.append((rel, "SEO", "HIGH", "缺少 canonical 链接"))
    elif "iptv-demo.example.com" in canonical:
        issues.append((rel, "SEO", "HIGH", f"canonical 使用占位域名: {canonical}"))

    # ---------- 4. JSON-LD schema ----------
    schemas = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', content, re.S)
    stats["schemas"] = len(schemas)
    if not schemas:
        issues.append((rel, "SEO", "HIGH", "缺少 JSON-LD 结构化数据"))
    else:
        for s in schemas:
            try:
                data = json.loads(s.strip())
            except Exception:
                issues.append((rel, "SEO", "CRITICAL", "JSON-LD 解析失败（非法 JSON）"))
                continue
            # 检查 schema 中的占位域名
            if "iptv-demo.example.com" in s:
                issues.append((rel, "SEO", "HIGH", "JSON-LD 含占位域名 iptv-demo.example.com"))

    # ---------- 5. H1 ----------
    h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", content, re.S)
    stats["h1_count"] = len(h1s)
    if len(h1s) == 0:
        issues.append((rel, "SEO", "HIGH", "缺少 H1 标签"))
    elif len(h1s) > 1:
        issues.append((rel, "SEO", "WARN", f"多个 H1 标签 ({len(h1s)} 个)"))

    # ---------- 6. img alt ----------
    imgs = re.findall(r"<img[^>]*>", content)
    no_alt = 0
    for img in imgs:
        if 'alt="' not in img and "alt='" not in img:
            no_alt += 1
    stats["imgs"] = len(imgs)
    stats["no_alt"] = no_alt
    if no_alt:
        issues.append((rel, "SEO", "WARN", f"{no_alt}/{len(imgs)} 张图片缺少 alt 属性"))

    # ---------- 7. lang ----------
    if not re.search(r'<html[^>]*lang="[^"]*"', content):
        issues.append((rel, "SEO", "HIGH", "html 缺少 lang 属性"))

    # ---------- 8. Open Graph ----------
    og = re.findall(r'<meta\s+property="og:([^"]*)"', content)
    stats["og"] = len(og)
    if "title" not in og or "description" not in og or "type" not in og:
        issues.append((rel, "SEO", "WARN", f"Open Graph 不完整 (有: {og})"))

    # ---------- 9. 内部链接断链 ----------
    links = re.findall(r'href="([^"#]*?)(?:#.*)?"', content)
    local_links = set()
    for l in links:
        if not l or l.startswith(("http", "mailto:", "tel:", "//", "javascript:")):
            continue
        if l.startswith("/"):
            local_links.add(l)
        else:
            # 相对链接转绝对
            local_links.add(os.path.normpath(os.path.join(os.path.dirname(rel), l)).replace(os.sep, "/"))

    broken = []
    for l in sorted(local_links):
        # 去掉查询参数
        path = l.split("?")[0]
        if not path:
            continue
        # 目录形式 → index.html
        candidates = []
        if path.endswith("/"):
            candidates.append(path + "index.html")
            candidates.append(path.rstrip("/") + "/index.html")
        else:
            candidates.append(path)
            if not path.endswith(".html"):
                candidates.append(path + "/index.html")
        if not any(c in real_files for c in candidates):
            broken.append(l)

    stats["links"] = len(local_links)
    stats["broken"] = broken
    if broken:
        issues.append((rel, "LINK", "CRITICAL", f"{len(broken)} 个断链: {broken[:5]}..."))

    # ---------- 10. 锚点检查 ----------
    anchors = re.findall(r'href="[^"]*#([^"]+)"', content)
    # 忽略纯 JS 锚点
    real_anchors = [a for a in anchors if a not in ("", "top", "menu")]
    page_ids = set(re.findall(r'id="([^"]+)"', content))
    bad_anchor = [a for a in real_anchors if a not in page_ids]
    stats["anchors"] = len(real_anchors)
    stats["bad_anchors"] = bad_anchor
    if bad_anchor:
        issues.append((rel, "LINK", "WARN", f"无效锚点: {bad_anchor[:5]}"))

    page_stats.append(stats)

# ---------- 汇总 ----------
sev_count = defaultdict(int)
by_type = defaultdict(int)
for _, cat, sev, msg in issues:
    sev_count[sev] += 1
    by_type[cat] += 1

print(f"=== 检查完成 ===")
print(f"页面: {len(pages)}")
print(f"问题: {len(issues)}")
for sev in ("CRITICAL", "HIGH", "WARN"):
    print(f"  {sev}: {sev_count[sev]}")
print(f"按类型: {dict(by_type)}")

# ---------- 写报告 ----------
with open(OUT, "w", encoding="utf-8") as f:
    f.write("# SEO & 断链检查报告\n\n")
    f.write(f"- 检查时间: 2026-08-04\n")
    f.write(f"- 页面数: {len(pages)}\n")
    f.write(f"- 问题总数: {len(issues)}\n\n")
    f.write("## 问题汇总\n\n")
    f.write("| 严重度 | 数量 |\n|---|---|\n")
    for sev in ("CRITICAL", "HIGH", "WARN"):
        f.write(f"| {sev} | {sev_count[sev]} |\n")
    f.write("\n## 详细问题\n\n")
    for rel, cat, sev, msg in sorted(issues, key=lambda x: ({"CRITICAL": 0, "HIGH": 1, "WARN": 2}[x[2]], x[0])):
        f.write(f"### [{sev}] ({cat}) {rel}\n\n{msg}\n\n")

print(f"报告已写入 {OUT}")
