"""Graphics primitives: pseudo-3D relief renderer, materials, panels, typography."""
import os
import math
import functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "fonts")

W, H, FPS = 1080, 1920, 30

# Safe zone (TikTok / Reels): 220 top, 480 bottom, 120 left/right.
SAFE = dict(x0=120, y0=220, x1=W - 120, y1=H - 480)
# Lower-right button column: keep graphics left of this when below y=1000.
BTN_X = 905

NAVY = (7, 18, 44)
NAVY2 = (14, 34, 78)
GOLD = (212, 175, 55)
GOLD_L = (246, 226, 168)
GOLD_D = (150, 110, 34)
WHITE = (255, 255, 255)


# ----------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease_out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


def ease_out_expo(x):
    x = clamp(x)
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def ease_out_back(x, s=1.7):
    x = clamp(x)
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def prog(t, t0, dur):
    return clamp((t - t0) / dur)


def env(t, t_in, t_out, fade_in=0.35, fade_out=0.3):
    """0..1 visibility envelope."""
    if t < t_in or t > t_out:
        return 0.0
    a = ease_out_cubic((t - t_in) / fade_in) if fade_in > 0 else 1.0
    b = ease_in_out((t_out - t) / fade_out) if fade_out > 0 else 1.0
    return min(a, b)


# ----------------------------------------------------------------- fonts
@functools.lru_cache(None)
def font(name, size, weight=None):
    f = ImageFont.truetype(os.path.join(FONT_DIR, name + ".ttf"), size)
    if weight is not None:
        axes = f.get_variation_axes()
        vals = []
        for a in axes:
            n = a["name"]
            n = n.decode() if isinstance(n, bytes) else n
            if n.lower().startswith("weight"):
                vals.append(weight)
            elif n.lower().startswith("optical"):
                vals.append(min(a["maximum"], max(a["minimum"], size / 2)))
            else:
                vals.append(a["default"])
        f.set_variation_by_axes(vals)
    return f


def text_mask(text, fnt, tracking=0, pad=6):
    """Render text to an L mask with letter tracking. Returns (Image L, list of glyph boxes)."""
    asc, desc = fnt.getmetrics()
    xs, x = [], 0.0
    for ch in text:
        xs.append(x)
        x += fnt.getlength(ch) + tracking
    w = int(math.ceil(x - tracking)) + pad * 2
    h = asc + desc + pad * 2
    im = Image.new("L", (max(w, 1), h), 0)
    d = ImageDraw.Draw(im)
    boxes = []
    for ch, cx in zip(text, xs):
        d.text((pad + cx, pad), ch, font=fnt, fill=255)
        boxes.append((pad + cx, pad + cx + fnt.getlength(ch)))
    return im, boxes


def colorize(mask, color):
    im = Image.new("RGBA", mask.size, tuple(color) + (0,))
    im.putalpha(mask)
    return im


def gradient_fill(mask, stops, vertical=True):
    """Fill mask with a multi-stop gradient. stops: [(pos, (r,g,b)), ...]"""
    w, h = mask.size
    n = h if vertical else w
    pos = np.linspace(0, 1, n)
    cols = np.stack([np.interp(pos, [s[0] for s in stops], [s[1][c] for s in stops]) for c in range(3)], -1)
    if vertical:
        arr = np.repeat(cols[:, None, :], w, 1)
    else:
        arr = np.repeat(cols[None, :, :], h, 0)
    rgba = np.dstack([arr, np.asarray(mask, np.float32)]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


GOLD_TEXT = [(0, (255, 244, 205)), (0.42, (236, 200, 110)), (0.58, (196, 148, 52)), (1.0, (246, 214, 130))]


def gold_text(text, fnt, tracking=0):
    m, _ = text_mask(text, fnt, tracking)
    return gradient_fill(m, GOLD_TEXT)


def white_text(text, fnt, tracking=0, color=WHITE):
    m, _ = text_mask(text, fnt, tracking)
    return colorize(m, color)


# ----------------------------------------------------------------- image ops
def with_alpha(im, a):
    if a >= 0.999:
        return im
    im = im.copy()
    al = im.getchannel("A").point(lambda v: int(v * a))
    im.putalpha(al)
    return im


def scaled(im, s, resample=Image.LANCZOS):
    if abs(s - 1) < 1e-3:
        return im
    w, h = im.size
    return im.resize((max(1, int(w * s)), max(1, int(h * s))), resample)


def paste(dst, src, x, y, a=1.0, anchor="lt"):
    """Alpha-composite src onto dst (RGBA) at (x,y). anchor: lt, mm, mt, lm."""
    if src is None or a <= 0.003:
        return
    src = with_alpha(src, a)
    w, h = src.size
    if anchor == "mm":
        x, y = x - w / 2, y - h / 2
    elif anchor == "mt":
        x = x - w / 2
    elif anchor == "lm":
        y = y - h / 2
    elif anchor == "mb":
        x, y = x - w / 2, y - h
    x, y = int(round(x)), int(round(y))
    # clip
    sx0, sy0 = max(0, -x), max(0, -y)
    sx1, sy1 = min(w, dst.width - x), min(h, dst.height - y)
    if sx1 <= sx0 or sy1 <= sy0:
        return
    if (sx0, sy0, sx1, sy1) != (0, 0, w, h):
        src = src.crop((sx0, sy0, sx1, sy1))
    dst.alpha_composite(src, (x + sx0, y + sy0))


def glow(im, radius=18, color=GOLD, strength=0.8):
    """Return an image = soft colored glow of im's alpha (bigger canvas)."""
    pad = radius * 2
    a = im.getchannel("A")
    big = Image.new("L", (im.width + pad * 2, im.height + pad * 2), 0)
    big.paste(a, (pad, pad))
    big = big.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: int(min(255, v * strength)))
    return colorize(big, color), pad


def shimmer(im, phase, width=0.12, strength=0.85, angle=0.35):
    """Brighten a diagonal band across im (phase 0..1 sweeps across)."""
    if phase <= 0 or phase >= 1:
        return im
    arr = np.asarray(im).astype(np.float32)
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = (xx + yy * angle) / (w + h * angle)
    c = -0.2 + phase * 1.4
    band = np.exp(-((u - c) ** 2) / (2 * (width / 2.5) ** 2)) * strength
    arr[..., :3] = arr[..., :3] + (255 - arr[..., :3]) * band[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


# ----------------------------------------------------------------- relief (pseudo 3D)
MATS = {
    "gold": [(0.0, (34, 20, 4)), (0.28, (112, 76, 20)), (0.5, (190, 140, 52)), (0.72, (232, 192, 104)),
             (0.92, (252, 228, 160)), (1.15, (255, 250, 232)), (2.0, (255, 255, 250))],
    "pearl": [(0.0, (70, 82, 110)), (0.3, (160, 172, 196)), (0.55, (218, 224, 238)), (0.8, (244, 246, 252)),
              (1.0, (255, 255, 255)), (2.0, (255, 255, 255))],
    "navy": [(0.0, (2, 5, 14)), (0.3, (6, 16, 40)), (0.55, (14, 34, 78)), (0.8, (46, 82, 150)),
             (1.05, (170, 200, 250)), (2.0, (240, 248, 255))],
}


def _lut(mat, I):
    stops = MATS[mat]
    xs = [s[0] for s in stops]
    return np.stack([np.interp(I, xs, [s[1][c] for s in stops]) for c in range(3)], -1)


def relief(mask, bevel=10.0, mat="gold", light=(-0.55, -0.75), sheen=0.35, emboss=1.0, flat=0.0):
    """Render a mask (L image or float array 0..1) as a bevelled metallic object -> RGBA Image."""
    if isinstance(mask, Image.Image):
        m = np.asarray(mask, np.float32) / 255.0
    else:
        m = mask.astype(np.float32)
    inside = m > 0.5
    d = ndimage.distance_transform_edt(inside).astype(np.float32)
    h = np.clip(d / bevel, 0, 1)
    h = np.sin(h * np.pi / 2) + flat * 0
    h = ndimage.gaussian_filter(h, 0.9)
    gy, gx = np.gradient(h * bevel * emboss * 0.9)
    nx, ny, nz = -gx, -gy, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + 1)
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    L = np.array([light[0], light[1], 0.85])
    L /= np.linalg.norm(L)
    diff = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    rx, ry, rz = 2 * nz * nx, 2 * nz * ny, 2 * nz * nz - 1
    rl = np.clip(rx * L[0] + ry * L[1] + rz * L[2], 0, 1)
    hh, ww = m.shape
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    u = (xx / max(ww, 1) + yy / max(hh, 1) * 0.6) / 1.6
    # light position drives where the broad sheen band sits
    c = 0.5 + light[0] * 0.55
    band = np.exp(-((u - c) ** 2) / 0.018)
    grad = 0.12 * (1 - yy / max(hh, 1))  # top a little brighter
    I = (0.16 + 0.36 * diff + 0.30 * rl ** 6 + 0.95 * rl ** 48 + 0.22 * np.clip(-ry, 0, 1) ** 1.5
         + 0.28 * (1 - nz) + sheen * band + grad)
    if mat == "gold":
        # fine brushed streaks
        rng = np.random.default_rng(7)
        streak = ndimage.gaussian_filter(rng.standard_normal((hh, ww)).astype(np.float32), (0.6, 18))
        I = I + streak * 0.3
    rgb = _lut(mat, I)
    a = np.clip(m, 0, 1) * 255
    return Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), "RGBA")


def inner_shadow(mask, radius=6, offset=(3, 5), strength=0.65):
    """Dark inner shadow inside mask (for recessed enamel)."""
    inv = ImageChops.invert(mask)
    sh = Image.new("L", mask.size, 0)
    sh.paste(inv, offset)
    sh = sh.filter(ImageFilter.GaussianBlur(radius))
    sh = ImageChops.multiply(sh, mask).point(lambda v: int(v * strength))
    return colorize(sh, (0, 0, 0))


def drop_shadow(im, radius=14, offset=(0, 14), strength=0.55, color=(0, 0, 0)):
    pad = radius * 2 + max(abs(offset[0]), abs(offset[1]))
    a = im.getchannel("A")
    big = Image.new("L", (im.width + pad * 2, im.height + pad * 2), 0)
    big.paste(a, (pad + offset[0], pad + offset[1]))
    big = big.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: int(v * strength))
    out = colorize(big, color)
    out.alpha_composite(im, (pad, pad))
    return out, pad


def extrude(front, theta, depth=16, side_mat="gold"):
    """Fake 3D rotation around Y: squash front by cos(theta), add an extruded side wall."""
    c, s = math.cos(theta), math.sin(theta)
    w, h = front.size
    fw = max(2, int(w * abs(c)))
    f = front.resize((fw, h), Image.LANCZOS)
    dx_total = s * depth
    pad = int(abs(dx_total)) + 2
    out = Image.new("RGBA", (fw + pad * 2, h), (0, 0, 0, 0))
    a = f.getchannel("A")
    steps = max(2, int(abs(dx_total)))
    side_cols = {"gold": ((92, 62, 16), (176, 130, 46)), "pearl": ((120, 130, 150), (200, 206, 220)),
                 "navy": ((4, 10, 26), (24, 50, 100))}[side_mat]
    for i in range(steps, 0, -1):
        k = i / steps
        col = tuple(int(side_cols[0][j] * k + side_cols[1][j] * (1 - k)) for j in range(3))
        layer = colorize(a, col)
        out.alpha_composite(layer, (int(pad - dx_total * k), 0))
    out.alpha_composite(f, (pad, 0))
    return out


# ----------------------------------------------------------------- shapes (masks, supersampled)
SS = 3


def _canvas(w, h):
    im = Image.new("L", (w * SS, h * SS), 0)
    return im, ImageDraw.Draw(im)


def _down(im, w, h):
    return im.resize((w, h), Image.LANCZOS)


def _bez(p0, p1, p2, n=24):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        pts.append((x, y))
    return pts


def shield_points(w, h, inset=0.0):
    w2, h2 = w * (1 - 2 * inset), h * (1 - 2 * inset)
    ox, oy = w * inset, h * inset * 1.05
    pts = []
    n = 30
    for i in range(n + 1):  # top edge with gentle crest
        x = i / n
        y = 0.12 * (2 * x - 1) ** 2 - 0.0
        pts.append((x, y + 0.02 * math.sin(math.pi * x) * 0))
    pts += _bez((1, 0.12), (1.0, 0.62), (0.5, 1.0))[1:]
    pts += _bez((0.5, 1.0), (0.0, 0.62), (0, 0.12))[1:]
    return [(ox + x * w2, oy + y * h2) for x, y in pts]


@functools.lru_cache(None)
def shield_mask(w, h, inset=0.0):
    im, d = _canvas(w, h)
    d.polygon([(x * SS, y * SS) for x, y in shield_points(w, h, inset)], fill=255)
    return _down(im, w, h)


@functools.lru_cache(None)
def check_mask(w, h, cx, cy, size, thick):
    im, d = _canvas(w, h)
    pts = [(cx - size * 0.5, cy + size * 0.02), (cx - size * 0.12, cy + size * 0.38), (cx + size * 0.55, cy - size * 0.36)]
    d.line([(x * SS, y * SS) for x, y in pts], fill=255, width=int(thick * SS), joint="curve")
    r = thick * SS / 2
    for x, y in (pts[0], pts[2]):
        d.ellipse((x * SS - r, y * SS - r, x * SS + r, y * SS + r), fill=255)
    return _down(im, w, h)


@functools.lru_cache(None)
def circle_mask(size, inset=0):
    im, d = _canvas(size, size)
    d.ellipse((inset * SS, inset * SS, (size - inset) * SS, (size - inset) * SS), fill=255)
    return _down(im, size, size)


@functools.lru_cache(None)
def ring_mask(size, r_out, r_in):
    im, d = _canvas(size, size)
    c = size * SS / 2
    d.ellipse((c - r_out * SS, c - r_out * SS, c + r_out * SS, c + r_out * SS), fill=255)
    d.ellipse((c - r_in * SS, c - r_in * SS, c + r_in * SS, c + r_in * SS), fill=0)
    return _down(im, size, size)


@functools.lru_cache(None)
def cross_mask(size, arm=0.32, rad=0.08):
    im, d = _canvas(size, size)
    s = size * SS
    a = s * arm
    r = s * rad
    d.rounded_rectangle((s / 2 - a / 2, s * 0.08, s / 2 + a / 2, s * 0.92), radius=r, fill=255)
    d.rounded_rectangle((s * 0.08, s / 2 - a / 2, s * 0.92, s / 2 + a / 2), radius=r, fill=255)
    return _down(im, size, size)


@functools.lru_cache(None)
def star_mask(size, points=5, inner=0.45):
    im, d = _canvas(size, size)
    c = size * SS / 2
    R = c * 0.95
    pts = []
    for i in range(points * 2):
        ang = -math.pi / 2 + i * math.pi / points
        r = R if i % 2 == 0 else R * inner
        pts.append((c + r * math.cos(ang), c + r * math.sin(ang)))
    d.polygon(pts, fill=255)
    return _down(im, size, size)


@functools.lru_cache(None)
def scallop_mask(size, bumps=24, depth=0.06):
    im, d = _canvas(size, size)
    c = size * SS / 2
    R = c * 0.94
    pts = []
    n = 720
    for i in range(n):
        ang = 2 * math.pi * i / n
        r = R * (1 - depth * (0.5 - 0.5 * math.cos(bumps * ang)))
        pts.append((c + r * math.cos(ang), c + r * math.sin(ang)))
    d.polygon(pts, fill=255)
    return _down(im, size, size)


@functools.lru_cache(None)
def person_mask(w, h, kind="man"):
    """Stylised person silhouette (head + shoulders/body)."""
    im, d = _canvas(w, h)
    s = SS
    hr = w * 0.22
    cx = w / 2
    if kind == "woman":  # head + hijab drape
        d.ellipse(((cx - hr * 1.08) * s, (h * 0.02) * s, (cx + hr * 1.08) * s, (h * 0.02 + hr * 2.25) * s), fill=255)
        d.polygon([((cx - hr * 1.05) * s, (h * 0.2) * s), ((cx + hr * 1.05) * s, (h * 0.2) * s),
                   ((cx + w * 0.36) * s, (h * 0.48) * s), ((cx - w * 0.36) * s, (h * 0.48) * s)], fill=255)
        top = h * 0.5
    else:
        d.ellipse(((cx - hr) * s, (h * 0.03) * s, (cx + hr) * s, (h * 0.03 + hr * 2) * s), fill=255)
        top = h * 0.03 + hr * 2 + h * 0.04
    d.rounded_rectangle(((cx - w * 0.46) * s, top * s, (cx + w * 0.46) * s, (h + w * 0.3) * s),
                        radius=w * 0.34 * s, fill=255)
    out = _down(im, w, h)
    return out


# ----------------------------------------------------------------- 3D objects
@functools.lru_cache(maxsize=256)
def shield_obj(w, h, lq, emblem="check"):
    """Gold shield with navy enamel and raised emblem. lq: quantised light x (-10..10)."""
    lx = lq / 10.0
    light = (lx, -0.75)
    outer = shield_mask(w, h, 0.0)
    inner = shield_mask(w, h, 0.085)
    img = relief(outer, bevel=w * 0.07, mat="gold", light=light, sheen=0.4)
    enamel = relief(inner, bevel=w * 0.03, mat="navy", light=light, sheen=0.25)
    img.alpha_composite(enamel)
    img.alpha_composite(inner_shadow(inner, radius=int(w * 0.03) + 2, offset=(int(w * 0.012), int(w * 0.025))))
    # inner thin gold line
    inner2 = shield_mask(w, h, 0.115)
    line = ImageChops.subtract(inner2, shield_mask(w, h, 0.125))
    img.alpha_composite(with_alpha(gradient_fill(line, GOLD_TEXT), 0.8))
    if emblem == "check":
        em = check_mask(w, h, w * 0.5, h * 0.47, w * 0.52, w * 0.11)
    elif emblem == "star":
        em = Image.new("L", (w, h), 0)
        st = star_mask(int(w * 0.46))
        em.paste(st, (int(w * 0.27), int(h * 0.3)))
    else:
        em = None
    if em is not None:
        emr = relief(em, bevel=w * 0.03, mat="gold", light=light, sheen=0.5)
        sh = colorize(em.filter(ImageFilter.GaussianBlur(w * 0.02)), (0, 0, 0))
        sh = with_alpha(sh, 0.7)
        img.alpha_composite(sh, (int(w * 0.01), int(w * 0.025)))
        img.alpha_composite(emr)
    return img


@functools.lru_cache(maxsize=128)
def coin_obj(size, lq):
    light = (lq / 10.0, -0.7)
    img = relief(circle_mask(size), bevel=size * 0.07, mat="gold", light=light, sheen=0.45)
    ring = ring_mask(size, size * 0.40, size * 0.36)
    img.alpha_composite(relief(ring, bevel=size * 0.02, mat="gold", light=(-light[0], 0.6), sheen=0.0))
    m, _ = text_mask("RM", font("Montserrat", int(size * 0.3), 800))
    tm = Image.new("L", (size, size), 0)
    tm.paste(m, ((size - m.width) // 2, (size - m.height) // 2 - int(size * 0.02)))
    sh = with_alpha(colorize(tm.filter(ImageFilter.GaussianBlur(2)), (60, 36, 6)), 0.8)
    img.alpha_composite(sh, (2, 3))
    img.alpha_composite(relief(tm, bevel=size * 0.02, mat="gold", light=light, sheen=0.3))
    return img


@functools.lru_cache(maxsize=128)
def medal_obj(size, lq):
    light = (lq / 10.0, -0.75)
    img = relief(scallop_mask(size), bevel=size * 0.05, mat="gold", light=light, sheen=0.4)
    inner = circle_mask(size, int(size * 0.15))
    img.alpha_composite(relief(inner, bevel=size * 0.03, mat="navy", light=light, sheen=0.2))
    img.alpha_composite(inner_shadow(inner, 5, (2, 4)))
    st = Image.new("L", (size, size), 0)
    s2 = int(size * 0.44)
    st.paste(star_mask(s2), ((size - s2) // 2, (size - s2) // 2 - int(size * 0.01)))
    img.alpha_composite(with_alpha(colorize(st.filter(ImageFilter.GaussianBlur(3)), (0, 0, 0)), 0.6), (2, 4))
    img.alpha_composite(relief(st, bevel=size * 0.04, mat="gold", light=light, sheen=0.5))
    return img


@functools.lru_cache(maxsize=128)
def medic_badge(size, lq):
    light = (lq / 10.0, -0.75)
    img = relief(circle_mask(size), bevel=size * 0.06, mat="gold", light=light, sheen=0.45)
    inner = circle_mask(size, int(size * 0.09))
    img.alpha_composite(relief(inner, bevel=size * 0.03, mat="navy", light=light, sheen=0.2))
    img.alpha_composite(inner_shadow(inner, 5, (2, 4)))
    cs = int(size * 0.5)
    cm = Image.new("L", (size, size), 0)
    cm.paste(cross_mask(cs), ((size - cs) // 2, (size - cs) // 2))
    img.alpha_composite(with_alpha(colorize(cm.filter(ImageFilter.GaussianBlur(4)), (0, 0, 0)), 0.7), (2, 5))
    img.alpha_composite(relief(cm, bevel=size * 0.05, mat="pearl", light=light, sheen=0.35))
    return img


@functools.lru_cache(maxsize=64)
def person_obj(w, h, kind, mat, lq):
    return relief(person_mask(w, h, kind), bevel=w * 0.12, mat=mat, light=(lq / 10.0, -0.7), sheen=0.3)


# ----------------------------------------------------------------- holographic panel
@functools.lru_cache(maxsize=32)
def _rr_mask(w, h, r):
    im, d = _canvas(w, h)
    d.rounded_rectangle((0, 0, w * SS - 1, h * SS - 1), radius=r * SS, fill=255)
    return _down(im, w, h)


@functools.lru_cache(maxsize=32)
def _panel_chrome(w, h, r):
    """Border, sheen and corner brackets for a panel (RGBA)."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    # sheen: diagonal white gradient top-left
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    sheen = np.clip(1 - (xx / w * 0.7 + yy / h), 0, 1) ** 2 * 26
    top = np.exp(-yy / 3.0) * 40
    al = np.clip(sheen + top, 0, 255)
    sh = np.dstack([np.full((h, w, 3), 255, np.float32), al]).astype(np.uint8)
    im.alpha_composite(Image.fromarray(sh, "RGBA"))
    # border
    outer = _rr_mask(w, h, r)
    inner = Image.new("L", (w, h), 0)
    inner.paste(_rr_mask(w - 4, h - 4, r - 2), (2, 2))
    border = ImageChops.subtract(outer, inner)
    bg = gradient_fill(border, [(0, (250, 230, 170)), (0.5, (170, 130, 50)), (1, (232, 196, 110))])
    im.alpha_composite(with_alpha(bg, 0.85))
    # corner brackets
    d = ImageDraw.Draw(im)
    L, t, o = 34, 4, 10
    c = GOLD_L + (255,)
    for (x, y, sx, sy) in ((o, o, 1, 1), (w - o, o, -1, 1), (o, h - o, 1, -1), (w - o, h - o, -1, -1)):
        d.line([(x, y + sy * L), (x, y), (x + sx * L, y)], fill=c, width=t)
    # mask by rounded rect
    im.putalpha(ImageChops.multiply(im.getchannel("A"), outer))
    return im


def panel(frame, x, y, w, h, reveal=1.0, alpha=1.0, r=30, tint=0.84):
    """Frosted navy glass panel composited onto frame (RGBA). reveal: holographic unfold 0..1."""
    if reveal <= 0 or alpha <= 0:
        return
    w, h = int(w), int(h)
    p = clamp(reveal)
    if p < 0.35:
        k = ease_out_cubic(p / 0.35)
        lw = max(4, int(w * k))
        line = Image.new("RGBA", (lw, 4), GOLD_L + (255,))
        g, pad = glow(line, 10, GOLD, 1.4)
        paste(frame, g, x + w / 2 - g.width / 2, y + h / 2 - g.height / 2, alpha)
        paste(frame, line, x + w / 2 - lw / 2, y + h / 2 - 2, alpha)
        return
    k = ease_out_cubic((p - 0.35) / 0.65)
    ch = max(6, int(h * k))
    cy = int(y + h / 2 - ch / 2)
    box = (int(x), cy, int(x) + w, cy + ch)
    crop = frame.crop(box).convert("RGB").filter(ImageFilter.GaussianBlur(22))
    arr = np.asarray(crop, np.float32)
    nav = np.array(NAVY, np.float32)
    arr = arr * (1 - tint) + nav * tint
    # vertical gradient: slightly lighter at top
    gy = np.linspace(1.12, 0.92, ch)[:, None, None]
    arr = np.clip(arr * gy, 0, 255)
    glass = Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")
    m = _rr_mask(w, ch, min(r, ch // 2))
    glass.putalpha(m)
    chrome = _panel_chrome(w, ch, min(r, ch // 2)) if ch > 2 * r else None
    if chrome is not None:
        glass.alpha_composite(chrome)
    # drop shadow (soft)
    sh = colorize(m.filter(ImageFilter.GaussianBlur(0)), (0, 0, 0))
    shb, pad = glow(sh, 24, (0, 0, 0), 0.6)
    paste(frame, shb, box[0] - pad, box[1] - pad + 14, alpha * 0.8)
    paste(frame, glass, box[0], box[1], alpha)
    if p < 1:  # scan line during unfold
        line = Image.new("RGBA", (w - 20, 3), GOLD_L + (255,))
        g, pad = glow(line, 8, GOLD, 1.2)
        for yy in (box[1], box[3] - 3):
            paste(frame, g, x + 10 - pad, yy - pad, alpha * (1 - k))
            paste(frame, line, x + 10, yy, alpha * (1 - k))


def pill(w, h, fill=(10, 26, 62, 235), border=GOLD, bw=2):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    m = _rr_mask(w, h, h // 2)
    body = Image.new("RGBA", (w, h), fill)
    body.putalpha(ImageChops.multiply(m, Image.new("L", (w, h), fill[3])))
    im.alpha_composite(body)
    inner = Image.new("L", (w, h), 0)
    inner.paste(_rr_mask(w - bw * 2, h - bw * 2, h // 2 - bw), (bw, bw))
    br = ImageChops.subtract(m, inner)
    im.alpha_composite(gradient_fill(br, [(0, (250, 230, 170)), (0.5, border), (1, (190, 145, 60))]))
    return im


def stagger_text(frame, text, fnt, x, y, t, t0, fill="white", tracking=0, per=0.035, dur=0.45,
                 rise=34, alpha=1.0, anchor="l", color=WHITE):
    """Per-glyph rise-in reveal. Returns text width."""
    m, boxes = text_mask(text, fnt, tracking)
    if fill == "gold":
        full = gradient_fill(m, GOLD_TEXT)
    else:
        full = colorize(m, color)
    if anchor == "m":
        x = x - m.width / 2
    n = len(text)
    if t >= t0 + per * n + dur:
        paste(frame, full, x, y, alpha)
        return m.width
    for i, (x0, x1) in enumerate(boxes):
        if text[i] == " ":
            continue
        p = prog(t, t0 + i * per, dur)
        if p <= 0:
            continue
        e = ease_out_cubic(p)
        a = int(max(0, x0 - 6))
        b = int(min(m.width, x1 + 8))
        g = full.crop((a, 0, b, m.height))
        paste(frame, g, x + a, y + (1 - e) * rise, alpha * min(1, p * 1.6))
    return m.width
