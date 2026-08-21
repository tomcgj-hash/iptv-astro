#!/usr/bin/env python3
"""筛选 FMUSER 核心广播设备产品，分配分类，生成抓取清单。
排除：定制家具、音频设备（调音台/麦克风）、'More' 占位、文章类。
输出: scripts/fmuser_core_products.json
"""
import json
import re

SRC = "scripts/fmuser_all_products.json"
OUT = "scripts/fmuser_core_products.json"

with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

# 排除关键词（非核心或噪音）
EXCLUDE = [
    "more", "podcast starter kit",
    # 定制家具
    "custom ", "desk", "console table", "counter", "furniture", "chair",
    "table for", "table ", "workstation", "cabinet", "rack mount shelf",
    # 音频消费设备
    "microphone", "headphone", "speaker", "audio processor", "mixer",
    "røde", "rodecaster", "aev ",
    # 文章/指南
    "guide to", "authoritative", "ultimate guide", "why does",
]
# 但保留部分含 console/table 的广播产品（如 control room console 是家具，但 studio console 是调音台——都排除）
# 保留关键词更准确：先用排除过滤，再人工检查

def is_core(title):
    t = title.lower().strip()
    if len(t) < 6:
        return False
    for kw in EXCLUDE:
        if kw in t:
            return False
    # 必须有广播/射频/IP相关特征词
    CORE_KW = [
        "transmitter", "transmission", "antenna", "filter", "combiner",
        "coupler", "divider", "dummy load", "attenuator", "iptv", "encoder",
        "decoder", "modulator", "demodulator", "transcoder", "multiplexer",
        "stb", "set-top", "gateway", "streaming", "mux", "stl", "rigid",
        "feeder", "coax", "cable", "connector", "adapter", "adptor",
        "fiber", "optical", "patch cord", "amplifier", "transistor",
        "power meter", "sfn", "lightning", "surge", "tower", "mast",
        "radio", "broadcast", "studio", "satellite", "dvb", "atsc", "isdb",
        "qam", "asi", "sdi", "hdmi", "rtsp", "rtmp", "udp", "ip ",
        "channel", "tv ", "digital", "analog", "antenna tuning", "atu",
        "receiver", "transceiver", "terminal", "modem", "converter",
        "switch", "server", "headend", "cam", "biss", "gps", "clock",
        "emergency", "epg", "vod", "ott", "software", "system", "package",
        "kit", "solution", "wavetrap", "impedance", "jumper", "bullet",
        "sleeve", "support", "elbow", "clamp", "ground", "earthing",
    ]
    return any(k in t for k in CORE_KW)

core = [p for p in data if is_core(p["title"])]

# 分配分类
def classify(title):
    t = title.lower()
    if "dummy load" in t or "attenuator" in t:
        return "rf-load"  # RF假负载
    if "transmitter" in t:
        if "am " in t or t.startswith("am ") or "am transmitter" in t:
            return "am-transmitters"
        if "tv" in t and ("transmitter" in t):
            return "tv-transmitters"
        return "fm-transmitters"
    if "antenna" in t or "atu" in t or "antenna tuning" in t:
        return "antennas"
    if "filter" in t:
        return "filters"
    if "combiner" in t:
        return "combiners"
    if "coupler" in t or "divider" in t:
        return "couplers"
    if any(k in t for k in ["iptv", "encoder", "decoder", "modulator", "demodulator",
                             "transcoder", "multiplexer", "mux", "stb", "set-top",
                             "gateway", "streaming", "headend", "vod", "ott", "epg"]):
        return "iptv"
    if "fiber" in t or "optical" in t or "patch cord" in t:
        return "fiber"
    if any(k in t for k in ["rigid", "feeder", "coax", "cable", "connector",
                             "adapter", "adptor", "bullet", "sleeve", "elbow",
                             "jumper", "clamp"]):
        return "rf-cables"
    if "amplifier" in t or "transistor" in t or "pallet" in t:
        return "amplifiers"
    if "stl" in t or "link" in t:
        return "stl"
    if "tower" in t or "mast" in t:
        return "towers"
    if "lightning" in t or "surge" in t or "earthing" in t:
        return "accessories"
    if "satellite" in t or "dvb" in t or "modem" in t:
        return "satellite"
    if "power meter" in t:
        return "test-equipment"
    if "sfn" in t:
        return "solutions"
    if "studio" in t or "console" in t or "broadcast" in t or "radio" in t:
        return "studio"
    if "package" in t or "kit" in t or "solution" in t or "system" in t:
        return "solutions"
    return "other"

for p in core:
    p["category"] = classify(p["title"])

# 分类统计
from collections import Counter
cnt = Counter(p["category"] for p in core)
print(f"核心产品: {len(core)} 个")
for k, v in cnt.most_common():
    print(f"  {k}: {v}")

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(core, f, ensure_ascii=False, indent=2)
print(f"\n已保存 {OUT}")
