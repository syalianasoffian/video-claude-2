"""Synthesise an original cinematic corporate score + SFX, synced to the edit's scene changes.

Usage: python3 music.py <music.wav> <sfx.wav>
"""
import sys
import numpy as np
from scipy import signal
import wave

SR = 48000
OFF = 1.5   # cover card before the video
DUR = 22.45 + OFF
N = int(SR * DUR)
t_all = np.arange(N) / SR
rng = np.random.default_rng(3)


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def write(path, x):
    x = np.clip(x, -1, 1)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def reverb(x, secs=2.2, mix=0.35, pre=0.02):
    n = int(SR * secs)
    tt = np.arange(n) / SR
    irL = rng.standard_normal(n) * np.exp(-tt * 6.9 / secs)
    irR = rng.standard_normal(n) * np.exp(-tt * 6.9 / secs)
    b, a = signal.butter(1, 5000 / (SR / 2))
    irL, irR = signal.lfilter(b, a, irL), signal.lfilter(b, a, irR)
    irL[: int(pre * SR)] = 0
    irR[: int(pre * SR)] = 0
    irL /= np.sqrt(np.sum(irL ** 2))
    irR /= np.sqrt(np.sum(irR ** 2))
    mono = x if x.ndim == 1 else x.mean(1)
    wl = signal.fftconvolve(mono, irL)[: len(mono)]
    wr = signal.fftconvolve(mono, irR)[: len(mono)]
    dry = np.stack([mono, mono], 1) if x.ndim == 1 else x
    return dry * (1 - mix) + np.stack([wl, wr], 1) * mix


# chord changes aligned to scene changes
CHORDS = [
    (0.0, [50, 62, 66, 69, 73, 76]),     # Dmaj9 (cover + opening)
    (4.95, [47, 59, 62, 66, 69, 73]),    # Bm9
    (9.85, [43, 55, 59, 62, 66, 73]),    # Gmaj7(#11-ish)
    (12.2, [40, 55, 59, 62, 66, 71]),    # Em9 / G
    (14.85, [45, 57, 62, 64, 69, 71]),   # Asus
    (17.65, [45, 57, 61, 64, 69, 73]),   # A (lift)
    (20.45, [38, 50, 62, 66, 69, 76, 81]),  # Dmaj9 resolve
]


CHORDS = [(0.0 if i == 0 else t + OFF, n) for i, (t, n) in enumerate(CHORDS)]


def chord_at(i):
    t0, notes = CHORDS[i]
    t1 = CHORDS[i + 1][0] if i + 1 < len(CHORDS) else DUR
    return t0, t1, notes


def pad():
    out = np.zeros((N, 2))
    for i in range(len(CHORDS)):
        t0, t1, notes = chord_at(i)
        a, b = int(max(0, t0 - 0.25) * SR), int(min(DUR, t1 + 0.6) * SR)
        tt = np.arange(b - a) / SR
        envl = np.minimum(1, tt / 0.5) * np.clip((t1 + 0.6 - t0 - tt) / 0.85, 0, 1)
        seg = np.zeros((b - a, 2))
        for m in notes[1:]:
            f = midi(m)
            for det, pan in ((-0.07, 0.2), (0.0, 0.5), (0.07, 0.8)):
                ff = f * 2 ** (det / 12)
                ph = rng.uniform(0, 6.28)
                v = np.zeros(b - a)
                for h in range(1, 9):
                    v += np.sin(2 * np.pi * ff * h * tt + ph * h) / h * np.exp(-h / 2.6)
                seg[:, 0] += v * (1 - pan)
                seg[:, 1] += v * pan
        lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.25 * tt)
        out[a:b] += seg * (envl * lfo)[:, None] * 0.05
    return out


def sub():
    out = np.zeros(N)
    beat = 60 / 90
    for i in range(len(CHORDS)):
        t0, t1, notes = chord_at(i)
        f = midi(notes[0] - 12 if notes[0] > 40 else notes[0])
        a, b = int(t0 * SR), int(t1 * SR)
        tt = np.arange(b - a) / SR
        pulse = 0.55 + 0.45 * np.exp(-((tt % beat) / 0.18))
        v = np.sin(2 * np.pi * f * tt) * pulse * np.minimum(1, tt / 0.05)
        if t0 >= 20.4 + OFF:
            v = np.sin(2 * np.pi * f * tt) * np.exp(-tt / 1.4)
        out[a:b] += v * 0.16
    return out


def pluck_arp():
    out = np.zeros((N, 2))
    step = 60 / 90 / 2
    t = 0.9 + OFF
    k = 0
    while t < 20.3 + OFF:
        i = max(j for j in range(len(CHORDS)) if CHORDS[j][0] <= t)
        notes = CHORDS[i][1][2:]
        m = notes[[0, 2, 1, 3, 2, 1, 3, 2][k % 8] % len(notes)] + 12
        f = midi(m)
        n = int(0.7 * SR)
        tt = np.arange(n) / SR
        v = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 9)) * np.exp(-tt * 5.5)
        v *= np.minimum(1, tt / 0.004)
        a = int(t * SR)
        b = min(N, a + n)
        pan = 0.5 + 0.3 * np.sin(k * 1.3)
        lvl = 0.05 if t < 4.95 + OFF else 0.065
        out[a:b, 0] += v[: b - a] * (1 - pan) * lvl
        out[a:b, 1] += v[: b - a] * pan * lvl
        t += step
        k += 1
    return out


def noise_hits():
    out = np.zeros(N)
    step = 60 / 90 / 2
    t = 4.95 + OFF + step
    hp = signal.butter(2, 7000 / (SR / 2), "high", output="sos")
    while t < 20.3 + OFF:
        n = int(0.06 * SR)
        v = signal.sosfilt(hp, rng.standard_normal(n)) * np.exp(-np.arange(n) / SR * 70)
        a = int(t * SR)
        out[a:a + n] += v * (0.035 if int(round((t - 4.95 - OFF) / step)) % 2 else 0.018)
        t += step
    return out


def bell(f, n_secs=2.5, lvl=0.2):
    n = int(n_secs * SR)
    tt = np.arange(n) / SR
    v = (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 2.2) + 0.45 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 4)
         + 0.25 * np.sin(2 * np.pi * f * 5.4 * tt) * np.exp(-tt * 7))
    return v * np.minimum(1, tt / 0.003) * lvl


def whoosh(dur=0.6, f0=300, f1=4000, lvl=0.25):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    x = rng.standard_normal(n)
    out = np.zeros(n)
    hop = 512
    for s in range(0, n, hop):
        p = s / n
        fc = f0 * (f1 / f0) ** p
        sos = signal.butter(2, [max(40, fc * 0.6) / (SR / 2), min(SR / 2 - 100, fc * 1.6) / (SR / 2)], "band",
                            output="sos")
        seg = signal.sosfilt(sos, x[max(0, s - 2048): s + hop])[-min(hop, n - s):]
        out[s: s + len(seg)] = seg
    envl = np.sin(np.pi * np.clip(tt / dur, 0, 1)) ** 2
    return out * envl * lvl


def riser(dur=1.6, lvl=0.18):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    w = whoosh(dur, 200, 6000, 1.0)
    envl = (tt / dur) ** 2.2
    tone = np.sin(2 * np.pi * (200 * tt + 400 * tt ** 2 / dur)) * 0.25
    return (w + tone) * envl * lvl


def impact(lvl=0.6):
    n = int(2.5 * SR)
    tt = np.arange(n) / SR
    f = 38 + 80 * np.exp(-tt * 18)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.4)
    lp = signal.butter(2, 1500 / (SR / 2), output="sos")
    crack = signal.sosfilt(lp, rng.standard_normal(n)) * np.exp(-tt * 25) * 0.4
    return (boom + crack) * lvl


def add(buf, x, t, gain=1.0):
    a = int(t * SR)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    b = min(len(buf), a + len(x))
    buf[a:b] += x[: b - a] * gain


def main(music_path, sfx_path):
    m = pad()
    m += np.stack([sub()] * 2, 1)
    m += pluck_arp()
    m += np.stack([noise_hits()] * 2, 1)
    m = reverb(m, 2.4, 0.3)
    # end resolve shimmer
    for k, mm in enumerate([74, 78, 81, 86]):
        add(m, reverb(bell(midi(mm), 3, 0.06), 3, 0.5), 20.5 + OFF + k * 0.12)
    # intro / outro fades
    fade = np.ones(N)
    fade[: int(0.03 * SR)] = np.linspace(0, 1, int(0.03 * SR))
    fade[-int(0.6 * SR):] = np.linspace(1, 0, int(0.6 * SR)) ** 1.5
    m *= fade[:, None]
    m /= np.max(np.abs(m)) + 1e-9
    write(music_path, m * 0.8)

    s = np.zeros((N, 2))
    # cover: impact + shimmer on frame 0, whoosh into the video
    add(s, impact(0.45), 0.0)
    for k, mm in enumerate([81, 86, 90]):
        add(s, bell(midi(mm), 1.6, 0.07), 0.05 + k * 0.08)
    add(s, whoosh(0.7, 250, 6000, 0.26), OFF - 0.55)
    for ts in (4.88, 9.78, 12.12, 14.8, 17.58):
        add(s, whoosh(0.6, 250, 5000, 0.22), ts + OFF)
    for ts, mm in ((0.88, 81), (5.5, 86), (6.86, 88), (9.14, 93), (11.36, 86), (13.3, 81), (16.76, 88), (19.66, 84)):
        add(s, bell(midi(mm), 2.0, 0.09), ts + OFF)
    add(s, riser(1.7, 0.16), 20.45 + OFF - 1.7)
    add(s, impact(0.55), 20.45 + OFF)
    s = reverb(s, 1.6, 0.25)
    write(sfx_path, s)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
