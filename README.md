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
