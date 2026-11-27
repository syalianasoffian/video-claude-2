"""Soundtrack: isolated original voice (demucs) delayed by the 1 s cover + synthesized
corporate-cinematic music bed (ducked under voice) + transition SFX. -> build/mc/mix.wav"""
import os, subprocess, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "build", "mc")
SR, DUR, COVER = 48000, 31.0, 1.0
N = int(DUR * SR)
rng = np.random.default_rng(3)
t_all = np.arange(N) / SR


def read(path):
    tmp = os.path.join(B, "_v.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-af",
                    "highpass=f=75,equalizer=f=210:t=o:w=1.2:g=2.5,equalizer=f=3400:t=o:w=1.4:g=-3,"
                    "equalizer=f=6800:t=q:w=2:g=-3.5,highshelf=f=11000:g=-2.5,deesser=i=0.4,"
                    "acompressor=threshold=-22dB:ratio=2:attack=12:release=160:knee=6,"
                    "aecho=0.85:0.6:19|31|47:0.13|0.09|0.05,loudnorm=I=-15:TP=-1.5:LRA=9",
                    "-ac", "1", "-ar", str(SR), tmp], check=True)
    w = wave.open(tmp)
    return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def lp1(x, fc):
    k = 1 - np.exp(-2 * np.pi * fc / SR)
    from scipy.signal import lfilter
    return lfilter([k], [1, -(1 - k)], x)


def midi(n): return 440 * 2 ** ((n - 69) / 12)


def adsr(n, a=.01, r=.3):
    e = np.ones(n); ai, ri = int(a * SR), int(r * SR)
    if ai: e[:ai] = np.linspace(0, 1, ai)
    if ri: e[-ri:] *= np.linspace(1, 0, ri)
    return e


def place(buf, x, t, g=1.0):
    i = int(t * SR)
    if i >= len(buf): return
    x = x[: len(buf) - i]; buf[i:i + len(x)] += x * g


# ---------- music ----------
BPM = 96; beat = 60 / BPM; bar = 4 * beat
# Dmaj9 - Bm9 - Gmaj7 - A6/9 (two bars each)
chords = [[50, 57, 61, 64, 66], [47, 54, 57, 61, 64], [43, 50, 54, 57, 62], [45, 52, 57, 61, 64]]
pad = np.zeros(N); pluck = np.zeros(N); bass = np.zeros(N); drums = np.zeros(N)
for ci in range(int(DUR / (2 * bar)) + 1):
    ch = chords[ci % 4]; t0 = ci * 2 * bar; n = int(2 * bar * SR) + int(.6 * SR)
    tt = np.arange(n) / SR
    y = np.zeros(n)
    for m in ch:
        for det in (-.07, .07):
            f = midi(m + 12) * 2 ** (det / 12)
            y += np.sin(2 * np.pi * f * tt + np.sin(2 * np.pi * .3 * tt)) * .5 + np.sin(4 * np.pi * f * tt) * .12
    place(pad, y * adsr(n, .8, .9) / len(ch), t0)
    bn = int(2 * bar * SR); bt = np.arange(bn) / SR
    place(bass, np.sin(2 * np.pi * midi(ch[0] - 12) * bt) * adsr(bn, .02, .3), t0)
    # arpeggio 8ths
    arp = [ch[1] + 12, ch[2] + 12, ch[3] + 12, ch[4] + 12, ch[3] + 12, ch[2] + 12, ch[4] + 12, ch[3] + 24]
    for k in range(16):
        nt = t0 + k * beat / 2; ln = int(.7 * SR); tt2 = np.arange(ln) / SR; f = midi(arp[k % 8])
        y = (np.sin(2 * np.pi * f * tt2) + .3 * np.sin(4 * np.pi * f * tt2) + .1 * np.sin(6 * np.pi * f * tt2)) * np.exp(-tt2 * 6)
        place(pluck, y * (.8 if k % 2 == 0 else .55), nt)
# drums start after cover
kick_len = int(.35 * SR); kt = np.arange(kick_len) / SR
kick = np.sin(2 * np.pi * np.cumsum(50 + 90 * np.exp(-kt * 30)) / SR) * np.exp(-kt * 9)
hat_len = int(.08 * SR); hat = rng.standard_normal(hat_len) * np.exp(-np.arange(hat_len) / SR * 60)
hat = hat - lp1(hat, 6000)
b = COVER
while b < DUR - .3:
    i = round((b - COVER) / beat)
    if i % 2 == 0: place(drums, kick, b, .8)
    place(drums, hat, b + beat / 2, .25)
    b += beat
music = .32 * pad + .22 * pluck + .35 * bass + drums
music = lp1(music, 9000)

# ---------- voice + ducking ----------
voice = np.zeros(N)
v = read(os.path.join(B, "sep/htdemucs/orig/vocals.wav"))
place(voice, v, COVER)
envv = np.abs(voice); envv = lp1(lp1(envv, 6), 6); envv /= envv.max()
duck = 1 - .55 * np.clip(envv * 6, 0, 1)
fade = np.clip(t_all / .05, 0, 1) * np.clip((DUR - t_all) / 1.5, 0, 1)
music *= duck * fade

# ---------- sfx ----------
sfx = np.zeros(N)
def whoosh(d=.7):
    n = int(d * SR); tt = np.linspace(0, 1, n); x = rng.standard_normal(n)
    y = lp1(x, 2500) - lp1(x, 300); return y * np.sin(np.pi * tt) ** 2 * 1.4
def shimmer(d=1.2):
    n = int(d * SR); tt = np.arange(n) / SR; y = np.zeros(n)
    for f in (1568, 2093, 2637, 3136):
        y += np.sin(2 * np.pi * f * tt) * np.exp(-tt * (3 + f / 1500))
    return y * .25
def impact(d=1.6):
    n = int(d * SR); tt = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(40 + 60 * np.exp(-tt * 12)) / SR) * np.exp(-tt * 3)
    return boom + lp1(rng.standard_normal(n), 1200) * np.exp(-tt * 8) * .4
def riser(d=.9):
    n = int(d * SR); tt = np.linspace(0, 1, n); x = rng.standard_normal(n)
    h = x - lp1(x, 2500); return h * tt ** 2 * .5

place(sfx, impact(), 0.0, .7)
place(sfx, shimmer(), 0.05, .6)
place(sfx, riser(), .15, .6)
for c in [COVER, 11.0, 15.95, 18.0, 21.0]:
    place(sfx, whoosh(), c - .35, .5)
for c in [5.64, 8.28, 14.46, 26.06, 29.24]:
    place(sfx, shimmer(), c, .45)

mix = voice * .95 + music * .2 + sfx * .35
mix = mix / max(1e-6, np.abs(mix).max()) * .89
st = np.stack([mix, mix], 1)
out = os.path.join(B, "mix.wav")
with wave.open(out, "w") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print("wrote", out)
