"""Layered, synthesized sound-design kit (48 kHz stereo).
Every sound is built from several layers (transient + body + tail) and runs
through a stereo convolution reverb so it sits like a produced SFX, not a beep."""
import numpy as np
from scipy.signal import fftconvolve, butter, sosfilt

SR = 48000
_rng = np.random.default_rng(11)


def T(d):
    return np.arange(int(d * SR)) / SR


def noise(d):
    return _rng.standard_normal(int(d * SR))


def bp(x, lo, hi, order=2):
    sos = butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return sosfilt(sos, x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, btype="low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, btype="high", fs=SR, output="sos"), x)


def sweep_filter(x, f0, f1, kind="low", steps=48, curve=1.0):
    """time-varying filter by crossfading blocks"""
    n = len(x); out = np.zeros(n); blk = n // steps + 1
    for i in range(steps):
        a, b = i * blk, min(n, (i + 1) * blk + 256)
        if a >= n: break
        u = (i / (steps - 1)) ** curve
        f = f0 * (f1 / f0) ** u
        f = min(max(f, 30), SR / 2 - 500)
        y = sosfilt(butter(2, f, btype=kind, fs=SR, output="sos"), x[max(0, a - 2048):b])[min(a, 2048):]
        w = np.ones(b - a); fade = min(256, b - a)
        w[-fade:] = np.linspace(1, 0, fade) if b < n else 1
        if i: w[:256] = np.linspace(0, 1, 256)
        out[a:b] += y[:b - a] * w
    return out


def adsr(n, a=0.005, d=0.1, s=0.0, r=0.05):
    e = np.zeros(n); A, D, R = int(a * SR), int(d * SR), int(r * SR)
    A = max(1, min(A, n)); e[:A] = np.linspace(0, 1, A)
    D = min(D, n - A); e[A:A + D] = np.linspace(1, s, D)
    e[A + D:] = s
    if R and s > 0: e[-R:] *= np.linspace(1, 0, R)
    return e


def expdec(d, k):
    return np.exp(-T(d) * k)


def stereo(x, pan=0.0, width=0.0):
    """pan -1..1 ; width adds a short Haas delay to one side"""
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    L, R = x * l, x * r
    if width:
        dl = int(width * 0.012 * SR); R = np.concatenate([np.zeros(dl), R])[:len(x)]
    return np.stack([L, R], 1)


def _ir(dur, decay, bright):
    n = int(dur * SR); t = np.arange(n) / SR
    out = []
    for s in (1, 2):
        g = np.random.default_rng(s).standard_normal(n) * np.exp(-t * decay)
        g = lp(g, bright); g[:int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
        out.append(g / np.sqrt(np.sum(g ** 2)))
    return np.stack(out, 1)


IR_HALL = _ir(2.6, 2.4, 7000)
IR_ROOM = _ir(0.7, 9.0, 9000)


def reverb(st, ir=IR_HALL, wet=0.25):
    n = len(st) + len(ir)
    out = np.zeros((n, 2)); out[:len(st)] += st * (1 - wet * 0.5)
    for c in range(2):
        cv = fftconvolve(st[:, c], ir[:, c])[:n]
        out[:len(cv), c] += cv * wet
    # trim silent tail
    e = np.max(np.abs(out), 1); idx = np.where(e > 1e-4)[0]
    return out[:idx[-1] + 1] if len(idx) else out


def norm(x, peak=0.9):
    m = np.max(np.abs(x)); return x / m * peak if m else x


# ---------------------------------------------------------------- sounds

def whoosh(d=0.55, pan_from=-0.6, pan_to=0.6, bright=7000, wet=0.18):
    t = np.linspace(0, 1, int(d * SR))
    x = noise(d)
    body = sweep_filter(x, 300, bright, "low", curve=0.7) - 0.6 * sweep_filter(x, 120, bright * 0.3, "low")
    shape = np.sin(np.pi * np.clip(t * 1.15, 0, 1)) ** 2.2
    tone = np.sin(2 * np.pi * np.cumsum(180 + 420 * t) / SR) * 0.08
    y = (body + tone) * shape
    pan = pan_from + (pan_to - pan_from) * t
    st = np.stack([y * np.cos((pan + 1) * np.pi / 4), y * np.sin((pan + 1) * np.pi / 4)], 1)
    return norm(reverb(st, IR_HALL, wet), 0.8)


def swish(d=0.22):
    """short, airy, fast UI swipe"""
    t = np.linspace(0, 1, int(d * SR))
    y = hp(sweep_filter(noise(d), 1500, 12000, "low", 24), 900) * (np.sin(np.pi * t) ** 3)
    return norm(reverb(stereo(y, 0, 1), IR_ROOM, 0.2), 0.6)


def impact(d=1.6, sub=48, wet=0.3):
    t = T(d)
    s = np.sin(2 * np.pi * np.cumsum(sub * (1 + 2.2 * np.exp(-t * 22))) / SR) * np.exp(-t * 2.6)
    body = lp(noise(d), 1600) * np.exp(-t * 16) * 0.9
    click = hp(noise(0.012), 2500) * np.linspace(1, 0, int(0.012 * SR)) * 0.8
    crack = bp(noise(d), 2000, 7000) * np.exp(-t * 35) * 0.35
    y = s * 1.0 + body + crack
    y[:len(click)] += click
    y = np.tanh(y * 1.6)
    return norm(reverb(stereo(y, 0, 1), IR_HALL, wet), 0.95)


def sub_drop(d=1.4, f0=90, f1=32):
    t = T(d); f = f1 + (f0 - f1) * np.exp(-t * 3.5)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.8) * adsr(len(t), 0.01, 0, 1, 0.2)
    return norm(stereo(np.tanh(y * 1.4)), 0.9)


def riser(d=1.6, f0=200, f1=1400):
    t = np.linspace(0, 1, int(d * SR))
    x = noise(d)
    y = sweep_filter(x, 400, 12000, "low", curve=1.6) * t ** 2.2
    for det in (0, 0.007, -0.006):
        y += np.sign(np.sin(2 * np.pi * np.cumsum(f0 * (f1 / f0) ** (t ** 1.6) * (1 + det)) / SR)) * 0.05 * t ** 2.5
    y = lp(y, 9000) * np.minimum(1, (1 - t) * 40)
    return norm(reverb(stereo(y, 0, 1), IR_HALL, 0.25), 0.7)


def reverse_swell(d=1.1):
    """reverse-cymbal style swell into a hit"""
    t = T(d)
    y = hp(noise(d), 3000) * np.exp(-t * 4.0)
    y = y[::-1]
    return norm(reverb(stereo(y, 0, 1), IR_HALL, 0.3), 0.6)


def pop(f=820, d=0.14):
    t = T(d)
    fr = f * (1 + 0.9 * np.exp(-t * 70))
    y = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 38)
    y += hp(noise(d), 4000) * np.exp(-t * 300) * 0.25
    return norm(reverb(stereo(y), IR_ROOM, 0.15), 0.5)


def tick(f=3200):
    t = T(0.04)
    y = bp(noise(0.04), f * 0.7, f * 1.4) * np.exp(-t * 180)
    return norm(stereo(y), 0.35)


def chime(f=1318.5, d=2.2, wet=0.35):
    t = T(d)
    y = np.zeros(len(t))
    for m, a, k in [(1, 1, 3.0), (2.0, .45, 4.5), (3.01, .22, 6), (4.2, .12, 9), (5.43, .06, 12)]:
        y += np.sin(2 * np.pi * f * m * t) * a * np.exp(-t * k)
    y *= adsr(len(t), 0.002, 0, 1, 0.05)
    return norm(reverb(stereo(y, 0, 1), IR_HALL, wet), 0.45)


def sparkle(d=1.4, base=2093):
    out = np.zeros((int((d + 2.6) * SR), 2))
    notes = [1, 1.26, 1.5, 2, 2.52, 3]
    for i, m in enumerate(notes):
        c = chime(base * m / 2, 0.8, 0.0)[:, 0]
        o = int(i * 0.055 * SR)
        p = -0.7 + 1.4 * i / (len(notes) - 1)
        out[o:o + len(c)] += stereo(c, p) * (0.9 ** i)
    return norm(reverb(out[:int(d * SR) + int(0.9 * SR)], IR_HALL, 0.4), 0.4)


def stamp():
    """rubber stamp: low thump + paper slap + table rattle"""
    d = 0.6; t = T(d)
    th = np.sin(2 * np.pi * np.cumsum(120 * (1 + 1.2 * np.exp(-t * 40))) / SR) * np.exp(-t * 18)
    slap = bp(noise(d), 600, 5000) * np.exp(-t * 55) * 0.9
    rattle = bp(noise(d), 200, 900) * np.exp(-t * 14) * 0.25
    y = np.tanh((th + slap + rattle) * 1.8)
    return norm(reverb(stereo(y, 0, 1), IR_ROOM, 0.25), 0.9)


def paper_rip(d=0.5):
    t = np.linspace(0, 1, int(d * SR))
    x = noise(d)
    crack = (_rng.random(len(x)) < 0.012 + 0.03 * np.sin(np.pi * t)).astype(float) * _rng.standard_normal(len(x))
    crack = np.convolve(crack, np.exp(-np.arange(80) / 12), "same")
    y = bp(x, 1200, 9000) * 0.35 * np.sin(np.pi * t) + bp(crack, 800, 10000)
    return norm(reverb(stereo(y, -0.2, 1), IR_ROOM, 0.2), 0.6)


def printer(d=1.2, rate=26):
    """thermal receipt printer: buzzing stepper + paper feed"""
    t = T(d)
    step = (np.sin(2 * np.pi * rate * t) > 0.6).astype(float)
    step = np.convolve(step, np.ones(40) / 40, "same")
    whine = np.sin(2 * np.pi * 1850 * t) * 0.15 + np.sin(2 * np.pi * 925 * t) * 0.1
    y = bp(noise(d), 1500, 6000) * 0.4 * step + whine * step
    y *= adsr(len(t), 0.02, 0, 1, 0.06)
    return norm(reverb(stereo(y, 0.15, 1), IR_ROOM, 0.15), 0.4)


def cash(d=1.6):
    """register drawer clunk + bell"""
    out = np.zeros((int(d * SR) + SR * 3, 2))
    c = stamp() * 0.5; out[:len(c)] += c
    b = chime(2637, 1.4, 0.3); o = int(0.05 * SR); out[o:o + len(b)] += b * 1.2
    return out[:int(d * SR) + SR]


def heartbeat(bpm=72, beats=2):
    d = 60 / bpm; out = np.zeros(int(d * beats * SR) + SR)
    for i in range(beats):
        for off, g in [(0, 1.0), (0.22, 0.7)]:
            t = T(0.25)
            th = np.sin(2 * np.pi * np.cumsum(55 * (1 + 0.8 * np.exp(-t * 30))) / SR) * np.exp(-t * 16) * g
            o = int((i * d + off) * SR); out[o:o + len(th)] += th
    return norm(stereo(lp(np.tanh(out * 2), 300)), 0.9)


def glitch(d=0.45):
    t = T(d)
    base = np.sign(np.sin(2 * np.pi * 110 * t)) * 0.4 + noise(d) * 0.4
    gate = (np.floor(t * 38) % 3 != 1).astype(float)
    crush = np.round(base * 6) / 6
    y = hp(crush * gate, 200)
    y *= adsr(len(t), 0.002, 0, 1, 0.03)
    return norm(stereo(y, 0, 1), 0.5)


def alarm(d=1.2):
    t = T(d)
    f = np.where((t * 4).astype(int) % 2 == 0, 880, 660)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.6 + np.sin(2 * np.pi * np.cumsum(f * 2) / SR) * 0.15
    y *= adsr(len(t), 0.02, 0, 1, 0.2)
    return norm(reverb(stereo(lp(y, 3000)), IR_HALL, 0.3), 0.35)


def tap():
    t = T(0.08)
    y = bp(noise(0.08), 1000, 6000) * np.exp(-t * 120) + np.sin(2 * np.pi * 300 * t) * np.exp(-t * 60) * 0.6
    return norm(reverb(stereo(y), IR_ROOM, 0.15), 0.55)


def notif():
    out = np.zeros((int(2.5 * SR), 2))
    for i, f in enumerate([1568, 2093]):
        c = chime(f, 1.2, 0.0)[:, 0]; o = int(i * 0.11 * SR)
        out[o:o + len(c)] += stereo(c, 0)
    return norm(reverb(out, IR_HALL, 0.3), 0.45)
