# Medical Card Premium — 9:16 Meta Ads edit (draft)

1080×1920, 30 fps, 31 s = 1 s hook cover + 30 s original footage with 3D motion graphics.
All text/graphics stay inside the TikTok/Reels safe zone (220 px top, 480 px bottom, 120 px sides).

Pipeline (raw video at `build/mc/raw.mp4`):
1. `medical-card/prep.sh` – graded 30 fps frames + blurred copy (hides the burned-in text of the raw)
2. `python3 -m demucs --two-stems=vocals -n htdemucs -o build/mc/sep build/mc/orig.wav` – isolate the voice
   (`orig.wav` = `ffmpeg -i raw.mp4 -ac 2 -ar 44100 orig.wav`)
3. `python3 medical-card/audio.py` – voice + synthesized music bed (ducked) + SFX → `build/mc/mix.wav`
4. `node medical-card/render.js` – Three.js + HTML overlays rendered in headless Chromium
   (`--stills 0,6.5 --guides` for preview frames with the safe-zone overlay)
5. `ffmpeg -i build/mc/video_noaudio.mp4 -i build/mc/mix.wav -c:v copy -c:a aac -b:a 192k -movflags +faststart output/medical_card_draft.mp4`

`words.json` – word timestamps of the voice-over (faster-whisper, Malay) used for captions and cue timing.
