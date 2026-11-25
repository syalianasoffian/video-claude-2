# Hibah Takaful — Premium Vertical Edit (Draft v1)

Source: 21.5 s iPhone HLG HDR clip, 1080×1920 @ 30 fps. Output: 1080×1920, 9:16, SDR BT.709, 22.45 s.

## Transcript (word-timed, Whisper medium)
> Seorang doktor, lelaki umur 32 tahun, tidak merokok, apply hibah sejuta ini dengan caruman RM130 sebulan
> sahaja untuk cover beban komitmen dia, dan kerana dia seorang breadwinner of the family.
> Tunggu apa lagi, dapatkan konsultasi percuma daripada saya, your AIA Certified FinCoach Practitioner.

## Timeline
| Time (s) | Spoken cue | Graphic |
|---|---|---|
| 0.0–0.5 | — | Fade in from navy, gold light sweep, camera pull-back 1.16→1.04 |
| 0.4–20.3 | — | Top pill label "KISAH PESERTA • HIBAH TAKAFUL" |
| 0.55–4.85 | doktor / lelaki / 32 tahun / tidak merokok | Holographic "Profil Peserta" card: 3D medical badge, ECG trace, chips that pop in on each word |
| 4.95–9.85 | hibah sejuta / caruman RM130 / sebulan / sahaja | Floating 3D gold shield on hologram projector, RM1,000,000 count-up, RM130 count-up, 3D spinning coin, "≈ RM4.27 sehari" (130×12/365), "sahaja!" stamp |
| 9.85–12.2 | cover beban komitmen | Commitment bars (house, car, family spending) fill to 100% gold with check badges |
| 12.2–14.85 | breadwinner of the family | Breadwinner figure glows, family joins, gold shield dome, "BREADWINNER" 3D gold type |
| 14.85–17.65 | tunggu apa lagi / konsultasi percuma | "Tunggu apa lagi?" + 3D gold "KONSULTASI PERCUMA" button with pulse and sparkles |
| 17.65–20.45 | daripada saya, AIA Certified FinCoach Practitioner | 3D medal + credential lower third |
| 20.45–22.45 | — | Flash transition, end card (covers the phone's "TV-off" glitch at the end of the raw clip) |

Camera punch-ins at: sejuta 5.5, RM130 6.86, sahaja 9.14, breadwinner 13.3, percuma 16.76, Practitioner 19.66.

## Safe zone
All text and graphics stay within x 120–960, y 220–1440. Below y=1000, nothing goes right of x=905 (TikTok/Reels button column).
Render with `--guides` to overlay the zone.

## Audio
Original voice (high-pass, light compression, presence boost), plus an original synthesized score
(chords change on each scene) ducked under the voice, plus subtle SFX (whooshes, chimes, riser, impact). Loudness -14 LUFS.

## Build
```
# 1. HDR -> SDR (hable tone-map)
ffmpeg -i raw.mp4 -vf "zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv444p" -c:v libx264 -crf 10 -an sdr.mp4
ffmpeg -i raw.mp4 -vn -c:a pcm_s16le -ar 48000 voice.wav
# 2. video
python3 src/render.py sdr.mp4 video_noaudio.mp4 [--guides]
# 3. music + sfx
python3 src/music.py music.wav sfx.wav
# 4. mix + mux: see src/mux.sh
```
