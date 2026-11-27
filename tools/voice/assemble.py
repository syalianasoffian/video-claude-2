"""Assemble chosen takes into one voice-over: trim silence, light polish, place lines
with designed gaps. Writes keyman/assets/audio/vo.wav and vo_lines.json (line placement)."""
import json, os, sys, subprocess
import numpy as np, soundfile as sf, librosa
sys.path.insert(0, os.path.dirname(__file__))
from lines import LINES

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = "/home/user/work/keyman"
SR = 48000
choice = json.load(open(os.path.join(HERE, "choice.json"))) if os.path.exists(os.path.join(HERE, "choice.json")) else {}

# pause BEFORE each line (seconds)
GAP = {"hook1": 0.12, "hook2": 0.22, "hook3": 0.3, "s1a": 1.05, "s1b": 0.22, "s2a": 0.55, "s2b": 0.22,
       "s3a": 0.55, "s3b": 0.22, "s3c": 0.28, "sol1": 0.7, "sol2": 0.3, "cta": 0.55}
# designed pauses INSIDE a line are kept as generated, but long internal silences are capped
MAX_INTERNAL = 0.32


def trim(y, sr):
    iv = librosa.effects.split(y, top_db=38, frame_length=1024, hop_length=256)
    if not len(iv): return y
    # cap internal silences
    parts = []
    for i, (a, b) in enumerate(iv):
        if i:
            gap = a - iv[i - 1][1]
            keep = min(gap, int(MAX_INTERNAL * sr))
            parts.append(np.zeros(keep))
        parts.append(y[a:b])
    out = np.concatenate(parts)
    pad = int(0.03 * sr)
    return np.concatenate([np.zeros(pad), out, np.zeros(pad)])


def main():
    t = 0.0; segs = []; placed = []
    for lid, text in LINES:
        take = choice.get(lid, f"{lid}_A0")
        y, sr = librosa.load(os.path.join(HERE, "takes", take + ".wav"), sr=SR)
        y = trim(y, SR)
        t += GAP[lid]
        placed.append({"id": lid, "text": text, "take": take, "start": round(t, 3), "end": round(t + len(y) / SR, 3)})
        segs.append((t, y)); t += len(y) / SR
    total = t + 0.1
    out = np.zeros(int(total * SR) + SR)
    for s, y in segs:
        o = int(s * SR); out[o:o + len(y)] += y
    os.makedirs(f"{PROJ}/assets/audio", exist_ok=True)
    raw = f"{HERE}/vo_raw.wav"
    sf.write(raw, out[:int(total * SR)], SR)
    # polish: rumble cut, gentle de-mud, presence, compression, loudness to -16 LUFS, peak -1.5
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af",
                    "highpass=f=75,equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3200:t=q:w=1:g=2.5,"
                    "equalizer=f=9000:t=h:w=2000:g=1.5,acompressor=threshold=-22dB:ratio=3:attack=6:release=90:makeup=2,"
                    "loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", str(SR), "-ac", "1", f"{PROJ}/assets/audio/vo.wav"], check=True)
    json.dump({"duration": round(total, 3), "lines": placed}, open(f"{HERE}/vo_lines.json", "w"), indent=1, ensure_ascii=False)
    for p in placed: print(p["id"], p["start"], p["end"], p["take"])
    print("total", round(total, 2))


if __name__ == "__main__":
    main()
