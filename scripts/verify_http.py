#!/usr/bin/env python3
"""最终验证：抽检页面和图片 HTTP 状态"""
import os
import random
import socket

def http_get(path):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect(("127.0.0.1", 4321))
        req = f"GET {path} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        s.sendall(req.encode())
        resp = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            resp += chunk
        return resp.split(b"\r\n")[0].decode()
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        s.close()

# 收集所有页面
pages = []
for root, dirs, files in os.walk("dist"):
    for f in files:
        if f.endswith(".html"):
            full = os.path.join(root, f)
            rel = "/" + os.path.relpath(full, "dist").replace(os.sep, "/")
            if rel.endswith("index.html"):
                rel = rel[:-10]
                if rel != "/":
                    rel += "/"
            pages.append(rel)

random.seed(42)
sample = ["/"] + random.sample(pages, 60)

bad = []
for p in sample:
    status = http_get(p)
    if "200" not in status:
        bad.append((p, status))

print(f"抽检 {len(sample)} 个页面")
if bad:
    print(f"失败 {len(bad)} 个:")
    for p, s in bad:
        print(f"  {p}: {s}")
else:
    print("全部 200 OK")

# 图片抽检
imgs = []
for root, dirs, files in os.walk("public/images/products"):
    for f in files:
        imgs.append("/images/products/" + f)
sample_imgs = random.sample(imgs, min(20, len(imgs)))
img_bad = []
for p in sample_imgs:
    status = http_get(p)
    if "200" not in status:
        img_bad.append((p, status))
print(f"\n图片抽检 {len(sample_imgs)} 张")
if img_bad:
    for p, s in img_bad:
        print(f"  {p}: {s}")
else:
    print("全部 200 OK")
