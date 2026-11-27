"""Renders the custom layered SFX into keyman/assets/sfx/*.wav (48 kHz stereo, -1 dBTP)."""
import os, sys
import numpy as np, soundfile as sf, librosa
sys.path.insert(0, os.path.dirname(__file__))
import sfxlib as S

OUT = "/home/user/work/keyman/assets/sfx"
SR = S.SR


def lib(name):
    y, _ = librosa.load(f"{OUT}/{name}", sr=SR, mono=False)
    y = np.atleast_2d(y)
    if y.shape[0] == 1: y = np.vstack([y, y])
    return y.T


def mix(*items, dur=None):
    """items: (stereo array, offset seconds, gain)"""
    n = max(int(o * SR) + len(a) for a, o, g in items)
    out = np.zeros((n, 2))
    for a, o, g in items:
        s = int(o * SR); out[s:s + len(a)] += a * g
    return out if dur is None else out[:int(dur * SR)]


def save(name, x, peak=0.89):
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    fade = int(0.01 * SR); x[-fade:] *= np.linspace(1, 0, fade)[:, None]
    sf.write(f"{OUT}/{name}", x.astype(np.float32), SR, subtype="PCM_24")
    print(name, round(len(x) / SR, 2))


def brush():
    """marker/highlighter stroke: dry felt-tip scrape"""
    d = 0.32; t = np.linspace(0, 1, int(d * SR))
    x = S.bp(S.noise(d), 1800, 9000) * (np.sin(np.pi * t) ** 0.8) * (0.7 + 0.3 * np.sin(2 * np.pi * 23 * t))
    return S.reverb(S.stereo(x, 0.1, 1), S.IR_ROOM, 0.15)


def pops10():
    out = np.zeros((int(1.2 * SR), 2))
    for i in range(10):
        p = S.pop(700 + 55 * i, 0.12); o = int(i * 0.05 * SR)
        out[o:o + len(p)] += S.stereo(p[:, 0], -0.6 + 1.2 * (i % 5) / 4) * 0.8
    return out


def clock():
    out = np.zeros((int(1.0 * SR), 2))
    for i in range(4):
        tk = S.tick(2600 if i % 2 else 3400); o = int(i * 0.22 * SR); out[o:o + len(tk)] += tk
    return out


def flip():
    out = np.zeros((int(2.6 * SR), 2))
    for i in range(11):
        o = int((0.04 + 1.6 * (i / 10) ** 1.2) * SR)
        f = S.paper_rip(0.07); out[o:o + len(f)] += f * 0.6
    return out


def pen():
    d = 0.6; t = np.linspace(0, 1, int(d * SR))
    x = S.bp(S.noise(d), 2500, 8000) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 7 * t))) * np.sin(np.pi * t) ** 0.5
    return S.stereo(x * 0.6, 0.15)


def chk():
    return mix((S.pop(1180, 0.1), 0, 0.7), (S.chime(2349, 0.5, 0.25), 0.01, 0.5))


def main():
    save("brush.wav", brush(), 0.6)
    save("stamp.wav", S.stamp(), 0.85)
    save("stamp_big.wav", mix((S.stamp(), 0, 1.0), (lib("impact-bass-1.mp3"), 0, 0.7), (S.sub_drop(1.2), 0, 0.5)), 0.95)
    save("tick.wav", S.tick(3000), 0.5)
    save("clock.wav", clock(), 0.5)
    save("riser_short.wav", S.riser(1.0), 0.7)
    save("pops10.wav", pops10(), 0.6)
    save("heartbeat.wav", S.heartbeat(76, 2), 0.95)
    save("printer.wav", S.printer(1.6), 0.55)
    save("flip.wav", flip(), 0.5)
    save("alarm.wav", S.alarm(1.5), 0.5)
    save("paper.wav", mix((S.whoosh(0.45, 0.4, -0.2, 5000, 0.1), 0, 0.6), (S.paper_rip(0.25), 0.2, 0.7)), 0.6)
    save("pen.wav", pen(), 0.45)
    save("reverse.wav", S.reverse_swell(1.0), 0.6)
    save("chk.wav", chk(), 0.55)


if __name__ == "__main__":
    main()
