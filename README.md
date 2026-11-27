# Takaful "Stone Concept" — 3D motion graphics

Re-edit of the original Takaful explainer into a ~29 s futuristic 3D motion-graphics video
(original aspect ratio 640×434, rendered at 1280×868). The original voice-over is kept; only
the key lines are cut together.

Pipeline:
1. `python3 src/timeline.py` – edit list of voice clips + subtitle words → `build/timeline.json`
2. `python3 src/audio.py` – voice clips + synthesized SFX + ambient bed → `build/mix.wav`
   (needs the original at `build/original.mp4`)
3. `node src/render.js` – renders `src/index.html` (Three.js) frame by frame in headless Chromium → `build/video_noaudio.mp4`
   (`--stills 1,5,9` for preview frames)
4. Mux: `ffmpeg -i build/video_noaudio.mp4 -i build/mix.wav -c:v copy -c:a aac output/takaful.mp4`

---

# Medical Card Premium — Meta Ads (9:16, 1080×1920)  `mc/`

1 s cover (hook) + 30.6 s edit of the raw presenter video, 3D gold/navy motion graphics,
frosted masks over the raw video's burned-in captions, and a WhatsApp CTA end card.
Every piece of text and graphics stays inside the TikTok/Reels safe zone
(120 px left/right, 220 px top, 480 px bottom, clear of the right-hand button column).

1. Raw video → `build/original.mp4`; frames: `ffmpeg -i build/original.mp4 -vf scale=1080:1920:flags=lanczos -q:v 2 build/mc/src/%04d.jpg`
2. `python3 mc/audio.py` → `build/mc/mix.wav` (original voice + synthesized music bed ducked under the voice + SFX)
3. `node mc/render.js` → `build/mc/video_noaudio.mp4` (`--stills 0.5,5,9 --guides` shows the safe zone; `--from/--to/--port` for parallel chunks)
4. `ffmpeg -i build/mc/video_noaudio.mp4 -i build/mc/mix.wav -c:v copy -c:a aac -b:a 192k output/medical_card_FINAL.mp4`
