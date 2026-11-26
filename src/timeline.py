"""Edit decision list: which pieces of the original voice-over are used, where
they land on the new 29 s timeline, and the corrected subtitle words.

Source times come from a word-level transcript of the original video.
Writes build/timeline.json (consumed by the renderer and the audio mixer).
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DURATION = 29.0

# (scene id, out_start, src_start, src_end, [(word, src_s, src_e), ...])
CLIPS = [
    ("family", 0.90, 17.00, 20.80, [
        ("Bagi", 17.04, 17.34), ("kita", 17.34, 17.78), ("sebagai", 17.78, 18.24),
        ("ibu", 18.24, 18.64), ("ayah,", 18.64, 19.18), ("sebagai", 19.54, 19.82),
        ("ketua", 19.82, 20.16), ("keluarga", 20.16, 20.72)]),
    ("house", 4.95, 59.90, 60.80, [
        ("kita", 59.94, 60.06), ("bayar", 60.06, 60.42), ("rumah,", 60.42, 60.68)]),
    ("money", 6.00, 62.10, 64.00, [
        ("kita", 62.14, 62.86), ("bayar", 62.86, 63.30), ("kereta...", 63.30, 63.92)]),
    ("hospital", 8.20, 116.93, 120.15, [
        ("kita", 116.90, 117.24), ("menghadapi", 117.24, 117.98),
        ("sakit", 117.98, 118.72), ("hospitalisasi.", 118.72, 120.04)]),
    ("risk", 11.80, 144.40, 148.98, [
        ("Bila-bila", 144.44, 145.54), ("salah", 145.54, 146.14), ("satu", 146.14, 147.06),
        ("musibah", 147.06, 148.16), ("ini", 148.16, 148.40), ("berlaku,", 148.40, 148.92)]),
    ("shield", 16.73, 227.85, 237.60, [
        ("tembok", 227.90, 228.46), ("ini,", 228.46, 228.76),
        ("perlindungan", 229.00, 229.70), ("takaful", 229.70, 230.22), ("ini", 230.22, 230.50),
        ("yang", 230.50, 230.72), ("akan", 230.72, 231.04), ("menahan", 231.04, 231.94),
        ("semua", 231.94, 233.04), ("beban", 233.04, 233.60), ("komitmen", 233.60, 234.32),
        ("ini", 234.32, 234.62), ("daripada", 234.62, 235.16), ("menimpa", 235.16, 235.90),
        ("keluarga", 235.90, 237.04), ("kita.", 237.04, 237.44)]),
]

# subtitle line breaks: index of words where a new caption page starts (per clip)
PAGES = {
    "family": [0, 5],
    "house": [0],
    "money": [0],
    "hospital": [0],
    "risk": [0, 3],
    "shield": [0, 2, 5, 8, 12, 14],
}

KEY_WORDS = {"ibu", "ayah,", "keluarga", "rumah,", "kereta...", "hospitalisasi.",
             "musibah", "tembok", "perlindungan", "takaful", "beban", "komitmen",
             "keluarga", "menahan"}


def build():
    clips, captions = [], []
    for sid, out0, s0, s1, words in CLIPS:
        out1 = out0 + (s1 - s0)
        clips.append({"id": sid, "out_start": out0, "out_end": round(out1, 3),
                      "src_start": s0, "src_end": s1})
        mapped = [{"w": w, "s": round(out0 + a - s0, 3), "e": round(out0 + b - s0, 3),
                   "key": w in KEY_WORDS} for w, a, b in words]
        starts = PAGES[sid] + [len(mapped)]
        for i in range(len(starts) - 1):
            ws = mapped[starts[i]:starts[i + 1]]
            nxt = mapped[starts[i + 1]]["s"] if starts[i + 1] < len(mapped) else ws[-1]["e"] + 0.35
            captions.append({"s": ws[0]["s"] - 0.05, "e": nxt - 0.02, "words": ws})
    out = {"duration": DURATION, "fps": 30, "clips": clips, "captions": captions}
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    with open(os.path.join(ROOT, "build", "timeline.json"), "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    return out


if __name__ == "__main__":
    t = build()
    for c in t["clips"]:
        print(c)
