"""Edit the owner's own recording into the voice-over: cap pauses, keep dramatic beats,
slight tempo lift, polish, then word-align against the spoken script and write the files build.py reads."""
import json, re, subprocess, difflib, warnings
import numpy as np, soundfile as sf, librosa
warnings.filterwarnings("ignore")
SR = 48000; R = "/home/user/work/rec"; TTS = "/home/user/work/tts"; PROJ = "/home/user/work/keyman"
TEMPO = 1.05

LINES = [
    ("hook1", "Ingat senang ke nak jadi business owner?"),
    ("hook2", "Ini tiga kerisauan kebanyakan business owner yang saya jumpa, sampai nak tidur malam pun tak lena."),
    ("hook3", "Dan yang ketiga itu paling scary."),
    ("s1a", "Pertama, tanggungan staf."),
    ("s1b", "Sepuluh, dua puluh orang staf yang hidupnya bergantung atas mereka."),
    ("s2a", "Kedua, bills dan tanggungan syarikat."),
    ("s2b", "Sewa, utiliti, bayaran kepada supplier. Setiap bulan tak pernah berhenti."),
    ("s3a", "Dan yang ketiga, loan dan pembiayaan."),
    ("s3b", "Beli mesin, hartanah, personal financing,"),
    ("s3c", "dan director syarikat adalah penjamin untuk loan tersebut."),
    ("sol1", "Sebab itu, ramai business owner yang ambil perlindungan KeyMan policy untuk cover diri mereka."),
    ("sol2", "Untuk cover ketiga-tiga kerisauan besar ini. Untuk ada peace of mind."),
    ("cta", "Business owner, nak tahu lebih lanjut, WhatsApp saya sekarang."),
]
# pause to keep (seconds, before tempo) for gaps that start near these source times
KEEP = {8.54: 0.38, 11.15: 0.7, 18.04: 0.42, 26.77: 0.42, 50.49: 0.4}
CAP = 0.16
LEAD_IN = 0.08


def norm(w): return re.sub(r"[^a-z0-9]", "", w.lower())


def gaps(y):
    hop = 240
    db = 20 * np.log10(librosa.feature.rms(y=y, frame_length=1024, hop_length=hop)[0] + 1e-9)
    th = np.percentile(db, 10) + 8
    q = db < th; out = []; i = 0
    while i < len(q):
        if q[i]:
            j = i
            while j < len(q) and q[j]: j += 1
            if (j - i) * hop / SR >= 0.12: out.append((i * hop / SR, j * hop / SR))
            i = j
        else: i += 1
    return out


def main():
    y, _ = librosa.load(f"{R}/den.wav", sr=SR)
    segs, pos = [], 0.0
    for a, b in gaps(y):
        keep = next((v for k, v in KEEP.items() if abs(k - a) < 0.25), CAP)
        if a < 0.05:  # leading silence
            pos = max(0, b - LEAD_IN); continue
        if b - a <= keep: continue
        mid_a = a + keep / 2; mid_b = b - keep / 2
        segs.append((pos, mid_a)); pos = mid_b
    segs.append((pos, len(y) / SR))
    parts = []
    for a, b in segs:
        s = y[int(a * SR):int(b * SR)].copy(); f = int(0.012 * SR)
        s[:f] *= np.linspace(0, 1, f); s[-f:] *= np.linspace(1, 0, f)
        parts.append(s)
    out = np.concatenate([np.zeros(int(0.1 * SR))] + parts + [np.zeros(int(0.15 * SR))])
    sf.write(f"{R}/cut.wav", out, SR)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{R}/cut.wav", "-af",
                    f"atempo={TEMPO},equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3500:t=q:w=1:g=2,highshelf=f=9000:g=1.5,"
                    "deesser=i=0.4,acompressor=threshold=-22dB:ratio=3:attack=6:release=90:makeup=2,"
                    "loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", str(SR), "-ac", "1", f"{PROJ}/assets/audio/vo.wav"], check=True)
    total = sf.info(f"{PROJ}/assets/audio/vo.wav").duration
    print("source", round(len(y) / SR, 2), "-> cut", round(len(out) / SR, 2), "-> final", round(total, 2))

    # word-align the final file
    import torch
    from transformers import pipeline
    torch.set_num_threads(4)
    pipe = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cpu")
    a16, _ = librosa.load(f"{PROJ}/assets/audio/vo.wav", sr=16000)
    r = pipe(a16, return_timestamps="word", generate_kwargs={"language": "malay", "task": "transcribe"}, chunk_length_s=30)
    ww = [(c["text"].strip(), c["timestamp"][0], c["timestamp"][1] or c["timestamp"][0] + 0.3) for c in r["chunks"]]
    print(r["text"])
    sw = [(lid, w) for lid, t in LINES for w in t.split()]
    sm = difflib.SequenceMatcher(None, [norm(w) for _, w in sw], [norm(w[0]) for w in ww], autojunk=False)
    times = [None] * len(sw)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("equal", "replace") and j2 > j1:
            if i2 - i1 == j2 - j1:
                for d in range(i2 - i1): times[i1 + d] = (ww[j1 + d][1], ww[j1 + d][2])
            else:
                s0, s1 = ww[j1][1], ww[j2 - 1][2]
                lens = [len(norm(w)) + 1 for _, w in sw[i1:i2]]; tot = sum(lens); acc = s0
                for d, ln in enumerate(lens):
                    e = acc + (s1 - s0) * ln / tot; times[i1 + d] = (acc, e); acc = e
    for i in range(len(sw)):
        if times[i] is None:
            p = next((times[j][1] for j in range(i - 1, -1, -1) if times[j]), 0)
            n = next((times[j][0] for j in range(i + 1, len(sw)) if times[j]), total)
            times[i] = (p, min(n, p + 0.3))
    lines, k = [], 0
    for lid, t in LINES:
        n = len(t.split()); ws = [{"w": w, "s": round(times[k + i][0], 3), "e": round(times[k + i][1], 3)} for i, (_, w) in enumerate(sw[k:k + n])]
        k += n
        lines.append({"id": lid, "text": t, "take": "rec", "start": ws[0]["s"], "end": ws[-1]["e"], "words": ws})
    json.dump({"duration": round(total, 3), "lines": [{k2: v for k2, v in l.items() if k2 != "words"} for l in lines]},
              open(f"{TTS}/vo_lines.json", "w"), indent=1, ensure_ascii=False)
    json.dump({"sig": [], "lines": lines}, open(f"{TTS}/align.json", "w"), indent=1, ensure_ascii=False)
    for l in lines: print(l["id"], l["start"], l["end"], " ".join(f'{w["w"]}@{w["s"]:.2f}' for w in l["words"]))


if __name__ == "__main__":
    main()
