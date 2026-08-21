#!/usr/bin/env python3
"""Generate favicon.ico for IPTVStream (32x32, blue gradient + white play triangle).
Pure stdlib: writes ICO container with a 32bpp DIB (BITMAPINFOHEADER + XOR + AND mask)."""
import struct

W = H = 32

def in_triangle(px, py, x1, y1, x2, y2, x3, y3):
    def sign(a, b, c):
        return (a[0] - c[0]) * (b[1] - c[1]) - (b[0] - c[0]) * (a[1] - c[1])
    p = (px, py)
    d1 = sign(p, (x1, y1), (x2, y2))
    d2 = sign(p, (x2, y2), (x3, y3))
    d3 = sign(p, (x3, y3), (x1, y1))
    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (has_neg and has_pos)

def pixel(x, y):
    # white play triangle (screen area)
    if in_triangle(x, y, 7, 6, 25, 16, 7, 26):
        return (255, 255, 255, 255)
    # antenna line
    if (3 <= y <= 5) and (15 <= x <= 17):
        return (30, 64, 175, 255)
    if y == 3 and 11 <= x <= 21:
        return (30, 64, 175, 255)
    # base stand
    if 27 <= y <= 28 and 11 <= x <= 21:
        return (37, 99, 235, 255)
    if y == 29 and 13 <= x <= 19:
        return (30, 64, 175, 255)
    # blue gradient background
    t = x / (W - 1)
    r = int(37 + 30 * t)
    g = int(99 + 40 * t)
    b = int(235 - 30 * (y / (H - 1)))
    return (b, g, r, 255)

# XOR data: rows bottom-up, each pixel BGRA
xor = bytearray()
for y in range(H - 1, -1, -1):
    for x in range(W):
        b, g, r, a = pixel(x, y)
        xor += bytes([b, g, r, a])

# AND mask: fully opaque -> all zeros
and_mask = b"\x00" * ((W // 8) * H)

dib = (
    struct.pack("<IiiHHIIiiII", 40, W, H * 2, 1, 32, 0, len(xor) + len(and_mask), 0, 0, 0, 0)
    + bytes(xor)
    + and_mask
)

icondir = struct.pack("<HHH", 0, 1, 1)
entry = struct.pack("<BBBBHHII", W, H, 0, 0, 1, 32, len(dib), 6 + 16)
ico = icondir + entry + dib

with open("favicon.ico", "wb") as f:
    f.write(ico)

print(f"favicon.ico written: {len(ico)} bytes")
