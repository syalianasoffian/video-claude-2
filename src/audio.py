"""Builds the soundtrack: original voice clips + synthesized ambient bed + SFX.
Output: build/mix.wav (48 kHz stereo)."""
import json, os, subprocess, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "build")
SR = 48000
rng = np.random.default_rng(7)


def load_voice():
    """Cleaned mono voice track of the whole original at SR."""
    path = os.path.join(B, "voice_clean.wav")
    if not os.path.exists(path):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(B, "original.mp4"),
                        "-af", "highpass=f=80,lowpass=f=12000,afftdn=nf=-25,"
                               "acompressor=threshold=-20dB:ratio=3:attack=5:release=80,"
                               "loudnorm=I=-15:TP=-1.5:LRA=7",
                        "-ac", "1", "-ar", str(SR), path], check=True)
    w = wave.open(path)
    return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def env(n, a, r):
    e = np.ones(n)
    a, r = int(a * SR), int(r * SR)
    if a: e[:a] = np.linspace(0, 1, a)
    if r: e[-r:] *= np.linspace(1, 0, r)
    return e


def lp(x, cutoff):
    """one-pole lowpass (cutoff may be an array)"""
    c = np.broadcast_to(np.asarray(cutoff, float), x.shape)
    k = 1 - np.exp(-2 * np.pi * c / SR)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += k[i] * (x[i] - acc); y[i] = acc
    return y


def whoosh(d=0.6, up=True):
    n = int(d * SR); t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    cut = (300 + 5000 * (t if up else 1 - t) ** 1.5)
    y = lp(noise, cut) - lp(noise, cut * 0.25)
    shape = np.sin(np.pi * t) ** 2
    return y * shape * 0.9


def pop(f=900, d=0.12):
    n = int(d * SR); t = np.arange(n) / SR
    fr = f * (1 + 0.6 * np.exp(-t * 60))
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 35) * 0.5


def ding(f=1320, d=0.9):
    n = int(d * SR); t = np.arange(n) / SR
    y = sum(np.sin(2 * np.pi * f * m * t) * a for m, a in [(1, 1), (2.01, .35), (3.02, .12)])
    return y * np.exp(-t * 6) * 0.25


def boom(d=1.2, f=52):
    n = int(d * SR); t = np.arange(n) / SR
    fr = f * (1 + 1.5 * np.exp(-t * 18))
    y = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 3.2)
    y += lp(rng.standard_normal(n), 900) * np.exp(-t * 14) * 0.8
    return y * 0.9


def riser(d=1.0):
    n = int(d * SR); t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    y = (lp(noise, 400 + 7000 * t ** 2) - lp(noise, 200 + 1500 * t ** 2)) * t ** 2
    y += np.sin(2 * np.pi * np.cumsum(220 + 660 * t ** 2) / SR) * t ** 3 * 0.25
    return y * 0.8


def shimmer(d=2.4, base=880):
    n = int(d * SR); t = np.arange(n) / SR
    y = np.zeros(n)
    for k, f in enumerate([base, base * 1.25, base * 1.5, base * 2, base * 2.5]):
        y += np.sin(2 * np.pi * f * t + k) * np.exp(-t * (1.6 + 0.4 * k)) * (0.9 ** k)
    return y * env(n, 0.01, 0.3) * 0.16


def thud(d=0.5):
    n = int(d * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * np.cumsum(90 * (1 + np.exp(-t * 25))) / SR) * np.exp(-t * 9)
    y += lp(rng.standard_normal(n), 2500) * np.exp(-t * 40) * 0.5
    return y * 0.7


def rumble(d=3.0):
    n = int(d * SR); t = np.linspace(0, 1, n)
    y = lp(rng.standard_normal(n), 140) * 6
    y *= (0.6 + 0.4 * np.sin(2 * np.pi * 3 * t * d)) * np.sin(np.pi * t)
    return y * 0.6


def coin(f=2600):
    n = int(0.25 * SR); t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * f * t) + 0.6 * np.sin(2 * np.pi * f * 1.5 * t)) * np.exp(-t * 22)
    return y * 0.16


def music(total):
    """Soft ambient tech bed: Dmaj9 / Bm9 / Gmaj7 / A pads + muted pulse."""
    n = int(total * SR); t = np.arange(n) / SR
    out = np.zeros((n, 2))
    bpm = 104; beat = 60 / bpm; bar = beat * 4
    chords = [[146.8, 220.0, 277.2, 329.6, 370.0], [123.5, 185.0, 293.7, 277.2, 370.0],
              [98.0, 196.0, 246.9, 293.7, 370.0], [110.0, 220.0, 277.2, 329.6, 440.0]]
    seg = bar * 2
    for i in range(int(total / seg) + 1):
        s0 = int(i * seg * SR); s1 = min(n, int((i + 1) * seg * SR + 0.5 * SR))
        if s0 >= n: break
        tt = np.arange(s1 - s0) / SR
        e = env(s1 - s0, 0.5, 0.6)
        for j, f in enumerate(chords[i % 4]):
            for det, pan in [(-0.12, 0.25), (0.12, 0.75)]:
                v = np.sin(2 * np.pi * (f + det) * tt + j) * 0.5 + np.sin(2 * np.pi * (f + det) * 2 * tt) * 0.08
                out[s0:s1, 0] += v * e * (1 - pan) * 0.05
                out[s0:s1, 1] += v * e * pan * 0.05
    # pulse: soft kick + hat
    k = 0
    while k * beat < total:
        s0 = int(k * beat * SR)
        kk = boom(0.35, 48) * 0.45
        hh = lp(rng.standard_normal(int(0.05 * SR)), 9000) * np.exp(-np.arange(int(0.05 * SR)) / SR * 90) * 0.06
        for arr, off in [(kk, 0), (hh, int(beat / 2 * SR))]:
            a = s0 + off; b = min(n, a + len(arr))
            if a < n:
                out[a:b] += arr[:b - a, None]
        k += 1
    # arp sparkle
    notes = [587.3, 740.0, 880.0, 1108.7]
    for k in range(int(total / (beat / 2))):
        if k % 3 == 2: continue
        s0 = int(k * beat / 2 * SR)
        p = pop(notes[k % 4], 0.25) * 0.12
        b = min(n, s0 + len(p))
        out[s0:b, k % 2] += p[:b - s0]
    return out


def main():
    tl = json.load(open(os.path.join(B, "timeline.json")))
    total = tl["duration"]; n = int(total * SR)
    voice_src = load_voice()
    voice = np.zeros(n)
    for c in tl["clips"]:
        a, b = int(c["src_start"] * SR), int(c["src_end"] * SR)
        seg = voice_src[a:b] * env(b - a, 0.02, 0.05)
        o = int(c["out_start"] * SR)
        voice[o:o + len(seg)] += seg

    sfx = np.zeros((n, 2))

    def put(sig, t, gain=1.0, pan=0.5):
        o = int(t * SR); m = min(len(sig), n - o)
        if m <= 0: return
        sfx[o:o + m, 0] += sig[:m] * gain * (1 - pan) * 2 ** 0.5
        sfx[o:o + m, 1] += sig[:m] * gain * pan * 2 ** 0.5

    put(whoosh(0.7), 0.0, 0.5); put(shimmer(1.6, 1175), 0.25, 0.8)
    put(whoosh(0.6), 0.65, 0.45, 0.3)
    put(pop(700), 1.55, 0.8, 0.35); put(pop(880), 2.0, 0.8, 0.65)          # parents
    put(pop(1050), 3.2, 0.8, 0.45)                                        # ketua keluarga chip
    put(whoosh(0.5), 4.6, 0.45, 0.7); put(boom(0.9, 60), 5.0, 0.55)        # house lands
    put(ding(1320), 5.35, 0.7)
    for i in range(9): put(coin(2400 + 180 * (i % 3)), 6.1 + i * 0.2, 0.9, 0.3 + 0.05 * i)
    put(whoosh(0.6), 7.95, 0.5, 0.3); put(boom(0.8, 70), 8.35, 0.4); put(ding(1568), 8.5, 0.55)
    put(pop(990), 10.2, 0.7)
    put(whoosh(0.6, False), 11.5, 0.5, 0.6); put(rumble(4.6), 11.8, 0.55)
    for i, tt in enumerate([12.4, 13.1, 13.8, 14.5]): put(pop(620 - 40 * i, 0.16), tt, 0.9, 0.2 + 0.2 * i)
    put(thud(), 15.4, 0.6, 0.3); put(thud(), 15.8, 0.6, 0.7)
    put(riser(1.0), 15.75, 0.55)
    put(boom(1.4, 46), 16.75, 0.8); put(shimmer(2.6, 880), 16.78, 1.0)
    put(whoosh(0.5), 17.3, 0.4, 0.2); put(whoosh(0.5), 17.45, 0.4, 0.8)
    for i, tt in enumerate([19.0, 19.55, 20.1]): put(ding(1046 * 1.122 ** i, 0.7), tt, 0.7, 0.3 + 0.2 * i)
    for i, tt in enumerate([21.2, 21.5, 21.8, 22.1]): put(thud(0.4), tt, 0.55, 0.3 + 0.13 * i)
    put(shimmer(2.0, 1175), 24.75, 0.8)
    put(whoosh(0.7), 26.35, 0.55); put(boom(1.2, 55), 26.75, 0.45); put(shimmer(2.2, 1318), 26.8, 0.9)

    mus = music(total)
    # sidechain-style ducking under voice
    venv = np.abs(voice)
    k = int(0.15 * SR)
    venv = np.convolve(venv, np.ones(k) / k, mode="same")
    duck = 1 - 0.55 * np.clip(venv / 0.05, 0, 1)
    fade = env(n, 0.4, 1.6)
    mix = voice[:, None] * 1.0 + sfx * 0.55 + mus * (duck * fade)[:, None] * 0.9
    peak = np.max(np.abs(mix))
    mix = mix / peak * 0.89
    w = wave.open(os.path.join(B, "mix.wav"), "w")
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
    print("mix written", total, "s, peak", peak)


if __name__ == "__main__":
    main()
