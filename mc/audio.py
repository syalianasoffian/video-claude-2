"""Soundtrack for the Medical Card Premium edit.
Original voice (vocals stem if build/mc/vocals.wav exists, else the original track),
offset by the 1 s cover, + synthesized cinematic bed (low, ducked) + SFX.
Output: build/mc/mix.wav (48 kHz stereo)."""
import os, subprocess, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "build", "mc")
SR = 48000
COVER, DUR = 1.0, 31.6
N = int(DUR * SR)
rng = np.random.default_rng(3)


def read(path):
    w = wave.open(path)
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return a.reshape(-1, w.getnchannels()).mean(1)


def voice():
    src = os.path.join(B, "vocals.wav")
    if not os.path.exists(src): src = os.path.join(ROOT, "build", "original.mp4")
    out = os.path.join(B, "voice_proc.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
                    "highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=90,"
                    "equalizer=f=3200:t=q:w=1.2:g=2,loudnorm=I=-15:TP=-1.5:LRA=8",
                    "-ac", "1", "-ar", str(SR), out], check=True)
    return read(out)


def env(n, a, r):
    e = np.ones(n); a, r = int(a * SR), int(r * SR)
    if a: e[:a] = np.linspace(0, 1, a)
    if r: e[-r:] *= np.linspace(1, 0, r)
    return e


def fft_filter(x, lo=None, hi=None):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); g = np.ones_like(f)
    if lo: g *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi: g *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * g, len(x))


def put(buf, x, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= len(buf): return
    x = x[: len(buf) - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(x), 0] += x * gain * l * 1.41
    buf[i:i + len(x), 1] += x * gain * r * 1.41


# ---------------- music ----------------
def keys(f, d):
    """soft felt-piano-ish tone"""
    n = int(d * SR); t = np.arange(n) / SR
    y = sum(a * np.sin(2 * np.pi * f * m * t + m) * np.exp(-t * (1.8 + m * 1.1)) for m, a in [(1, 1), (2, .45), (3, .18), (4, .08)])
    return y * env(n, .004, .3)


def pad(freqs, d):
    n = int(d * SR); t = np.arange(n) / SR; y = np.zeros(n)
    for f in freqs:
        for det in (-.18, .18):
            y += np.sin(2 * np.pi * (f + det) * t + rng.random() * 6) * (1 + .3 * np.sin(2 * np.pi * .23 * t))
    return y / len(freqs) * env(n, 1.2, 1.2)


def music():
    out = np.zeros((N, 2))
    bpm = 88; beat = 60 / bpm; bar = beat * 4
    # Fmaj9 – Am7 – Dm9 – Bbmaj7(#11)  (warm, premium)
    prog = [[87.3, 174.6, 220.0, 261.6, 329.6, 392.0], [110.0, 164.8, 220.0, 261.6, 329.6, 392.0],
            [73.4, 146.8, 220.0, 261.6, 329.6, 349.2], [58.3, 116.5, 233.1, 293.7, 349.2, 440.0]]
    t0 = 1.0  # music proper begins with the video
    nb = int((DUR - t0) / bar) + 1
    for b in range(nb):
        ch = prog[b % 4]; s = t0 + b * bar
        p = pad(ch[1:5], bar + 1.5)
        put(out, p * .055, s, pan=-.2); put(out, p * .055, s + .013, pan=.2)
        # sub bass
        n = int(bar * SR); tt = np.arange(n) / SR
        put(out, np.sin(2 * np.pi * ch[0] * tt) * env(n, .05, .4) * .10, s)
        # arpeggio (eighths), from bar 1
        if b >= 1:
            pat = [ch[2], ch[3], ch[4], ch[5], ch[4], ch[3], ch[5], ch[4]]
            for k, f in enumerate(pat):
                put(out, keys(f * 2, beat * 1.6) * .05 * (1 if k % 2 == 0 else .7), s + k * beat / 2, pan=(-.35 if k % 2 else .35))
        # soft pulse: kick-ish on 1 and 3 from bar 2, shaker on off-beats
        if b >= 2:
            for k in range(4):
                n2 = int(.35 * SR); t2 = np.arange(n2) / SR
                if k % 2 == 0:
                    put(out, np.sin(2 * np.pi * np.cumsum(55 * (1 + 2 * np.exp(-t2 * 30))) / SR) * np.exp(-t2 * 9) * .14, s + k * beat)
                sh = fft_filter(rng.standard_normal(int(.08 * SR)), lo=6000) * np.exp(-np.arange(int(.08 * SR)) / SR * 45) * .025
                put(out, sh, s + k * beat + beat / 2, pan=.3)
    # ending: swell and fade
    fade = np.ones(N); i0 = int((DUR - 1.6) * SR); fade[i0:] = np.linspace(1, 0, N - i0) ** 1.5
    return out * fade[:, None]


# ---------------- sfx ----------------
def whoosh(d=.7):
    n = int(d * SR); t = np.linspace(0, 1, n)
    y = fft_filter(rng.standard_normal(n), lo=500, hi=7000) * np.sin(np.pi * t) ** 3
    return y * .5


def riser(d=1.0):
    n = int(d * SR); t = np.linspace(0, 1, n)
    y = fft_filter(rng.standard_normal(n), lo=1500, hi=12000) * t ** 3 * .6
    y += np.sin(2 * np.pi * np.cumsum(300 + 900 * t ** 2) / SR) * t ** 3 * .12
    return y


def impact(d=1.6):
    n = int(d * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * np.cumsum(48 * (1 + 1.4 * np.exp(-t * 16))) / SR) * np.exp(-t * 3)
    y += fft_filter(rng.standard_normal(n), hi=1800) * np.exp(-t * 12) * .5
    return y * .55


def shimmer(d=2.5, base=1046.5):
    n = int(d * SR); t = np.arange(n) / SR
    y = sum(np.sin(2 * np.pi * base * r * t + k) * np.exp(-t * (1.4 + .5 * k)) * .8 ** k for k, r in enumerate([1, 1.25, 1.5, 2, 2.5, 3]))
    return y * env(n, .01, .4) * .09


def coin(f=2700):
    n = int(.35 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + .5 * np.sin(2 * np.pi * f * 1.48 * t)) * np.exp(-t * 16) * .07


def tick():
    n = int(.06 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 90) * .06


def pop(f=700):
    n = int(.18 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(f * (1 + .8 * np.exp(-t * 50))) / SR) * np.exp(-t * 26) * .22


def main():
    v = voice()
    vo = np.zeros(N); i = int(COVER * SR); seg = v[: N - i]
    # keep voice through the last word (v 26.32), then fade out the original end-card tail
    tv = np.arange(len(seg)) / SR
    seg = seg * np.clip(1 - (tv - 26.45) / .5, 0, 1)
    vo[i:i + len(seg)] = seg

    mus = music()
    # sidechain-style duck under the voice
    e = np.abs(vo); k = int(.12 * SR); e = np.convolve(e, np.ones(k) / k, "same")
    duck = 1 - .55 * np.clip(e / .06, 0, 1)
    duck = np.convolve(duck, np.ones(int(.2 * SR)) / int(.2 * SR), "same")
    mus *= duck[:, None]
    # music a bit fuller on the cover and CTA (no voice)
    lift = np.ones(N); tt = np.arange(N) / SR
    lift += .7 * np.clip((tt - 27.5) / 1.0, 0, 1)
    mus *= lift[:, None]

    sfx = np.zeros((N, 2))
    put(sfx, riser(.95), .05, .8)
    put(sfx, impact(), 1.0, .9); put(sfx, shimmer(), 1.0, .8)
    V = lambda x: x + COVER
    for c in [3.5, 8.1, 11.7, 13.0, 14.5, 17.6, 22.8]:
        put(sfx, whoosh(.6), V(c) - .32, .45, pan=rng.uniform(-.4, .4))
    put(sfx, whoosh(.5), V(2.3), .5, .4)                    # card fly-in
    put(sfx, impact(1.2), V(3.62), .45)                      # shield
    for k in range(18): put(sfx, tick(), V(4.4 + k * .062), .8)  # counter
    put(sfx, shimmer(2.0, 1318.5), V(5.5), .9)
    put(sfx, impact(.9), V(7.96), .5)                        # TAK CLAIM punch
    for k in range(9): put(sfx, coin(2400 + rng.uniform(-300, 600)), V(10.12 + k * .055), .9, pan=rng.uniform(-.7, .7))
    put(sfx, shimmer(1.6, 1568), V(11.4), .7)
    for a in [13.85, 14.7, 15.62]: put(sfx, pop(820), V(a + .15), .8)
    put(sfx, whoosh(.5), V(14.45), .4)
    for a in [16.15]: put(sfx, coin(2600), V(a), 1.0)
    put(sfx, shimmer(1.8, 1174.7), V(19.0), .6)
    for k in range(15): put(sfx, tick(), V(20.75 + k * .035), .7)
    put(sfx, impact(.9), V(21.3), .35)
    for a in [23.0, 24.2, 25.62]: put(sfx, whoosh(.4), V(a) - .15, .35); put(sfx, pop(660), V(a + .05), .6)
    put(sfx, riser(.8), V(25.8), .5); put(sfx, impact(1.4), V(26.6), .7); put(sfx, shimmer(3.0), V(26.65), .9)
    put(sfx, pop(900), V(28.0), .9); put(sfx, shimmer(2.0, 1568), V(28.05), .6)

    mix = vo[:, None] * np.array([1.0, 1.0]) + mus * .72 + sfx
    # gentle master limiting
    peak = np.max(np.abs(mix)); mix = np.tanh(mix / max(peak, 1e-6) * 1.15) * .89
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    w = wave.open(os.path.join(B, "mix.wav"), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes()); w.close()
    print("wrote mix.wav", N / SR, "s")


if __name__ == "__main__":
    main()
