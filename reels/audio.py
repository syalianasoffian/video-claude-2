"""Mix: original narration (unchanged timing) + soft synthesized SFX synced to the animations.
usage: python3 reels/audio.py   (needs build/reels/narration.mp3) -> build/reels/mix.wav
"""
import os, subprocess, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR, DUR = 44100, 45.6
B = os.path.join(ROOT, "build", "reels")

raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(B, "narration.mp3"), "-ac", "1", "-ar", str(SR),
                      "-f", "f32le", "-"], capture_output=True, check=True).stdout
voice = np.frombuffer(raw, np.float32)
mix = np.zeros(int(SR * DUR), np.float32)
mix[:len(voice)] += voice[:len(mix)]
rng = np.random.default_rng(7)


def env(n, a=0.005, r=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / r)


def pop(f=900, d=0.12):
    n = int(SR * d); t = np.arange(n) / SR
    return np.sin(2 * np.pi * (f * t - f * 0.4 * t * t / d)) * env(n, 0.002, d / 4)


def whoosh(d=0.45):
    n = int(SR * d); x = rng.standard_normal(n)
    y = np.convolve(x, np.ones(40) / 40, "same")  # low-pass
    w = np.sin(np.pi * np.arange(n) / n) ** 2
    return y * w * 1.6


def ding(f=1320, d=0.6):
    n = int(SR * d); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2 * t)) * env(n, 0.003, 0.18)


def add(sig, at, g):
    i = int(at * SR); j = min(len(mix), i + len(sig)); mix[i:j] += g * sig[: j - i]


for t in [3.55, 10.8, 18.85, 25.65, 34.7, 39.95]:
    add(whoosh(), t, 0.10)
for t in [0.0, 6.5, 7.1, 7.45, 13.1, 13.85, 14.4, 15.0, 16.6, 19.1, 21.95, 22.5, 23.85, 30.55, 40.2]:
    add(pop(), t, 0.05)
for t in [0.85, 9.0, 17.35, 26.6, 30.3, 32.6, 33.6, 39.2, 41.5]:
    add(ding(), t, 0.04)
add(pop(220, 0.35), 15.95, 0.12)  # crack

mix /= max(1.0, np.abs(mix).max() / 0.97)
with wave.open(os.path.join(B, "mix.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("wrote mix.wav")
