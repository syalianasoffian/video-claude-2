"""Render the premium vertical edit.

Usage: python3 render.py <sdr_source.mp4> <out.mp4> [--guides] [--workers N] [--frames a:b]
Timings are tied to word timestamps from the transcript (see docs/edit_plan.md).
"""
import sys
import os
import math
import subprocess
import argparse
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gfx import *  # noqa
from gfx import _rr_mask

SRC_LAST_GOOD = 612          # last clean source frame before the phone's "TV-off" glitch
END_START = 20.45            # end card starts (covers the glitch)
TOTAL = 22.45
NFRAMES = int(round(TOTAL * FPS))

# ------------------------------------------------------------------ camera
BASE_KEYS = [(0.0, 1.16), (1.5, 1.04), (4.88, 1.09), (5.05, 1.05), (9.78, 1.12), (9.95, 1.04),
             (12.12, 1.11), (12.3, 1.03), (14.78, 1.10), (14.95, 1.02), (17.58, 1.10), (17.75, 1.04),
             (20.45, 1.10)]
PUNCHES = [(5.5, 0.06), (6.86, 0.045), (9.14, 0.07), (13.3, 0.06), (16.76, 0.05), (19.66, 0.04)]


def zoom_at(t):
    z = BASE_KEYS[-1][1]
    for (t0, z0), (t1, z1) in zip(BASE_KEYS, BASE_KEYS[1:]):
        if t0 <= t <= t1:
            z = z0 + (z1 - z0) * ease_in_out((t - t0) / (t1 - t0))
            break
    for tp, amp in PUNCHES:
        if t >= tp - 0.02:
            dt = t - tp
            up = ease_out_cubic(dt / 0.16) if dt < 0.16 else 1.0
            down = math.exp(-max(0, dt - 0.16) / 0.45)
            z += amp * up * down
    return z


def camera(img, t):
    z = zoom_at(t)
    ax = 560 + 14 * math.sin(t * 0.55)
    ay = 560 + 10 * math.sin(t * 0.4 + 1)
    a = 1 / z
    return img.transform((W, H), Image.AFFINE, (a, 0, ax - ax * a, 0, a, ay - ay * a), Image.BICUBIC)


# ------------------------------------------------------------------ grade
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W * 0.62)) ** 2 + ((_yy - H * 0.42) / (H * 0.62)) ** 2)
VIG = np.clip(1 - 0.42 * _r ** 2.4, 0.35, 1)[..., None].astype(np.float32)
SWEEP_U = ((_xx * 0.8 + _yy * 0.45) / (W * 0.8 + H * 0.45)).astype(np.float32)
NAVY_F = np.array(NAVY, np.float32)


def grade(arr):
    x = arr.astype(np.float32) / 255.0
    lum = (x[..., 0] * 0.299 + x[..., 1] * 0.587 + x[..., 2] * 0.114)[..., None]
    # gentle S-curve + lift
    x = x + 0.10 * (x - 0.5) * (1 - np.abs(2 * x - 1))
    x = np.clip((x - 0.015) * 1.04, 0, 1)
    # split-tone: navy shadows, warm highlights
    x = x + (1 - lum) ** 2 * np.array([-0.012, 0.004, 0.035], np.float32)
    x = x + lum ** 2 * np.array([0.022, 0.010, -0.018], np.float32)
    # saturation
    l2 = (x[..., 0] * 0.299 + x[..., 1] * 0.587 + x[..., 2] * 0.114)[..., None]
    x = l2 + (x - l2) * 1.06
    x = np.clip(x, 0, 1) * 255
    # navy vignette
    x = x * VIG + NAVY_F * (1 - VIG) * 0.9
    return np.clip(x, 0, 255)


def light_sweep(arr, p, strength=0.22, width=0.07, col=(255, 226, 160)):
    if p <= 0 or p >= 1:
        return arr
    c = -0.15 + 1.3 * ease_in_out(p)
    band = np.exp(-((SWEEP_U - c) ** 2) / (2 * width ** 2)) * strength * math.sin(math.pi * p)
    band = band[..., None]
    colv = np.array(col, np.float32)
    return arr + (colv - arr) * band


# ------------------------------------------------------------------ particles
rng = np.random.default_rng(42)
PARTS = [dict(x=rng.uniform(140, 880), y=rng.uniform(880, 1430), v=rng.uniform(12, 34), s=rng.uniform(2, 6),
              ph=rng.uniform(0, 6.28), a=rng.uniform(0.25, 0.7)) for _ in range(34)]
PARTS_END = [dict(x=rng.uniform(140, 940), y=rng.uniform(240, 1430), v=rng.uniform(10, 40), s=rng.uniform(2, 7),
                  ph=rng.uniform(0, 6.28), a=rng.uniform(0.25, 0.8)) for _ in range(60)]
_DOT = {}


def dot(s):
    s = int(round(s))
    if s not in _DOT:
        n = s * 6
        im = Image.new("L", (n, n), 0)
        d = ImageDraw.Draw(im)
        d.ellipse((n / 2 - s / 2, n / 2 - s / 2, n / 2 + s / 2, n / 2 + s / 2), fill=255)
        im = im.filter(ImageFilter.GaussianBlur(s * 0.9))
        im = im.point(lambda v: min(255, v * 3))
        _DOT[s] = colorize(im, GOLD_L)
    return _DOT[s]


def particles(fr, t, parts, y0, y1, alpha=1.0):
    span = y1 - y0
    for p in parts:
        y = y1 - ((y1 - p["y"]) + p["v"] * t) % span
        x = p["x"] + 10 * math.sin(t * 0.7 + p["ph"])
        tw = 0.55 + 0.45 * math.sin(t * 2.2 + p["ph"] * 3)
        edge = min(1, (y - y0) / 80, (y1 - y) / 80)
        paste(fr, dot(p["s"]), x, y, alpha * p["a"] * tw * max(0, edge), "mm")


# ------------------------------------------------------------------ helpers
def lq_of(t, base=-5, amp=4, speed=1.1):
    return int(round(base + amp * math.sin(t * speed)))


def obj3d(fr, img, cx, cy, theta, depth, a=1.0, scale=1.0, shadow=True, side="gold", glow_amt=0.0):
    im = extrude(img, theta, depth, side)
    if scale != 1.0:
        im = scaled(im, scale)
    if glow_amt > 0:
        g, pad = glow(im, 26, GOLD, glow_amt)
        paste(fr, g, cx - g.width / 2, cy - g.height / 2, a)
    if shadow:
        d, pad = drop_shadow(im, 16, (0, 20), 0.55)
        paste(fr, d, cx - d.width / 2, cy - d.height / 2 + 0, a)
    else:
        paste(fr, im, cx, cy, a, "mm")


def holo_ring(fr, cx, cy, w, h, a=1.0, t=0.0):
    im = Image.new("RGBA", (w + 80, h + 80 + 160), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, oy = 40, 40 + 160
    for k, al in ((0, 220), (16, 120), (32, 60)):
        d.ellipse((ox + k, oy + k * h / w, ox + w - k, oy + h - k * h / w), outline=GOLD_L + (al,), width=3)
    # light cone
    cone = Image.new("L", im.size, 0)
    cd = ImageDraw.Draw(cone)
    cd.polygon([(ox + 10, oy + h / 2), (ox + w - 10, oy + h / 2), (ox + w * 0.75, 20), (ox + w * 0.25, 20)], fill=60)
    cone = cone.filter(ImageFilter.GaussianBlur(18))
    grad = np.linspace(0, 1, im.height)[:, None] ** 1.5
    cone = Image.fromarray((np.asarray(cone, np.float32) * grad).astype(np.uint8))
    out = colorize(cone, GOLD)
    out.alpha_composite(im)
    g, pad = glow(im, 10, GOLD, 1.0)
    paste(fr, g, cx - g.width / 2, cy - (oy + h / 2) - pad, a * (0.8 + 0.2 * math.sin(t * 4)))
    paste(fr, out, cx - out.width / 2, cy - (oy + h / 2), a)


def chip(fr, text, x, y, w, h, t, t0, a=1.0, icon=None, fnt=None):
    p = prog(t, t0, 0.4)
    if p <= 0:
        return
    e = ease_out_cubic(p)
    fnt = fnt or font("Montserrat", 28, 600)
    im = pill(w, h)
    tm = white_text(text, fnt)
    tx = (w - tm.width) // 2 + (16 if icon else 0)
    im.alpha_composite(tm, (tx, (h - tm.height) // 2))
    if icon is not None:
        im.alpha_composite(icon, (22, (h - icon.height) // 2))
    paste(fr, im, x, y + (1 - e) * 22, a * min(1, p * 1.5))


def no_smoke_icon(s=40):
    im = Image.new("RGBA", (s * 3, s * 3), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    S3 = s * 3
    d.rounded_rectangle((S3 * 0.18, S3 * 0.44, S3 * 0.74, S3 * 0.56), radius=6, fill=(255, 255, 255, 255))
    d.rectangle((S3 * 0.64, S3 * 0.44, S3 * 0.74, S3 * 0.56), fill=GOLD + (255,))
    d.ellipse((6, 6, S3 - 6, S3 - 6), outline=GOLD_L + (255,), width=10)
    d.line((S3 * 0.2, S3 * 0.8, S3 * 0.8, S3 * 0.2), fill=GOLD_L + (255,), width=10)
    return im.resize((s, s), Image.LANCZOS)


def gold_check_badge(s):
    im = relief(circle_mask(s), bevel=s * 0.12, mat="gold", light=(-0.5, -0.7), sheen=0.4)
    cm = check_mask(s, s, s * 0.5, s * 0.5, s * 0.55, s * 0.13)
    im.alpha_composite(colorize(cm, NAVY))
    return im


def hline(fr, x0, y, x1, a=1.0, col=GOLD, thick=2):
    if x1 - x0 < 2:
        return
    ln = Image.new("RGBA", (int(x1 - x0), thick), col + (255,))
    # fade ends
    arr = np.asarray(ln).copy()
    n = arr.shape[1]
    ramp = np.minimum(1, np.minimum(np.arange(n) / 30, (n - np.arange(n)) / 30))
    arr[..., 3] = (arr[..., 3] * ramp[None, :]).astype(np.uint8)
    paste(fr, Image.fromarray(arr, "RGBA"), x0, y, a)


def sparkle(fr, cx, cy, size, a):
    if a <= 0:
        return
    n = int(size * 4)
    im = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(im)
    c = n / 2
    d.polygon([(c, 0), (c + size * 0.18, c), (c, n), (c - size * 0.18, c)], fill=255)
    d.polygon([(0, c), (c, c - size * 0.18), (n, c), (c, c + size * 0.18)], fill=255)
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    paste(fr, colorize(im, (255, 246, 220)), cx, cy, a, "mm")


# ------------------------------------------------------------------ top label
_TITLE = {}


def title_plate():
    """Persistent title "HIBAH RM1 JUTA": navy glass plate + white/gold 3D type."""
    if "im" not in _TITLE:
        f = font("Montserrat", 58, 800)
        a = white_text("HIBAH", f, tracking=4, color=WHITE)
        m, _ = text_mask("RM1 JUTA", f, tracking=4)
        b = relief(m, bevel=2.5, mat="gold", light=(-0.4, -0.75), sheen=0.45)
        gap = 18
        tw = a.width + gap + b.width
        w, h = tw + 84, 100
        im = pill(w, h, fill=(7, 18, 44, 225), bw=3)
        ty = (h - a.height) // 2 + 1
        im.alpha_composite(a, (42, ty))
        im.alpha_composite(b, (42 + a.width + gap, ty))
        _TITLE["im"] = im
    return _TITLE["im"]


def top_label(fr, t):
    """Title shown for the whole video (also on the end card). Top edge sits at y=232 (safe zone 220)."""
    a = env(t, 0.3, TOTAL + 1, 0.5, 0.0)
    if a <= 0:
        return
    im = title_plate()
    ph = ((t - 1.2) % 4.0) / 1.1  # periodic gold glint
    im = shimmer(im, ph, width=0.12, strength=0.55)
    e = ease_out_back(prog(t, 0.3, 0.6))
    im = scaled(im, 0.85 + 0.15 * e)
    g, pad = glow(im, 18, GOLD, 0.35)
    y = 232 + (100 - im.height) / 2
    paste(fr, g, W / 2 - g.width / 2, y - pad, a * 0.9)
    paste(fr, im, W / 2, y, a, "mt")


# ------------------------------------------------------------------ scenes
def scene_profile(fr, t):
    if not (0.5 <= t <= 4.9):
        return
    x, y, w, h = 130, 1010, 770, 410
    out = prog(t, 4.6, 0.25)
    a = 1 - out
    y += 40 * ease_in_out(out)
    panel(fr, x, y, w, h, reveal=prog(t, 0.55, 0.55), alpha=a)
    if t < 1.0:
        return
    # header
    pulse = 0.6 + 0.4 * math.sin(t * 6)
    d = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    ImageDraw.Draw(d).ellipse((0, 0, 15, 15), fill=GOLD + (255,))
    g, pad = glow(d, 8, GOLD, 1.4)
    paste(fr, g, x + 40 - pad, y + 34 - pad, a * pulse)
    paste(fr, d, x + 40, y + 34, a)
    stagger_text(fr, "PROFIL PESERTA", font("Montserrat", 23, 600), x + 68, y + 24, t, 1.0, tracking=5,
                 per=0.015, dur=0.35, rise=12, alpha=a, color=GOLD_L)
    # ECG holographic trace in header (medical vital sign)
    ecg_x0, ecg_x1, ecg_y = x + 400, x + w - 44, y + 44
    pts = []
    n = int(ecg_x1 - ecg_x0)
    for i in range(0, n, 2):
        u = (i / n * 3) % 1.0
        v = 0
        if 0.40 < u < 0.44: v = -6
        elif 0.46 < u < 0.49: v = 22
        elif 0.49 < u < 0.53: v = -30
        elif 0.53 < u < 0.56: v = 10
        elif 0.68 < u < 0.76: v = -6 * math.sin((u - 0.68) / 0.08 * math.pi)
        pts.append((i, v))
    head = (t - 1.0) * 160 % (n + 60)
    ecg = Image.new("RGBA", (n + 4, 70), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ecg)
    vis = [(px, 35 + py) for px, py in pts if px <= head]
    if len(vis) > 1:
        dd.line(vis, fill=GOLD_L + (230,), width=3, joint="curve")
        hx, hy = vis[-1]
        dd.ellipse((hx - 5, hy - 5, hx + 5, hy + 5), fill=(255, 255, 255, 255))
    g, pad = glow(ecg, 6, GOLD, 1.0)
    paste(fr, g, ecg_x0 - pad, ecg_y - 35 - pad, a * 0.9)
    paste(fr, ecg, ecg_x0, ecg_y - 35, a)
    p = prog(t, 1.0, 0.7)
    hline(fr, x + 40, y + 78, x + 40 + (w - 80) * ease_out_cubic(p), a * 0.6, GOLD, 2)

    # medical badge (3D)
    pb = prog(t, 0.88, 0.7)
    if pb > 0:
        e = ease_out_back(pb)
        theta = (1 - ease_out_cubic(pb)) * 2.6 + 0.28 * math.sin((t - 0.88) * 1.9)
        badge = medic_badge(170, lq_of(t))
        obj3d(fr, badge, x + 128, y + 225 + 6 * math.sin(t * 2.2), theta, 14, a * min(1, pb * 2), scale=0.4 + 0.6 * e)
    # title
    stagger_text(fr, "Doktor", font("PlayfairDisplay", 86, 700), x + 252, y + 92, t, 0.88, per=0.045, dur=0.5,
                 alpha=a)
    chip(fr, "Lelaki", x + 252, y + 222, 168, 62, t, 1.62, a)
    if t >= 2.68:
        age = int(round(32 * ease_out_expo(prog(t, 2.68, 0.55))))
        chip(fr, f"{age} Tahun", x + 438, y + 222, 214, 62, t, 2.68, a)
    chip(fr, "Tidak Merokok", x + 252, y + 300, 330, 62, t, 3.58, a, icon=no_smoke_icon(38))
    pc = prog(t, 3.9, 0.45)
    if pc > 0:
        cb = gold_check_badge(54)
        paste(fr, scaled(cb, 0.5 + 0.5 * ease_out_back(pc)), x + 630, y + 331, a * min(1, pc * 2), "mm")


def scene_hibah(fr, t):
    if not (4.9 <= t <= 9.9):
        return
    x, y, w, h = 130, 1040, 770, 392
    out = prog(t, 9.6, 0.25)
    a = 1 - out
    y += 40 * ease_in_out(out)
    panel(fr, x, y, w, h, reveal=prog(t, 4.95, 0.5), alpha=a)
    if t < 5.0:
        return
    # hologram projector + floating shield
    ps = prog(t, 5.02, 0.8)
    holo_ring(fr, x + 150, y + 330, 230, 42, a * ease_out_cubic(prog(t, 5.0, 0.5)), t)
    if ps > 0:
        e = ease_out_back(ps)
        theta = (1 - ease_out_cubic(ps)) * -1.6 + 0.36 * math.sin((t - 5.0) * 1.9)
        bob = 9 * math.sin(t * 2.4)
        boost = math.exp(-max(0, t - 5.5) / 0.35) * 1.3 if t >= 5.5 else 0
        sh = shield_obj(250, 300, lq_of(t, -4, 5, 1.6))
        obj3d(fr, sh, x + 150, y + 140 + bob + (1 - e) * 90, theta, 20, a * min(1, ps * 2), scale=0.55 + 0.45 * e,
              glow_amt=0.35 + boost)
    X = x + 300
    stagger_text(fr, "HIBAH TAKAFUL", font("Montserrat", 23, 600), X, y + 30, t, 5.02, tracking=5, per=0.015,
                 dur=0.35, rise=12, alpha=a, color=GOLD_L)
    if t >= 5.5:
        pv = prog(t, 5.5, 0.95)
        v = int(round(1_000_000 * ease_out_expo(pv)))
        im = gold_text(f"RM{v:,}", font("Montserrat", 58, 800))
        im = shimmer(im, prog(t, 6.35, 0.7))
        e = ease_out_cubic(prog(t, 5.5, 0.3))
        g, pad = glow(im, 16, GOLD, 0.5 * math.exp(-max(0, t - 6.45) / 0.6))
        paste(fr, g, X - pad, y + 66 - pad, a)
        paste(fr, im, X, y + 66 + (1 - e) * 20, a * e)
    stagger_text(fr, "Nilai perlindungan", font("Montserrat", 22, 500), X + 4, y + 146, t, 5.85, per=0.012, dur=0.3,
                 rise=10, alpha=a * 0.8)
    hline(fr, X, y + 190, X + 430 * ease_out_cubic(prog(t, 6.4, 0.5)), a * 0.55)
    stagger_text(fr, "CARUMAN", font("Montserrat", 22, 600), X, y + 206, t, 6.4, tracking=6, per=0.02, dur=0.35,
                 rise=10, alpha=a, color=GOLD_L)
    if t >= 6.86:
        v = int(round(130 * ease_out_expo(prog(t, 6.86, 0.6))))
        im = gold_text(f"RM{v}", font("Montserrat", 66, 800))
        im = shimmer(im, prog(t, 9.14, 0.55))
        e = ease_out_cubic(prog(t, 6.86, 0.3))
        paste(fr, im, X, y + 236 + (1 - e) * 20, a * e)
        rm_w = gold_text("RM130", font("Montserrat", 66, 800)).width
        stagger_text(fr, "/ bulan", font("Montserrat", 32, 500), X + rm_w + 10, y + 266, t, 7.94, per=0.03,
                     dur=0.35, rise=12, alpha=a)
        # underline sweep on "sahaja"
        pu = prog(t, 9.14, 0.35)
        if pu > 0:
            hline(fr, X + 4, y + 318, X + 4 + (rm_w - 8) * ease_out_cubic(pu), a, GOLD_L, 4)
    stagger_text(fr, "≈ RM4.27 sehari", font("Montserrat", 23, 500), X + 4, y + 330, t, 8.3, per=0.012,
                 dur=0.3, rise=10, alpha=a * 0.75)
    # coin
    pcn = prog(t, 6.86, 0.5)
    if pcn > 0:
        th = (t - 6.86) * 2.4
        th = ((th + math.pi / 2) % math.pi) - math.pi / 2
        coin = coin_obj(104, lq_of(t, -3, 6, 2.0))
        obj3d(fr, coin, 842, 990 + 6 * math.sin(t * 2.7), th, 10, a * min(1, pcn * 2),
              scale=0.4 + 0.6 * ease_out_back(pcn))
    # "sahaja!" stamp
    pst = prog(t, 9.14, 0.45)
    if pst > 0:
        im = gold_text("sahaja!", font("PlayfairDisplay-Italic", 50, 700))
        s = 1.7 - 0.7 * ease_out_back(pst)
        im2 = scaled(im, s)
        g, pad = glow(im2, 18, GOLD, 0.9 * math.exp(-(t - 9.14) / 0.5))
        cx, cy = x + w - 40 - im.width / 2, y + 340
        paste(fr, g, cx - g.width / 2, cy - g.height / 2, a)
        paste(fr, im2, cx, cy, a * min(1, pst * 2.5), "mm")
        for i, (dx, dy) in enumerate(((-110, -36), (84, -34), (-60, 12), (78, 12))):
            ps2 = prog(t, 9.2 + i * 0.05, 0.5)
            sparkle(fr, cx + dx, cy + dy, 22, a * math.sin(math.pi * ps2))


def scene_commit(fr, t):
    if not (9.8 <= t <= 12.25):
        return
    x, y, w, h = 130, 1000, 770, 420
    out = prog(t, 11.95, 0.25)
    a = 1 - out
    y += 40 * ease_in_out(out)
    panel(fr, x, y, w, h, reveal=prog(t, 9.85, 0.5), alpha=a)
    if t < 10.0:
        return
    ic = shield_obj(34, 40, -5)
    paste(fr, ic, x + 40, y + 22, a * ease_out_cubic(prog(t, 10.0, 0.3)))
    stagger_text(fr, "LINDUNGI KOMITMEN", font("Montserrat", 23, 600), x + 88, y + 26, t, 10.0, tracking=5,
                 per=0.012, dur=0.3, rise=12, alpha=a, color=GOLD_L)
    fw = stagger_text(fr, "Beban ", font("PlayfairDisplay", 60, 700), x + 40, y + 70, t, 10.98, per=0.04, alpha=a)
    stagger_text(fr, "Komitmen", font("PlayfairDisplay-Italic", 60, 700), x + 40 + fw - 6, y + 70, t, 11.36,
                 fill="gold", per=0.04, alpha=a)
    labels = ["Pinjaman Rumah", "Pinjaman Kereta", "Perbelanjaan Keluarga"]
    fills = [0.82, 0.58, 0.7]
    gold_k = ease_in_out(prog(t, 11.36, 0.6))
    for i, (lab, f0) in enumerate(zip(labels, fills)):
        ry = y + 178 + i * 76
        t0 = 10.05 + i * 0.15
        stagger_text(fr, lab, font("Montserrat", 24, 500), x + 40, ry, t, t0, per=0.01, dur=0.3, rise=10,
                     alpha=a * 0.92)
        pb = prog(t, t0, 0.4)
        if pb <= 0:
            continue
        bx0, bx1, by = x + 40, x + 560, ry + 40
        trk = pill(bx1 - bx0, 12, fill=(255, 255, 255, 40), border=(120, 120, 140), bw=0)
        paste(fr, trk, bx0, by, a * pb)
        frac = f0 * ease_out_cubic(prog(t, t0 + 0.1, 0.8))
        frac = frac + (1 - frac) * gold_k
        fw2 = max(12, int((bx1 - bx0) * frac))
        m = Image.new("L", (fw2, 12), 255)
        if gold_k > 0:
            bar = gradient_fill(m, [(0, (176, 130, 46)), (0.5, (246, 214, 130)), (1, (212, 175, 55))], vertical=False)
            white = colorize(m, (225, 230, 242))
            bar = Image.blend(white, bar, gold_k)
        else:
            bar = colorize(m, (225, 230, 242))
        bar.putalpha(pill(fw2, 12).getchannel("A"))
        paste(fr, bar, bx0, by, a)
        pc = prog(t, 10.98 + i * 0.14, 0.4)
        if pc > 0:
            cb = gold_check_badge(50)
            paste(fr, scaled(cb, 0.4 + 0.6 * ease_out_back(pc)), x + 630, ry + 30, a * min(1, pc * 2), "mm")
    if gold_k > 0:
        im = white_text("100% DILINDUNGI", font("Montserrat", 20, 700), tracking=3, color=GOLD_L)
        paste(fr, im, x + 560 - im.width, y + 404 - im.height + 6, a * gold_k)


def scene_family(fr, t):
    if not (12.15 <= t <= 14.85):
        return
    x, y, w, h = 130, 1000, 770, 430
    out = prog(t, 14.55, 0.25)
    a = 1 - out
    y += 40 * ease_in_out(out)
    panel(fr, x, y, w, h, reveal=prog(t, 12.2, 0.45), alpha=a)
    if t < 12.3:
        return
    cx = x + w / 2 - 20
    base = y + 228
    # dome shield outline
    pd = prog(t, 14.02, 0.55)
    if pd > 0:
        sw, shh = 470, 222
        outer = shield_mask(sw, shh, 0.0)
        inner = shield_mask(sw, shh, 0.025)
        ring = Image.fromarray(np.clip(np.asarray(outer, np.int16) - np.asarray(inner, np.int16), 0, 255).astype(np.uint8))
        fill = colorize(outer.point(lambda v: v * 0.10), GOLD)
        rim = relief(ring, bevel=3, mat="gold", light=(-0.4, -0.8))
        im = fill
        im.alpha_composite(rim)
        e = ease_out_back(pd)
        im2 = scaled(im, 1.25 - 0.25 * e)
        g, pad = glow(im2, 20, GOLD, 0.9)
        paste(fr, g, cx - g.width / 2, y + 22 + shh / 2 - g.height / 2, a * pd)
        paste(fr, im2, cx, y + 22 + shh / 2, a * min(1, pd * 2), "mm")
    figs = [("woman", -118, 96, 136, 13.84), ("man", 0, 116, 170, 12.3), ("man", 104, 70, 100, 13.94),
            ("woman", 178, 62, 92, 14.04)]
    for kind, dx, fw, fh, t0 in figs:
        p = prog(t, t0, 0.5)
        if p <= 0:
            continue
        e = ease_out_back(p)
        isdad = (dx == 0)
        mat = "pearl"
        im = person_obj(fw, fh, kind, mat, lq_of(t, -4, 3, 1.4))
        if isdad and t >= 13.3:
            k = ease_out_cubic(prog(t, 13.3, 0.4))
            g, pad = glow(im, 22, GOLD, 1.0 * k)
            paste(fr, g, cx + dx - g.width / 2, base - fh - pad + (1 - e) * 30, a)
        paste(fr, im, cx + dx - fw / 2, base - fh + (1 - e) * 30, a * min(1, p * 2))
    # ground line
    hline(fr, cx - 250, base + 2, cx - 250 + 500 * ease_out_cubic(prog(t, 12.35, 0.6)), a * 0.6, GOLD_L, 2)
    # BREADWINNER
    pt = prog(t, 13.3, 0.6)
    if pt > 0:
        m, boxes = text_mask("BREADWINNER", font("Cinzel", 64, 800), tracking=6)
        im = relief(m, bevel=2.5, mat="gold", light=(lq_of(t, -4, 5, 2) / 10, -0.7), sheen=0.5)
        im = shimmer(im, prog(t, 13.9, 0.7))
        cxt = x + w / 2
        for i, (x0, x1) in enumerate(boxes):
            p = prog(t, 13.3 + i * 0.03, 0.45)
            if p <= 0:
                continue
            e = ease_out_cubic(p)
            g = im.crop((int(max(0, x0 - 4)), 0, int(min(im.width, x1 + 8)), im.height))
            paste(fr, g, cxt - im.width / 2 + max(0, x0 - 4), y + 250 + (1 - e) * 30, a * min(1, p * 1.6))
    stagger_text(fr, "of the family", font("PlayfairDisplay-Italic", 42, 500), x + w / 2, y + 340, t, 14.02,
                 per=0.025, dur=0.4, alpha=a, anchor="m")


def scene_cta(fr, t):
    if not (14.8 <= t <= 17.7):
        return
    x, y, w, h = 130, 1040, 770, 380
    out = prog(t, 17.4, 0.25)
    a = 1 - out
    y += 40 * ease_in_out(out)
    panel(fr, x, y, w, h, reveal=prog(t, 14.85, 0.45), alpha=a)
    if t < 14.95:
        return
    cx = x + w / 2
    stagger_text(fr, "Tunggu apa lagi?", font("PlayfairDisplay-Italic", 64, 700), cx, y + 34, t, 14.95, per=0.03,
                 alpha=a, anchor="m")
    stagger_text(fr, "DAPATKAN", font("Montserrat", 24, 600), cx, y + 140, t, 15.54, tracking=10, per=0.02,
                 dur=0.35, rise=12, alpha=a, anchor="m", color=GOLD_L)
    pb = prog(t, 16.04, 0.55)
    if pb > 0:
        bw, bh = 620, 112
        m = _rr_mask(bw, bh, bh // 2)
        btn = relief(m, bevel=10, mat="gold", light=(lq_of(t, -3, 6, 2.2) / 10, -0.75), sheen=0.45)
        tm = colorize(text_mask("KONSULTASI PERCUMA", font("Montserrat", 38, 800), tracking=2)[0], NAVY)
        btn.alpha_composite(tm, ((bw - tm.width) // 2, (bh - tm.height) // 2))
        ph = (t - 16.04) % 1.6 / 1.0
        btn = shimmer(btn, ph, width=0.15, strength=0.6)
        pulse = 0
        if t >= 16.76:
            dt = t - 16.76
            pulse = 0.07 * math.sin(min(1, dt / 0.35) * math.pi)
        s = (0.6 + 0.4 * ease_out_back(pb)) * (1 + pulse)
        im = scaled(btn, s)
        gl = 0.6 + (1.2 * math.exp(-(t - 16.76) / 0.5) if t >= 16.76 else 0)
        g, pad = glow(im, 26, GOLD, gl)
        cy = y + 250
        d, pad2 = drop_shadow(im, 14, (0, 14), 0.5)
        paste(fr, g, cx - g.width / 2, cy - g.height / 2, a * min(1, pb * 2))
        paste(fr, d, cx - d.width / 2, cy - d.height / 2, a * min(1, pb * 2))
        if t >= 16.76:
            for i, (dx, dy) in enumerate(((-300, -60), (290, -54), (-250, 62), (310, 50), (0, -80))):
                ps2 = prog(t, 16.8 + i * 0.06, 0.55)
                sparkle(fr, cx + dx * 0.95, cy + dy, 26, a * math.sin(math.pi * ps2))


def scene_cred(fr, t):
    if not (17.6 <= t <= END_START + 0.1):
        return
    x, y, w, h = 130, 1100, 770, 320
    a = 1.0
    panel(fr, x, y, w, h, reveal=prog(t, 17.65, 0.45), alpha=a)
    if t < 17.76:
        return
    pm = prog(t, 17.76, 0.8)
    if pm > 0:
        e = ease_out_back(pm)
        theta = (1 - ease_out_cubic(pm)) * 3.0 + 0.3 * math.sin((t - 17.76) * 2)
        md = medal_obj(176, lq_of(t, -4, 5, 1.5))
        obj3d(fr, md, x + 135, y + 160 + 6 * math.sin(t * 2.3), theta, 14, a * min(1, pm * 2), scale=0.4 + 0.6 * e,
              glow_amt=0.3)
    X = x + 262
    stagger_text(fr, "AIA CERTIFIED", font("Montserrat", 28, 700), X, y + 46, t, 18.45, tracking=6, per=0.02,
                 dur=0.35, rise=12, alpha=a, color=GOLD_L)
    stagger_text(fr, "FinCoach", font("PlayfairDisplay", 70, 700), X, y + 92, t, 19.1, per=0.04, alpha=a)
    stagger_text(fr, "Practitioner", font("PlayfairDisplay-Italic", 50, 600), X + 2, y + 188, t, 19.4,
                 fill="gold", per=0.03, alpha=a)


# ------------------------------------------------------------------ end card
_END_BG = {}


def chat_icon(s):
    """Generic chat-bubble + handset icon in navy (not a brand logo)."""
    n = s * 4
    m = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((n * 0.06, n * 0.06, n * 0.94, n * 0.94), fill=255)
    d.polygon([(n * 0.12, n * 0.97), (n * 0.2, n * 0.68), (n * 0.38, n * 0.86)], fill=255)
    d.ellipse((n * 0.16, n * 0.16, n * 0.84, n * 0.84), fill=0)
    d.polygon([(n * 0.17, n * 0.86), (n * 0.23, n * 0.72), (n * 0.3, n * 0.8)], fill=0)
    # handset
    d.rounded_rectangle((n * 0.32, n * 0.3, n * 0.46, n * 0.44), radius=n * 0.04, fill=255)
    d.rounded_rectangle((n * 0.56, n * 0.56, n * 0.7, n * 0.7), radius=n * 0.04, fill=255)
    d.line((n * 0.38, n * 0.4, n * 0.62, n * 0.64), fill=255, width=int(n * 0.09))
    m = m.resize((s, s), Image.LANCZOS)
    return colorize(m, NAVY)


def end_card(t, frozen):
    te = t - END_START
    key = "bg"
    if key not in _END_BG:
        im = frozen.filter(ImageFilter.GaussianBlur(30))
        arr = np.asarray(im, np.float32)
        arr = arr * 0.28 + NAVY_F * 0.72
        r = np.sqrt(((_xx - W / 2) / 520) ** 2 + ((_yy - 640) / 640) ** 2)
        glowc = np.exp(-r ** 2 * 1.6)[..., None] * np.array([60, 46, 14], np.float32)
        arr = arr + glowc
        arr = arr * (VIG * 0.6 + 0.4)
        _END_BG[key] = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    bg = _END_BG[key]
    z = 1.0 + 0.04 * te / 2
    a = 1 / z
    bg = bg.transform((W, H), Image.AFFINE, (a, 0, 540 - 540 * a, 0, a, 900 - 900 * a), Image.BILINEAR)
    fr = bg.convert("RGBA")
    particles(fr, t, PARTS_END, 240, 1430, 0.9)
    cx = W / 2
    holo_ring(fr, cx, 790, 300, 54, ease_out_cubic(prog(te, 0.1, 0.5)), t)
    ps = prog(te, 0.1, 0.8)
    if ps > 0:
        e = ease_out_back(ps)
        theta = (1 - ease_out_cubic(ps)) * 2.2 + 0.32 * math.sin(te * 1.8)
        sh = shield_obj(270, 320, lq_of(t, -4, 5, 1.6), "star")
        obj3d(fr, sh, cx, 590 + 8 * math.sin(te * 2.4), theta, 22, min(1, ps * 2), scale=0.5 + 0.5 * e,
              glow_amt=0.6)
    stagger_text(fr, "Konsultasi", font("PlayfairDisplay", 80, 700), cx, 830, te, 0.3, per=0.035, anchor="m")
    pp = prog(te, 0.5, 0.5)
    if pp > 0:
        m, _ = text_mask("PERCUMA", font("Montserrat", 92, 800), tracking=14)
        im = relief(m, bevel=3, mat="gold", light=(lq_of(t, -3, 5, 2) / 10, -0.7), sheen=0.5)
        im = shimmer(im, prog(te, 0.9, 0.8))
        e = ease_out_cubic(pp)
        im2 = scaled(im, 1.15 - 0.15 * e)
        g, pad = glow(im2, 22, GOLD, 0.6)
        paste(fr, g, cx - g.width / 2, 980 - g.height / 2, min(1, pp * 2))
        paste(fr, im2, cx, 980, min(1, pp * 2), "mm")
    pl = prog(te, 0.7, 0.6)
    if pl > 0:
        L = 300 * ease_out_cubic(pl)
        hline(fr, cx - 24 - L, 1068, cx - 24, 0.8, GOLD_L, 2)
        hline(fr, cx + 24, 1068, cx + 24 + L, 0.8, GOLD_L, 2)
        dm = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        ImageDraw.Draw(dm).polygon([(8, 0), (16, 8), (8, 16), (0, 8)], fill=GOLD_L + (255,))
        paste(fr, dm, cx, 1069, pl, "mm")
    stagger_text(fr, "Hibah  •  Takaful  •  Perlindungan Keluarga", font("Montserrat", 25, 500), cx, 1092,
                 te, 0.8, per=0.008, dur=0.3, rise=10, anchor="m", color=(235, 238, 246))
    pb = prog(te, 1.0, 0.5)
    if pb > 0:
        bw, bh = 600, 104
        btn = relief(_rr_mask(bw, bh, bh // 2), bevel=10, mat="gold", light=(lq_of(t, -3, 6, 2.2) / 10, -0.75),
                     sheen=0.45)
        ic = chat_icon(46)
        tm = colorize(text_mask("KLIK WHATSAPP SEKARANG", font("Montserrat", 31, 800), tracking=1)[0], NAVY)
        x0 = (bw - (ic.width + 14 + tm.width)) // 2
        btn.alpha_composite(ic, (x0, (bh - ic.height) // 2))
        btn.alpha_composite(tm, (x0 + ic.width + 14, (bh - tm.height) // 2))
        btn = shimmer(btn, ((te - 1.3) % 1.4) / 1.0, width=0.15, strength=0.6)
        pulse = 1 + 0.035 * math.sin(max(0, te - 1.5) * 6.0) if te > 1.5 else 1.0
        im = scaled(btn, (0.6 + 0.4 * ease_out_back(pb)) * pulse)
        g, pad = glow(im, 24, GOLD, 0.9)
        paste(fr, g, cx - g.width / 2, 1190 - g.height / 2, min(1, pb * 2))
        d, pad2 = drop_shadow(im, 14, (0, 14), 0.5)
        paste(fr, d, cx - d.width / 2, 1190 - d.height / 2, min(1, pb * 2))
    top_label(fr, t)
    stagger_text(fr, "AIA CERTIFIED FINCOACH PRACTITIONER", font("Montserrat", 21, 600), cx, 1272, te, 1.2,
                 tracking=4, per=0.006, dur=0.3, rise=8, anchor="m", color=GOLD_L, alpha=0.85)
    return fr


# ------------------------------------------------------------------ guides
def draw_guides(fr):
    d = ImageDraw.Draw(fr)
    s = SAFE
    d.rectangle((s["x0"], s["y0"], s["x1"], s["y1"]), outline=(255, 40, 40, 255), width=3)
    d.rectangle((BTN_X, 1000, W, H - 300), outline=(255, 140, 0, 255), width=3)
    d.text((s["x0"] + 6, s["y0"] + 4), "SAFE ZONE", fill=(255, 60, 60, 255), font=font("Montserrat", 22, 700))


# ------------------------------------------------------------------ frame
def render_frame(i, src_rgb, frozen, guides=False):
    t = i / FPS
    if t >= END_START:
        fr = end_card(t, frozen)
        arr = np.asarray(fr.convert("RGB"), np.float32)
        # flash transition into end card
        fl = 0.0
        if t < END_START + 0.4:
            fl = 0.75 * math.exp(-(t - END_START) / 0.12)
        arr = arr + (np.array([255, 240, 210], np.float32) - arr) * fl
        fo = prog(t, TOTAL - 0.35, 0.35)
        arr = arr * (1 - fo) + NAVY_F * fo
    else:
        img = camera(Image.fromarray(src_rgb), t)
        arr = grade(np.asarray(img))
        # intro: fade from navy
        fi = 1 - ease_out_cubic(prog(t, 0.0, 0.45))
        arr = arr * (1 - fi) + NAVY_F * fi
        fr = Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")
        particles(fr, t, PARTS, 880, 1430, 0.55)
        top_label(fr, t)
        scene_profile(fr, t)
        scene_hibah(fr, t)
        scene_commit(fr, t)
        scene_family(fr, t)
        scene_cta(fr, t)
        scene_cred(fr, t)
        arr = np.asarray(fr.convert("RGB"), np.float32)
        for ts in (0.05, 4.88, 9.78, 12.12, 14.8, 17.58):
            arr = light_sweep(arr, prog(t, ts, 0.55))
        if END_START - 0.2 <= t < END_START:  # pre-flash glow
            k = prog(t, END_START - 0.2, 0.2) ** 2 * 0.75
            arr = arr + (np.array([255, 240, 210], np.float32) - arr) * k
    out = np.clip(arr, 0, 255).astype(np.uint8)
    if guides:
        g = Image.fromarray(out).convert("RGBA")
        draw_guides(g)
        out = np.asarray(g.convert("RGB"))
    return out


def read_frames(src, a, b):
    """Yield source frames a..b inclusive (rgb24)."""
    cmd = ["ffmpeg", "-v", "error", "-i", src, "-vf", f"select='between(n\\,{a}\\,{b})'", "-vsync", "0",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    p.wait()


def get_frozen(src):
    for f in read_frames(src, SRC_LAST_GOOD, SRC_LAST_GOOD):
        arr = grade(np.asarray(camera(Image.fromarray(f), END_START)))
        return Image.fromarray(arr.astype(np.uint8), "RGB")


def work(args):
    src, a, b, out, guides = args
    frozen = get_frozen(src)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "15",
                            "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-colorspace", "bt709", out], stdin=subprocess.PIPE)
    last_src = SRC_LAST_GOOD + 1
    src_iter = read_frames(src, a, min(b, last_src)) if a <= last_src else iter(())
    for i in range(a, b + 1):
        f = next(src_iter, None) if i <= last_src else None
        enc.stdin.write(render_frame(i, f, frozen, guides).tobytes())
    enc.stdin.close()
    enc.wait()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--guides", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--still", type=float, nargs="*", help="render stills at these times instead")
    args = ap.parse_args()
    if args.still:
        frozen = get_frozen(args.src)
        for ts in args.still:
            i = int(round(ts * FPS))
            f = None
            if i <= SRC_LAST_GOOD + 1:
                f = next(read_frames(args.src, i, i))
            Image.fromarray(render_frame(i, f, frozen, args.guides)).save(f"{args.out}_{ts:05.2f}.jpg", quality=88)
        return
    n = NFRAMES
    k = args.workers
    bounds = [(n * j // k, n * (j + 1) // k - 1) for j in range(k)]
    tmpdir = os.path.dirname(os.path.abspath(args.out))
    jobs = [(args.src, a, b, os.path.join(tmpdir, f"_chunk{j}.mp4"), args.guides) for j, (a, b) in enumerate(bounds)]
    with Pool(k) as p:
        outs = p.map(work, jobs)
    lst = os.path.join(tmpdir, "_chunks.txt")
    with open(lst, "w") as f:
        for o in outs:
            f.write(f"file '{o}'\n")
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                           args.out])
    for o in outs:
        os.remove(o)
    os.remove(lst)


if __name__ == "__main__":
    main()
