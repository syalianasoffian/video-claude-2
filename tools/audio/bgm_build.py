"""Stitch the two MusicGen sections into one bed timed to the edit:
tense from 0 until the KeyMan reveal, a riser+silence beat, bright from the reveal to the end."""
import json, numpy as np, soundfile as sf, librosa, subprocess
SR = 48000
sc = json.load(open("/home/user/work/tts/scenes.json"))
total = sc["total"]
reveal = next(s[1] for s in sc["scenes"] if s[0] == "keyman")
loan = next(s[1] for s in sc["scenes"] if s[0] == "loan")


def load(p):
    y, _ = librosa.load(p, sr=SR, mono=True)
    return y / (np.max(np.abs(y)) + 1e-9)


def fit(y, n, xf=1.0):
    """loop with crossfade until length n"""
    x = int(xf * SR)
    out = y.copy()
    while len(out) < n:
        seg = y[int(2.0 * SR):]   # skip the intro on repeats
        fade = np.linspace(0, 1, x)
        out[-x:] = out[-x:] * (1 - fade) + seg[:x] * fade
        out = np.concatenate([out, seg[x:]])
    return out[:n]


tense = load("/home/user/work/audio/bgm_tense.wav")
bright = load("/home/user/work/audio/bgm_bright.wav")
n = int(total * SR)
bed = np.zeros(n)
a = fit(tense, int((reveal + 0.2) * SR))
# tension: thin the bed out under the loan scene for the scary part (lowpass-ish by smoothing) - keep simple: slight dip
env = np.ones(len(a)); f = int(0.25 * SR)
env[-f:] = np.linspace(1, 0, f)
bed[:len(a)] += a * env
b = fit(bright, n - int((reveal - 0.05) * SR))
fb = np.ones(len(b)); fi = int(0.12 * SR); fb[:fi] = np.linspace(0, 1, fi)
o = int((reveal - 0.05) * SR)
bed[o:o + len(b)] += b[:n - o] * fb[:n - o] * 1.05
sf.write("/home/user/work/audio/bgm_raw.wav", bed, SR)
# EQ: cut sub mud, lift presence so the bed reads on phone speakers; loudness target
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "/home/user/work/audio/bgm_raw.wav", "-af",
                "highpass=f=40,equalizer=f=120:t=q:w=1:g=-3,highshelf=f=2500:g=4,equalizer=f=900:t=q:w=1.2:g=2,"
                "loudnorm=I=-18:TP=-2:LRA=9,aformat=channel_layouts=stereo",
                "-ar", str(SR), "/home/user/work/keyman/assets/audio/bgm.wav"], check=True)
print("bgm", total, "reveal", reveal)
