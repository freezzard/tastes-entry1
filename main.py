#!/usr/bin/env python3
"""One strawberry, procedural PNG. Stdlib only.

Draws a single perfect strawberry (hero shot) on a dark soft
background and writes /output/entry.png (1024x1024 PNG).
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024
OUT = "/output/entry.png"

CX = 512
TOP = 212
BOT = 908
MAXHW = 332


def clamp01(v):
    r = v
    r = 0.0 if r < 0.0 else r
    r = 1.0 if r > 1.0 else r
    return r


def sstep(a, b, x):
    u = (x - a) / (b - a)
    u = clamp01(u)
    return u * u * (3.0 - 2.0 * u)


def lerp(a, b, f):
    return a + (b - a) * f


def body_halfw(t):
    base = (1.0 - t ** 2.5) ** 0.62
    top = 0.22 + 0.78 * sstep(0.0, 0.28, t)
    hw = MAXHW * base * top
    hw = 1.5 if hw < 1.5 else hw
    return hw


def body_color_vertical(t):
    r0, g0, b0 = 238.0, 42.0, 44.0
    r1, g1, b1 = 214.0, 20.0, 28.0
    r2, g2, b2 = 122.0, 10.0, 18.0
    f = t / 0.45
    f = clamp01(f)
    r = lerp(r0, r1, f)
    g = lerp(g0, g1, f)
    b = lerp(b0, b1, f)
    f2 = (t - 0.45) / 0.55
    f2 = clamp01(f2)
    r = lerp(r, r2, f2)
    g = lerp(g, g2, f2)
    b = lerp(b, b2, f2)
    return r, g, b


def noise2(x, y):
    n = (x * 374761393 + y * 668265263) ^ (x * y * 974634 + 1442695041)
    n = n & 0x7FFFFFFF
    return (n % 7) - 3


def blend(buf, x, y, r, g, b, a):
    inside = 0 <= x < W and 0 <= y < H
    done = False
    if inside:
        idx = (y * W + x) * 3
        buf[idx] = int(buf[idx] * (1.0 - a) + r * a)
        buf[idx + 1] = int(buf[idx + 1] * (1.0 - a) + g * a)
        buf[idx + 2] = int(buf[idx + 2] * (1.0 - a) + b * a)
        done = True
    return done


def render():
    buf = bytearray(W * H * 3)
    for y in range(H):
        row = y * W * 3
        dy_bg = y - 470
        in_body = TOP <= y <= BOT
        t = 0.0
        hw = 0.0
        x0 = 0
        x1 = 0
        vr = vg = vb = 0.0
        if in_body:
            t = (y - TOP) / (BOT - TOP)
            hw = body_halfw(t)
            x0 = int(CX - hw)
            x1 = int(CX + hw)
            vr, vg, vb = body_color_vertical(t)
        for x in range(W):
            dx_bg = x - 512
            d2 = dx_bg * dx_bg + dy_bg * dy_bg
            # dark background, radial falloff + warm glow behind berry
            fall = clamp01(d2 / 524176.0)
            br = lerp(30.0, 10.0, fall)
            bg = lerp(18.0, 7.0, fall)
            bb = lerp(20.0, 8.0, fall)
            glow = 1.0 - clamp01(d2 / 250000.0)
            br = br + 26.0 * glow
            bg = bg + 8.0 * glow
            bb = bb + 6.0 * glow
            # soft ground shadow ellipse under the berry
            ex = (x - 512) / 290.0
            ey = (y - 945) / 34.0
            se = ex * ex + ey * ey
            sh = 0.0
            if se < 1.0:
                sh = (1.0 - se) * 0.55
            br = br * (1.0 - sh)
            bg = bg * (1.0 - sh)
            bb = bb * (1.0 - sh)
            r = br
            g = bg
            b = bb
            if in_body and x0 <= x <= x1:
                dx = x - CX
                nx = dx / hw
                anx = abs(nx)
                shade = 1.0 - 0.28 * anx * anx * anx
                r = vr * shade
                g = vg * shade
                b = vb * shade
                # warm radial highlight, upper left
                hdx = x - 395
                hdy = y - 335
                hd2 = hdx * hdx + hdy * hdy
                hl = 1.0 - clamp01(hd2 / 160000.0)
                hl = hl * hl
                r = r + 78.0 * hl
                g = g + 40.0 * hl
                b = b + 32.0 * hl
                # warm rim light on the right edge
                rim = 0.0
                if dx > 0:
                    rim = clamp01((dx - (hw - 30.0)) / 30.0)
                r = r + 26.0 * rim
                g = g + 6.0 * rim
                b = b + 2.0 * rim
                # faint dimpled bands between seed rows + streaks + grain
                band = math.sin(y * 0.136) * 2.0
                st = math.sin(x * 0.045 + y * 0.011) * 4.0
                nz = noise2(x, y)
                r = r + st + band + nz
                g = g + st * 0.6 + band + nz
                b = b + st * 0.5 + band + nz
            r = 0.0 if r < 0.0 else r
            r = 255.0 if r > 255.0 else r
            g = 0.0 if g < 0.0 else g
            g = 255.0 if g > 255.0 else g
            b = 0.0 if b < 0.0 else b
            b = 255.0 if b > 255.0 else b
            buf[row + x * 3] = int(r)
            buf[row + x * 3 + 1] = int(g)
            buf[row + x * 3 + 2] = int(b)
    return buf


def sheen(buf, cx, cy, rx, ry, alpha):
    for y in range(cy - ry, cy + ry + 1):
        for x in range(cx - rx, cx + rx + 1):
            e = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            hit = e < 1.0
            a = 0.0
            if hit:
                a = (1.0 - e) * alpha
            if a > 0.0:
                blend(buf, x, y, 255.0, 235.0, 225.0, a)


def draw_specular(buf):
    sheen(buf, 430, 330, 150, 92, 0.30)
    sheen(buf, 622, 520, 62, 42, 0.18)


def achenes():
    pts = []
    row = 0
    y = 300
    while y <= 852:
        t = (y - TOP) / (BOT - TOP)
        hw = body_halfw(t)
        off = 27 if row % 2 == 1 else 0
        x = CX - 320 + off
        while x <= CX + 320:
            inside = abs(x - CX) < hw - 34
            if inside:
                pts.append((x, y))
            x = x + 54
        row = row + 1
        y = y + 46
    return pts


def draw_achenes(buf):
    for ax, ay in achenes():
        for yy in range(ay - 11, ay + 12):
            for xx in range(ax - 8, ax + 9):
                dx = xx - ax
                dy = yy - ay
                e = (dx / 6.5) ** 2 + (dy / 9.5) ** 2
                hit = e <= 1.0
                if hit:
                    rim = e > 0.72
                    cr, cg, cb = 244.0, 222.0, 152.0
                    if rim:
                        cr, cg, cb = 178.0, 134.0, 54.0
                    he = ((dx + 2) / 2.2) ** 2 + ((dy + 3) / 3.0) ** 2
                    hi = he <= 1.0
                    if hi:
                        cr, cg, cb = 255.0, 252.0, 230.0
                    blend(buf, xx, yy, cr, cg, cb, 0.95)


def draw_leaf(buf, cx, cy, ang_deg, length, width):
    ang = math.radians(ang_deg)
    ca = math.cos(ang)
    sa = math.sin(ang)
    span = int(length) + 8
    for yy in range(cy - span, cy + span + 1):
        for xx in range(cx - span, cx + span + 1):
            dx = xx - cx
            dy = yy - cy
            u = dx * ca + dy * sa
            v = -dx * sa + dy * ca
            e = (u / length) ** 2 + (v / width) ** 2
            shape = e <= 1.0 and -0.18 * length <= u <= length
            if shape:
                along = clamp01(u / length)
                cr = lerp(58.0, 30.0, along)
                cg = lerp(138.0, 84.0, along)
                cb = lerp(52.0, 30.0, along)
                vein = abs(v) < 2.2 and u > 0.0
                if vein:
                    cr, cg, cb = 22.0, 74.0, 24.0
                top = v < -width * 0.45
                if top:
                    cr = cr + 16.0
                    cg = cg + 26.0
                    cb = cb + 8.0
                blend(buf, xx, yy, cr, cg, cb, 0.96)


def draw_calyx(buf):
    draw_leaf(buf, 512, 240, -168.0, 168.0, 26.0)
    draw_leaf(buf, 512, 240, -138.0, 185.0, 28.0)
    draw_leaf(buf, 512, 240, -108.0, 172.0, 27.0)
    draw_leaf(buf, 512, 240, -72.0, 172.0, 27.0)
    draw_leaf(buf, 512, 240, -42.0, 185.0, 28.0)
    draw_leaf(buf, 512, 240, -12.0, 168.0, 26.0)
    # green cap covering the berry top joint
    for yy in range(212, 268):
        for xx in range(422, 603):
            e = ((xx - 512) / 90.0) ** 2 + ((yy - 242) / 30.0) ** 2
            if e <= 1.0:
                blend(buf, xx, yy, 30.0, 92.0, 32.0, 0.95)


def draw_stem(buf):
    p0 = (512.0, 240.0)
    p1 = (500.0, 175.0)
    p2 = (530.0, 112.0)
    i = 0
    while i <= 36:
        f = i / 36.0
        bx = (1 - f) * (1 - f) * p0[0] + 2 * (1 - f) * f * p1[0] + f * f * p2[0]
        by = (1 - f) * (1 - f) * p0[1] + 2 * (1 - f) * f * p1[1] + f * f * p2[1]
        rad = lerp(9.0, 4.5, f)
        rr = int(rad) + 1
        for yy in range(int(by) - rr, int(by) + rr + 1):
            for xx in range(int(bx) - rr, int(bx) + rr + 1):
                d2 = (xx - bx) ** 2 + (yy - by) ** 2
                if d2 <= rad * rad:
                    blend(buf, xx, yy, 104.0, 82.0, 44.0, 0.97)
                    lite = xx < bx - 1.0
                    if lite:
                        blend(buf, xx, yy, 158.0, 128.0, 74.0, 0.35)
        i = i + 1


def draw_droplet(buf, dx0, dy0, r):
    rr = int(r) + 2
    for yy in range(dy0 - rr, dy0 + rr + 1):
        for xx in range(dx0 - rr, dx0 + rr + 1):
            d2 = (xx - dx0) ** 2 + (yy - dy0) ** 2
            if d2 <= r * r:
                fall = 1.0 - d2 / (r * r)
                a = 0.28 + 0.42 * fall
                blend(buf, xx, yy, 214.0, 228.0, 240.0, a)
                sx = xx - (dx0 - 0.35 * r)
                sy = yy - (dy0 - 0.38 * r)
                sd = sx * sx + sy * sy
                if sd <= (0.32 * r) ** 2:
                    blend(buf, xx, yy, 255.0, 255.0, 255.0, 0.92)


def draw_droplets(buf):
    drops = [
        (430, 420, 11.0), (600, 500, 9.0), (480, 640, 13.0),
        (640, 700, 8.0), (380, 560, 7.0), (560, 330, 8.0),
        (700, 600, 10.0), (450, 780, 9.0), (330, 450, 6.0),
        (660, 420, 7.0), (520, 540, 6.0), (590, 820, 8.0),
        (430, 205, 7.0), (600, 200, 6.0),
    ]
    for dx0, dy0, r in drops:
        draw_droplet(buf, dx0, dy0, r)


def draw_sparkles(buf):
    pts = [(372, 372, 2), (618, 452, 2), (470, 700, 1), (688, 548, 2)]
    for sx, sy, sr in pts:
        for yy in range(sy - sr, sy + sr + 1):
            for xx in range(sx - sr, sx + sr + 1):
                blend(buf, xx, yy, 255.0, 255.0, 255.0, 0.85)


def chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out = out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def encode_png(buf):
    raw = bytearray()
    prev = bytes(W * 3)
    for y in range(H):
        row = buf[y * W * 3:(y + 1) * W * 3]
        filt = 0 if y == 0 else 2
        raw.append(filt)
        if filt == 0:
            raw.extend(row)
        if filt == 2:
            for i in range(W * 3):
                raw.append((row[i] - prev[i]) & 0xFF)
        prev = bytes(row)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png = png + chunk(b"IHDR", ihdr)
    png = png + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png = png + chunk(b"IEND", b"")
    return png


def main():
    buf = render()
    draw_specular(buf)
    draw_achenes(buf)
    draw_calyx(buf)
    draw_stem(buf)
    draw_droplets(buf)
    draw_sparkles(buf)
    png = encode_png(buf)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    written = 0
    with open(OUT, "wb") as f:
        written = f.write(png)
    print("WROTE %s %dx%d %d bytes" % (OUT, W, H, written))
    return written


main()
